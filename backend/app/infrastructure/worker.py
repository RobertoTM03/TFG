import asyncio
import json
import threading
import time
from typing import List, Optional

from loguru import logger

from app.config import Settings
from app.domain.exceptions import EmbeddingUnavailableError, LLMUnavailableError
from app.domain.ports.task_repository import TaskRepositoryPort
from app.domain.ports.installation_repository import InstallationRepositoryPort
from app.domain.ports.repo_config_repository import RepoConfigRepositoryPort
from app.infrastructure.container import Container
from app.infrastructure.tracing import validation_trace
from app.infrastructure.websocket_manager import WebSocketManager


class _WorkerThread:
    """Single worker thread that polls the task queue and processes tasks."""

    def __init__(
        self,
        name: str,
        container: Container,
        task_repo: TaskRepositoryPort,
        installation_repo: InstallationRepositoryPort,
        repo_config_repo: RepoConfigRepositoryPort,
        settings: Settings,
        ws_manager: Optional[WebSocketManager],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._name = name
        self._container = container
        self._db = task_repo
        self._installation_repo = installation_repo
        self._repo_config_repo = repo_config_repo
        self._settings = settings
        self._ws_manager = ws_manager
        self._loop = loop
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=self._name,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _run(self) -> None:
        while self._running:
            try:
                task = self._db.claim_pending_task()
                if task:
                    self._process_task(task)
                else:
                    time.sleep(self._settings.WORKER_POLL_INTERVAL)
            except Exception as exc:
                logger.error(f"[{self._name}] Worker loop error: {exc}")
                time.sleep(5)

    def _process_task(self, task: dict) -> None:
        task_id = str(task["id"])
        user_id = str(task["user_id"]) if task.get("user_id") else None
        repo_url = task["repository_url"]
        rules = task["rules"] if isinstance(task["rules"], list) else []

        clone_url = None
        installation_id = task.get("github_installation_id")
        repo_full_name = task.get("repository_full_name", "")
        if installation_id:
            try:
                inst_token = self._container.github_app.get_installation_token(installation_id)
                clone_url = repo_url.replace("https://", f"https://x-access-token:{inst_token}@", 1)
            except Exception as exc:
                logger.warning(f"[{self._name}] Could not get installation token for cloning: {exc}")
                # Stale installation ID — try a fresh lookup from GitHub API
                if repo_full_name and "/" in repo_full_name:
                    owner, repo_name = repo_full_name.split("/", 1)
                    try:
                        fresh_id = self._container.github_app.get_installation_id_for_repo(owner, repo_name)
                        if fresh_id and fresh_id != installation_id:
                            logger.info(f"[{self._name}] Fresh installation ID: {fresh_id} (was {installation_id})")
                            if task.get("user_id"):
                                self._installation_repo.upsert_installation(fresh_id, str(task["user_id"]), owner)
                            inst_token = self._container.github_app.get_installation_token(fresh_id)
                            clone_url = repo_url.replace("https://", f"https://x-access-token:{inst_token}@", 1)
                    except Exception as exc2:
                        logger.warning(f"[{self._name}] Fresh installation lookup also failed: {exc2}")

        logger.info(f"[{self._name}] Processing task {task_id} for {repo_url}")

        def on_progress(pct: int, msg: str) -> None:
            self._db.update_task_progress(task_id, pct, msg)
            self._notify(user_id, task_id, {
                "type": "task_progress",
                "task_id": task_id,
                "progress": pct,
                "message": msg,
            })

        # Partial results from a previous attempt (LLM resumption)
        partial_results = self._db.get_task_partial_result(task_id)
        if partial_results:
            logger.info(
                f"[{self._name}] Task {task_id} resuming from rule "
                f"{len(partial_results) + 1} ({len(partial_results)} already evaluated)"
            )

        # Callback: persist each verdict as it's obtained
        partial_snapshot: list = list(partial_results)

        def on_rule_evaluated(idx: int, validation) -> None:
            ev = validation.evaluation
            cc = validation.cross_check
            entry = {
                "rule": validation.rule,
                "evaluation": {
                    "verdict": ev.verdict if ev else "fail",
                    "explanation": ev.explanation if ev else "",
                    "suggestions": ev.suggestions if ev else [],
                    "llm_provider": ev.llm_provider if ev else "",
                    "tokens_used": ev.tokens_used if ev else 0,
                },
                "cross_check": {
                    "primary_verdict": cc.primary.verdict,
                    "primary_model": cc.primary.llm_provider,
                    "primary_explanation": cc.primary.explanation,
                    "secondary_verdict": cc.secondary.verdict,
                    "secondary_model": cc.secondary.llm_provider,
                    "secondary_explanation": cc.secondary.explanation,
                    "agreement": cc.agreement,
                    "discriminator_used": cc.discriminator_used,
                    "discriminator_model": cc.discriminator_model,
                    "discriminator_reasoning": cc.discriminator_reasoning,
                } if cc else None,
            }
            partial_snapshot.append(entry)
            self._db.save_task_partial_result(task_id, partial_snapshot)

        try:
            enable_cross_check = bool(task.get("enable_cross_check", False))
            repo_config = self._repo_config_repo.get_repo_config(
                str(task["user_id"]), task["repository_full_name"]
            ) if task.get("user_id") else None
            max_chunks_per_rule = repo_config["max_chunks_per_rule"] if repo_config else None

            # Resolve per-repo LLM overrides (fall back to global settings if NULL)
            llm_override = None
            llm_primary_override = None
            llm_secondary_override = None
            if repo_config:
                if repo_config.get("llm_model"):
                    llm_override = self._container.get_llm(repo_config["llm_model"])
                if repo_config.get("llm_primary_model"):
                    llm_primary_override = self._container.get_llm(repo_config["llm_primary_model"])
                if repo_config.get("llm_secondary_model"):
                    llm_secondary_override = self._container.get_llm(repo_config["llm_secondary_model"])

            service = self._container.validation_service
            langsmith_enabled = bool(
                self._settings.LANGSMITH_TRACING and self._settings.LANGSMITH_API_KEY
            )
            with validation_trace(repo_url, rules, enabled=langsmith_enabled):
                result = service.validate(
                    repo_url, rules,
                    on_progress=on_progress,
                    enable_cross_check=enable_cross_check,
                    clone_url=clone_url,
                    pr_branch=task.get("pr_head_ref"),
                    max_chunks_per_rule=max_chunks_per_rule,
                    partial_results=partial_results,
                    on_rule_evaluated=on_rule_evaluated,
                    llm_override=llm_override,
                    llm_primary_override=llm_primary_override,
                    llm_secondary_override=llm_secondary_override,
                )

            result_json = self._serialize_result(result)
            self._db.complete_task(task_id, result_json)

            self._notify(user_id, task_id, {
                "type": "task_completed",
                "task_id": task_id,
            })
            logger.info(f"[{self._name}] Task {task_id} completed successfully")

            if task.get("pr_number"):
                self._post_github_review(task, result_json)

        except (LLMUnavailableError, EmbeddingUnavailableError) as exc:
            retry_count = task.get("retry_count", 0)
            max_retries = self._settings.WORKER_MAX_TASK_RETRIES
            error_kind = "LLM" if isinstance(exc, LLMUnavailableError) else "Embedding"
            if retry_count < max_retries:
                self._db.requeue_task(task_id, self._settings.WORKER_RETRY_DELAY)
                self._notify(user_id, task_id, {
                    "type": "task_requeued",
                    "task_id": task_id,
                    "retry": retry_count + 1,
                    "max_retries": max_retries,
                })
                logger.warning(
                    f"[{self._name}] Task {task_id} requeued due to {error_kind} unavailability "
                    f"(attempt {retry_count + 1}/{max_retries}). "
                    f"Retry after {self._settings.WORKER_RETRY_DELAY}s."
                )
            else:
                code = "LLM_UNAVAILABLE" if isinstance(exc, LLMUnavailableError) else "EMBEDDING_UNAVAILABLE"
                error_payload = json.dumps({
                    "code": code,
                    "message": (
                        f"El servicio de IA no respondió tras {max_retries} intentos. "
                        "Inténtalo de nuevo más tarde."
                        if isinstance(exc, LLMUnavailableError) else
                        f"El servicio de búsqueda semántica no respondió tras {max_retries} intentos. "
                        "Inténtalo de nuevo más tarde."
                    ),
                    "technical": str(exc),
                })
                self._db.fail_task(task_id, error_payload)
                self._notify(user_id, task_id, {
                    "type": "task_failed",
                    "task_id": task_id,
                    "error": error_payload,
                })
                logger.error(
                    f"[{self._name}] Task {task_id} permanently failed after "
                    f"{max_retries} requeue attempts: {exc}"
                )
                if task.get("pr_number"):
                    self._post_github_review_error(task, error_payload)

        except Exception as exc:
            error_payload = json.dumps({
                "code": "UNEXPECTED_ERROR",
                "message": "Ocurrió un error inesperado durante la evaluación. Contacta con soporte si persiste.",
                "technical": str(exc),
            })
            self._db.fail_task(task_id, error_payload)
            self._notify(user_id, task_id, {
                "type": "task_failed",
                "task_id": task_id,
                "error": error_payload,
            })
            logger.error(f"[{self._name}] Task {task_id} failed: {exc}")

            if task.get("pr_number"):
                self._post_github_review_error(task, error_payload)

    # GitHub PR review posting

    def _post_github_review(self, task: dict, result_json: dict) -> None:
        try:
            installation_id = task.get("github_installation_id")
            if not installation_id:
                return

            github_app = self._container.github_app
            owner_login, repo_name = task["repository_full_name"].split("/", 1)
            pr_number = task["pr_number"]
            pr_head_sha = task.get("pr_head_sha")

            score = github_app.calculate_score(result_json)

            repo_config = self._repo_config_repo.get_repo_config(
                str(task["user_id"]), task["repository_full_name"]
            ) if task.get("user_id") else None
            threshold = repo_config["approval_threshold"] if repo_config else self._settings.APPROVAL_THRESHOLD
            approved = score >= threshold

            if pr_head_sha:
                pct = int(score * 100)
                desc = f"{'Aprobado' if approved else 'Cambios requeridos'} — {pct}% (umbral {int(threshold * 100)}%)"
                github_app.set_commit_status(
                    installation_id, owner_login, repo_name, pr_head_sha,
                    "success" if approved else "failure", desc,
                )

            eval_number = self._db.count_pr_tasks(
                task["repository_full_name"], pr_number
            )
            body = github_app.build_comment(score, result_json, threshold, eval_number)
            github_app.post_pr_comment(installation_id, owner_login, repo_name, pr_number, body)

            logger.info(
                f"[{self._name}] Posted bot review for {task['repository_full_name']} "
                f"PR #{pr_number} (score={score:.2f}, approved={approved})"
            )
        except Exception as exc:
            logger.error(f"[{self._name}] Failed to post GitHub review for task {task['id']}: {exc}")

    def _post_github_review_error(self, task: dict, error_msg: str) -> None:
        try:
            installation_id = task.get("github_installation_id")
            if not installation_id:
                return

            github_app = self._container.github_app
            owner_login, repo_name = task["repository_full_name"].split("/", 1)
            pr_head_sha = task.get("pr_head_sha")

            if pr_head_sha:
                github_app.set_commit_status(
                    installation_id, owner_login, repo_name, pr_head_sha,
                    "error", "Validation error — see PR comment",
                )

            body = "## Informe de evaluación\n\nNo ha sido posible completar la evaluación en estos momentos. Por favor, inténtalo de nuevo más tarde.\n\n---\n_Generado automáticamente_"
            github_app.post_pr_comment(installation_id, owner_login, repo_name, task["pr_number"], body)
        except Exception as exc:
            logger.error(f"[{self._name}] Failed to post error review for task {task['id']}: {exc}")

    def _notify(self, user_id: Optional[str], task_id: str, message: dict) -> None:
        if not user_id or not self._ws_manager or not self._loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._ws_manager.notify_task(task_id, user_id, message),
                self._loop,
            )
        except Exception:
            pass

    @staticmethod
    def _serialize_result(result) -> dict:
        return {
            "validations": [
                {
                    "rule": v.rule,
                    "related_files": [
                        {
                            "file_path": f.file_path,
                            "relevance_score": f.relevance_score,
                            "file_content": f.file_content,
                            "language": f.language,
                            "matched_symbols": f.matched_symbols,
                            "truncated": f.truncated,
                        }
                        for f in v.related_files
                    ],
                    "evaluation": {
                        "verdict": v.evaluation.verdict,
                        "explanation": v.evaluation.explanation,
                        "suggestions": v.evaluation.suggestions,
                        "llm_provider": v.evaluation.llm_provider,
                        "tokens_used": v.evaluation.tokens_used,
                    } if v.evaluation else None,
                    "cross_check": {
                        "primary_verdict": v.cross_check.primary.verdict,
                        "primary_model": v.cross_check.primary.llm_provider,
                        "primary_explanation": v.cross_check.primary.explanation,
                        "secondary_verdict": v.cross_check.secondary.verdict,
                        "secondary_model": v.cross_check.secondary.llm_provider,
                        "secondary_explanation": v.cross_check.secondary.explanation,
                        "agreement": v.cross_check.agreement,
                        "discriminator_used": v.cross_check.discriminator_used,
                        "discriminator_model": v.cross_check.discriminator_model,
                        "discriminator_reasoning": v.cross_check.discriminator_reasoning,
                    } if v.cross_check else None,
                }
                for v in result.validations
            ],
            "embedding_model": result.embedding_model,
            "chunking_strategy": result.chunking_strategy,
            "llm_model": result.llm_model,
            "processing_time_seconds": result.processing_time_seconds,
        }


class TaskWorker:
    """Manager that spawns and supervises N worker threads."""

    def __init__(
        self,
        container: Container,
        task_repo: TaskRepositoryPort,
        installation_repo: InstallationRepositoryPort,
        repo_config_repo: RepoConfigRepositoryPort,
        settings: Settings,
        ws_manager: Optional[WebSocketManager] = None,
    ) -> None:
        self._container = container
        self._task_repo = task_repo
        self._installation_repo = installation_repo
        self._repo_config_repo = repo_config_repo
        self._settings = settings
        self._ws_manager = ws_manager
        self._workers: List[_WorkerThread] = []

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        n = self._settings.WORKER_CONCURRENCY
        for i in range(n):
            name = f"task-worker-{i + 1}" if n > 1 else "task-worker"
            w = _WorkerThread(
                name=name,
                container=self._container,
                task_repo=self._task_repo,
                installation_repo=self._installation_repo,
                repo_config_repo=self._repo_config_repo,
                settings=self._settings,
                ws_manager=self._ws_manager,
                loop=loop,
            )
            w.start()
            self._workers.append(w)
        logger.info(f"Task worker started ({n} thread{'s' if n > 1 else ''})")

    def stop(self) -> None:
        for w in self._workers:
            w.stop()
        logger.info("Task worker stopping")

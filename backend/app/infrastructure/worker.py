import asyncio
import threading
import time
from typing import Optional

from loguru import logger

from app.config import Settings
from app.infrastructure.container import Container
from app.infrastructure.database import Database
from app.infrastructure.websocket_manager import WebSocketManager

class TaskWorker:
    """Daemon thread that processes validation tasks from the database."""

    def __init__(
        self,
        container: Container,
        database: Database,
        settings: Settings,
        ws_manager: Optional[WebSocketManager] = None,
    ) -> None:
        self._container = container
        self._db = database
        self._settings = settings
        self._ws_manager = ws_manager
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start the worker daemon. Must be called from the main thread."""
        self._loop = loop
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="task-worker",
        )
        self._thread.start()
        logger.info("Task worker started")

    def stop(self) -> None:
        self._running = False
        logger.info("Task worker stopping")

    # Main loop

    def _run(self) -> None:
        """Poll for pending tasks and process them one at a time."""
        while self._running:
            try:
                # Need to use the real claim_pending_task from the DB
                task = self._db.claim_pending_task()
                if task:
                    self._process_task(task)
                else:
                    time.sleep(self._settings.WORKER_POLL_INTERVAL)
            except Exception as exc:
                logger.error(f"Worker loop error: {exc}")
                time.sleep(5)

    # Task processing

    def _process_task(self, task: dict) -> None:
        task_id = str(task["id"])
        user_id = str(task["user_id"]) if task.get("user_id") else None
        repo_url = task["repository_url"]
        rules = task["rules"] if isinstance(task["rules"], list) else []

        installation_id = task.get("github_installation_id")
        if installation_id:
            try:
                inst_token = self._container.github_app.get_installation_token(installation_id)
                repo_url = repo_url.replace("https://", f"https://x-access-token:{inst_token}@", 1)
            except Exception as exc:
                logger.warning(f"Could not get installation token for cloning: {exc}")

        safe_url = repo_url.split("@")[-1] if "@" in repo_url else repo_url
        logger.info(f"Processing task {task_id} for {safe_url}")

        def on_progress(pct: int, msg: str) -> None:
            self._db.update_task_progress(task_id, pct, msg)
            self._notify(user_id, {
                "type": "task_progress",
                "task_id": task_id,
                "progress": pct,
                "message": msg,
            })

        try:
            # Import here to avoid circular dependency at module level
            from app.application.services.validation_service import (
                ValidationService,
            )

            enable_cross_check = bool(task.get("enable_cross_check", False))
            service = ValidationService(self._container, self._settings)
            result = service.validate(
                repo_url, rules,
                on_progress=on_progress,
                enable_cross_check=enable_cross_check,
            )

            result_json = self._serialize_result(result)
            self._db.complete_task(task_id, result_json)

            self._notify(user_id, {
                "type": "task_completed",
                "task_id": task_id,
            })
            logger.info(f"Task {task_id} completed successfully")

            if task.get("pr_number"):
                self._post_github_review(task, result_json)

        except Exception as exc:
            error_msg = str(exc)
            self._db.fail_task(task_id, error_msg)

            self._notify(user_id, {
                "type": "task_failed",
                "task_id": task_id,
                "error": error_msg,
            })
            logger.error(f"Task {task_id} failed: {error_msg}")

            if task.get("pr_number"):
                self._post_github_review_error(task, error_msg)

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
            threshold = self._settings.APPROVAL_THRESHOLD
            approved = score >= threshold

            if pr_head_sha:
                pct = int(score * 100)
                desc = f"{'Aprobado' if approved else 'Cambios requeridos'} — {pct}% (umbral {int(threshold*100)}%)"
                github_app.set_commit_status(
                    installation_id, owner_login, repo_name, pr_head_sha,
                    "success" if approved else "failure", desc,
                )

            body = github_app.build_comment(score, result_json, threshold)
            github_app.post_pr_comment(installation_id, owner_login, repo_name, pr_number, body)

            logger.info(
                f"Posted bot review for {task['repository_full_name']} PR #{pr_number} "
                f"(score={score:.2f}, approved={approved})"
            )
        except Exception as exc:
            logger.error(f"Failed to post GitHub review for task {task['id']}: {exc}")

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

            body = f"## Validacion automatica\n\nLa validacion fallo:\n\n> {error_msg}"
            github_app.post_pr_comment(installation_id, owner_login, repo_name, task["pr_number"], body)
        except Exception as exc:
            logger.error(f"Failed to post error review for task {task['id']}: {exc}")

    # WebSocket notification from worker thread

    def _notify(self, user_id: Optional[str], message: dict) -> None:
        """Send a WebSocket notification. Safe to call from any thread."""
        if not user_id or not self._ws_manager or not self._loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._ws_manager.notify_user(user_id, message),
                self._loop,
            )
        except Exception:
            pass

    # Serialisation helpers

    @staticmethod
    def _serialize_result(result) -> dict:
        return {
            "repomap": result.repomap,
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
                    "match_count": len(v.related_files),
                    "evaluation": {
                        "verdict": v.evaluation.verdict,
                        "confidence": v.evaluation.confidence,
                        "explanation": v.evaluation.explanation,
                        "suggestions": v.evaluation.suggestions,
                        "llm_provider": v.evaluation.llm_provider,
                        "tokens_used": v.evaluation.tokens_used,
                    } if v.evaluation else None,
                    "cross_check": {
                        "primary_verdict": v.cross_check.primary.verdict,
                        "primary_confidence": v.cross_check.primary.confidence,
                        "primary_model": v.cross_check.primary.llm_provider,
                        "secondary_verdict": v.cross_check.secondary.verdict,
                        "secondary_confidence": v.cross_check.secondary.confidence,
                        "secondary_model": v.cross_check.secondary.llm_provider,
                        "strategy_used": v.cross_check.strategy_used,
                        "agreement": v.cross_check.agreement,
                    } if v.cross_check else None,
                }
                for v in result.validations
            ],
            "embedding_model": result.embedding_model,
            "chunking_strategy": result.chunking_strategy,
            "llm_model": result.llm_model,
        }

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

        if user_id:
            user = self._db.get_user_by_id(user_id)
            git_token = user.get("git_token") if user else None
            if git_token and repo_url.startswith("https://"):
                repo_url = repo_url.replace("https://", f"https://{git_token}@", 1)

        logger.info(f"Processing task {task_id} for {repo_url}")

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

            service = ValidationService(self._container, self._settings)
            result = service.validate(repo_url, rules, on_progress=on_progress)

            result_json = self._serialize_result(result)
            self._db.complete_task(task_id, result_json)

            self._notify(user_id, {
                "type": "task_completed",
                "task_id": task_id,
            })
            logger.info(f"Task {task_id} completed successfully")

        except Exception as exc:
            error_msg = str(exc)
            self._db.fail_task(task_id, error_msg)

            self._notify(user_id, {
                "type": "task_failed",
                "task_id": task_id,
                "error": error_msg,
            })
            logger.error(f"Task {task_id} failed: {error_msg}")

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
            "summary": result.summary,
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
                        "confidence": v.evaluation.confidence,
                        "explanation": v.evaluation.explanation,
                        "suggestions": v.evaluation.suggestions,
                        "llm_provider": v.evaluation.llm_provider,
                        "tokens_used": v.evaluation.tokens_used,
                    } if v.evaluation else None,
                }
                for v in result.validations
            ],
            "embedding_model": result.embedding_model,
            "chunking_strategy": result.chunking_strategy,
            "llm_model": result.llm_model,
        }

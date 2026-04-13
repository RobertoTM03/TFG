import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from loguru import logger

from app.config import Settings
from app.infrastructure.container import Container
from app.infrastructure.websocket_manager import WebSocketManager
from app.infrastructure.worker import TaskWorker

from app.api.routes import auth, health, repos, rules, tasks, webhooks, repo_config, students
from app.infrastructure.limiter import limiter, init_limiter


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: wire dependencies and launch the worker daemon.
    Shutdown: stop the worker gracefully."""

    settings = Settings()
    init_limiter(settings)
    for warning in settings.warn_if_incomplete():
        logger.warning(f"[config] {warning}")

    container = Container(settings)
    ws_manager = WebSocketManager()
    worker = TaskWorker(container, container.database, settings, ws_manager)

    application.state.settings = settings
    application.state.container = container
    application.state.database = container.database
    application.state.ws_manager = ws_manager
    application.state.worker = worker

    loop = asyncio.get_running_loop()
    worker.start(loop)
    logger.info("Application started -- worker daemon running")

    yield

    worker.stop()
    container.database.close()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="TFG Repository Validator",
    description=(
        "Unified API that authenticates users via GitHub OAuth, "
        "lets them define validation rules per repository, and "
        "evaluates those rules asynchronously using semantic search "
        "over the repository's source code."
    ),
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS -- allow the frontend to reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(repos.router)
app.include_router(rules.router)
app.include_router(tasks.router)
app.include_router(repo_config.router)
app.include_router(students.router)
app.include_router(webhooks.router)

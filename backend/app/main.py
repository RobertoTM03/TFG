import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import Settings
from app.infrastructure.container import Container
from app.infrastructure.websocket_manager import WebSocketManager
from app.infrastructure.worker import TaskWorker

from app.api.routes import auth, health, repos, rules, tasks


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: wire dependencies and launch the worker daemon.
    Shutdown: stop the worker gracefully."""

    settings = Settings()
    container = Container(settings)
    ws_manager = WebSocketManager()
    worker = TaskWorker(container, container.database, settings, ws_manager)

    application.state.settings = settings
    application.state.container = container
    application.state.database = container.database
    application.state.ws_manager = ws_manager
    application.state.worker = worker

    loop = asyncio.get_event_loop()
    worker.start(loop)
    logger.info("Application started -- worker daemon running")

    yield

    worker.stop()
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
)

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

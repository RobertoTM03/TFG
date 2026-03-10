from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import Settings


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: wire dependencies and launch the worker daemon.
    Shutdown: stop the worker gracefully."""

    settings = Settings()
    application.state.settings = settings

    # TODO: initialize Database, Container
    # TODO: initialize WebSocketManager, TaskWorker

    logger.info("Application started")

    yield

    logger.info("Application shutdown complete")


app = FastAPI(
    title="TFG Repository Validator",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: register routers

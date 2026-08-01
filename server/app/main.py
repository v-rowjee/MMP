"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.dashboard import router as dashboard_router
from app.api.upload import router as upload_router
from app.config import Settings
from app.core.database import create_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared application resources."""

    settings = Settings.model_validate({})

    app.state.settings = settings
    app.state.db = create_database(settings)

    yield


def create_app() -> FastAPI:
    """Create the FastAPI application."""

    app = FastAPI(
        title="MMP Backend",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(upload_router)
    app.include_router(chat_router)
    app.include_router(dashboard_router)

    return app


app = create_app()
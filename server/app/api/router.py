"""API router registration."""

from fastapi import APIRouter

from app.api.upload import router as upload_router
from app.api.chat import router as chat_router
from app.api.dashboard import router as dashboard_router


router = APIRouter()

router.include_router(upload_router)
router.include_router(chat_router)
router.include_router(dashboard_router)
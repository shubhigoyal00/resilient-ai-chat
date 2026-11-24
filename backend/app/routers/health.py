"""GET /health — liveness of SQLite and the configured key pool."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import db_reachable
from app.services.cache_service import cache_enabled

router = APIRouter()


@router.get("/health")
def health():
    settings = get_settings()
    keys_configured = len(settings.key_pool)
    healthy = db_reachable() and keys_configured >= 2
    payload = {
        "status": "ok" if healthy else "unhealthy",
        "keys_configured": keys_configured,
        "cache_enabled": cache_enabled(),
    }
    return JSONResponse(payload, status_code=200 if healthy else 503)

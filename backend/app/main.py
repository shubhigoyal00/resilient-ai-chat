"""Application entrypoint."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.routers import chat, health, sessions
from app.services.cache_service import configure_cache

logger = logging.getLogger(__name__)

settings = get_settings()

# Docs routes disabled to keep the public surface to exactly three endpoints.
app = FastAPI(title="Resilient AI Chat", docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(sessions.router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    configure_cache()


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "internal server error"}, status_code=500)

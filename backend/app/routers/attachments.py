"""Attachment upload and retrieval endpoints."""

import base64
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Attachment
from app.services.file_service import UploadRejected, classify_upload

router = APIRouter()


@router.post("/attachments", status_code=201)
async def upload_attachment(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    settings = get_settings()

    session_id = (session_id or "").strip()
    if not 1 <= len(session_id) <= 128:
        raise HTTPException(422, "invalid session_id")

    # Read at most limit+1 bytes so oversized files are rejected early.
    limit = settings.max_upload_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            413, f"file too large (max {settings.max_upload_mb:g} MB)"
        )

    try:
        info = classify_upload(file.filename, data, settings.max_doc_chars)
    except UploadRejected as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc

    attachment = Attachment(
        id=uuid.uuid4().hex,
        session_id=session_id,
        filename=info["filename"],
        mime_type=info["mime_type"],
        kind=info["kind"],
        content_b64=base64.b64encode(data).decode("ascii")
        if info["kind"] == "image"
        else None,
        extracted_text=info["extracted_text"],
    )
    db.add(attachment)
    db.commit()

    return {
        "attachment_id": attachment.id,
        "filename": attachment.filename,
        "mime_type": attachment.mime_type,
        "kind": attachment.kind,
        "text_chars": len(attachment.extracted_text)
        if attachment.extracted_text is not None
        else None,
    }


@router.get("/attachments/{attachment_id}/raw")
def get_attachment_raw(attachment_id: str, db: Session = Depends(get_db)):
    """Serve stored image bytes (used by the frontend for previews/history)."""
    att = db.scalar(select(Attachment).where(Attachment.id == attachment_id))
    if att is None or att.kind != "image" or not att.content_b64:
        raise HTTPException(404, "attachment not found")
    return Response(
        content=base64.b64decode(att.content_b64),
        media_type=att.mime_type,
    )

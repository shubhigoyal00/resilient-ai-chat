"""POST /chat — the only inference endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Attachment
from app.models import Message as MessageRow
from app.schemas import ChatRequest, ChatResponse
from app.services import llm_service, session_service

router = APIRouter()


def _user_content_parts(text: str, attachments: list[Attachment]) -> str | list[dict]:
    """Build the LiteLLM message content for a user turn.

    Text-only turns keep a plain string (preserving cache identity with
    historical requests); turns with attachments use typed content parts —
    image_url data URIs for images, extracted text blocks for documents.
    """
    if not attachments:
        return text
    parts: list[dict] = [{"type": "text", "text": text}]
    for att in attachments:
        if att.kind == "image" and att.content_b64:
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{att.mime_type};base64,{att.content_b64}"
                    },
                }
            )
        elif att.extracted_text:
            parts.append(
                {
                    "type": "text",
                    "text": (
                        f"\n\n[Document: {att.filename}]\n"
                        "Answer using the document content below; "
                        "say so if it does not contain the answer.\n\n"
                        f"{att.extracted_text}"
                    ),
                }
            )
    return parts


def _history_content(db: Session, m: MessageRow) -> str | list[dict]:
    """Rebuild a stored message's content for the LiteLLM payload,
    re-attaching files that were part of that turn."""
    if m.role != "user":
        return m.content
    att_refs = (m.msg_metadata or {}).get("attachments") or []
    if not att_refs:
        return m.content
    attachments = session_service.get_attachments(
        db, [a["id"] for a in att_refs], m.session_id
    )
    return _user_content_parts(m.content, attachments)


def _build_messages(
    db: Session,
    system_prompt: str,
    history: list[MessageRow],
    new_content: str | list[dict],
) -> list[dict]:
    """Assemble the full LiteLLM payload: system + history + new message."""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": m.role, "content": _history_content(db, m)} for m in history
    )
    messages.append({"role": "user", "content": new_content})
    return messages


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()

    # Resolve attachments (scoped to this session).
    attachments: list[Attachment] = []
    if body.attachment_ids:
        attachments = session_service.get_attachments(
            db, body.attachment_ids, body.session_id
        )
        found = {a.id for a in attachments}
        missing = [i for i in body.attachment_ids if i not in found]
        if missing:
            raise HTTPException(422, "invalid or unknown attachment_id")

    # System prompt: request override > stored session override > default.
    system_prompt = (
        body.system_prompt
        or session_service.get_system_prompt(db, body.session_id)
        or settings.default_system_prompt
    )

    history = session_service.get_history(db, body.session_id)
    user_content = _user_content_parts(body.message, attachments)
    messages = _build_messages(db, system_prompt, history, user_content)

    simulate = None
    if settings.enable_failure_simulation:
        simulate = llm_service.parse_simulation_header(
            request.headers.get("X-Simulate-Failure")
        )

    try:
        reply, metadata = await llm_service.generate_reply(messages, simulate)
    except llm_service.AllProvidersUnavailable as exc:
        raise HTTPException(status_code=503, detail="all providers unavailable") from exc

    # Persist only after a successful inference.
    user_metadata = None
    if attachments:
        user_metadata = {
            "attachments": [
                {
                    "id": a.id,
                    "filename": a.filename,
                    "mime_type": a.mime_type,
                    "kind": a.kind,
                }
                for a in attachments
            ]
        }
    session_service.save_exchange(
        db=db,
        session_id=body.session_id,
        user_content=body.message,
        assistant_content=reply,
        assistant_metadata=metadata,
        system_prompt=body.system_prompt,
        user_metadata=user_metadata,
    )
    return ChatResponse(session_id=body.session_id, reply=reply, metadata=metadata)

"""POST /chat — the only inference endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services import llm_service, session_service

router = APIRouter()


def _build_messages(
    system_prompt: str, history: list, new_message: str
) -> list[dict]:
    """Assemble the full LiteLLM payload: system + history + new message."""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": m.role, "content": m.content} for m in history)
    messages.append({"role": "user", "content": new_message})
    return messages


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()

    # System prompt: request override > stored session override > default.
    system_prompt = (
        body.system_prompt
        or session_service.get_system_prompt(db, body.session_id)
        or settings.default_system_prompt
    )

    history = session_service.get_history(db, body.session_id)
    messages = _build_messages(system_prompt, history, body.message)

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
    session_service.save_exchange(
        db=db,
        session_id=body.session_id,
        user_content=body.message,
        assistant_content=reply,
        assistant_metadata=metadata,
        system_prompt=body.system_prompt,
    )
    return ChatResponse(session_id=body.session_id, reply=reply, metadata=metadata)

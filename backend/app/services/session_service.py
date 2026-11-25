"""SQLite-backed persistence for sessions, messages, and attachments."""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.models import Attachment, Message, Session


def session_exists(db: OrmSession, session_id: str) -> bool:
    return db.scalar(select(Session.id).where(Session.session_id == session_id)) is not None


def get_system_prompt(db: OrmSession, session_id: str) -> str | None:
    return db.scalar(select(Session.system_prompt).where(Session.session_id == session_id))


def get_history(db: OrmSession, session_id: str) -> list[Message]:
    """Conversation messages in chronological order (system prompt excluded)."""
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at, Message.id)
    )
    return list(db.scalars(stmt))


def get_attachments(db: OrmSession, ids: list[str], session_id: str) -> list[Attachment]:
    """Fetch attachments by id, scoped to the session. Order preserved."""
    if not ids:
        return []
    rows = db.scalars(
        select(Attachment).where(
            Attachment.id.in_(ids), Attachment.session_id == session_id
        )
    ).all()
    by_id = {a.id: a for a in rows}
    return [by_id[i] for i in ids if i in by_id]


def save_exchange(
    db: OrmSession,
    session_id: str,
    user_content: str,
    assistant_content: str,
    assistant_metadata: dict,
    system_prompt: str | None,
    user_metadata: dict | None = None,
) -> None:
    """Persist a successful exchange. Called ONLY after successful inference,
    so failed requests never modify conversation history."""
    session = db.scalar(select(Session).where(Session.session_id == session_id))
    if session is None:
        session = Session(session_id=session_id, system_prompt=system_prompt)
        db.add(session)
    elif system_prompt is not None:
        session.system_prompt = system_prompt

    db.add(
        Message(
            session_id=session_id,
            role="user",
            content=user_content,
            msg_metadata=user_metadata,
        )
    )
    db.add(
        Message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            msg_metadata=assistant_metadata,
        )
    )
    db.commit()

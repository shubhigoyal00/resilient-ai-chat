"""GET /sessions/{session_id}/messages — stored history, chronological."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import StoredMessage
from app.services import session_service

router = APIRouter()


@router.get("/sessions/{session_id}/messages", response_model=list[StoredMessage])
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    if not session_service.session_exists(db, session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return [
        StoredMessage(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            metadata=m.msg_metadata,
            created_at=m.created_at,
        )
        for m in session_service.get_history(db, session_id)
    ]

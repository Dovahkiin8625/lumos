"""/api/sessions/{id}/messages 路由。"""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import MessageOut, ChatMessageRequest
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User
from lumos.persistence.repositories.sessions import ChatSessionRepository
from lumos.persistence.repositories.messages import MessageRepository


router = APIRouter(prefix="/api/sessions/{session_id}/messages", tags=["messages"])


def _to_out(m) -> MessageOut:
    tcs = None
    if m.tool_calls:
        try:
            tcs = json.loads(m.tool_calls)
        except Exception:
            tcs = None
    return MessageOut(
        id=m.id, role=m.role, content=m.content,
        tool_calls=tcs, tool_call_id=m.tool_call_id, name=m.name,
        prompt_tokens=m.prompt_tokens,
        completion_tokens=m.completion_tokens,
        created_at=m.created_at,
    )


@router.get("", response_model=list[MessageOut])
async def list_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cs_repo = ChatSessionRepository(db)
    cs = await cs_repo.get(session_id, user.id)
    if cs is None:
        raise HTTPException(404, "session not found")
    repo = MessageRepository(db)
    rows = await repo.list_by_session(session_id)
    return [_to_out(r) for r in rows]
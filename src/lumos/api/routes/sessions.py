"""/api/sessions 路由。"""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import SessionCreate, SessionUpdate, SessionOut
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User
from lumos.persistence.repositories.sessions import ChatSessionRepository


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _to_out(cs) -> SessionOut:
    try:
        skills = json.loads(cs.enabled_skills or "[]")
    except Exception:
        skills = []
    return SessionOut(
        id=cs.id, title=cs.title, enabled_skills=skills,
        created_at=cs.created_at, updated_at=cs.updated_at,
    )


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    rows = await repo.list_by_user(user.id)
    return [_to_out(r) for r in rows]


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    req: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    title = req.title or "新会话"
    cs = await repo.create(user_id=user.id, title=title)
    if req.enabled_skills:
        await repo.update_skills(cs.id, json.dumps(req.enabled_skills))
    return _to_out(cs)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    cs = await repo.get(session_id, user.id)
    if cs is None:
        raise HTTPException(404, "session not found")
    return _to_out(cs)


@router.patch("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: str,
    req: SessionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    cs = await repo.get(session_id, user.id)
    if cs is None:
        raise HTTPException(404, "session not found")
    if req.title is not None:
        await repo.update_title(session_id, req.title)
    if req.enabled_skills is not None:
        await repo.update_skills(session_id, json.dumps(req.enabled_skills))
    cs = await repo.get(session_id, user.id)
    return _to_out(cs)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    ok = await repo.delete(session_id, user.id)
    if not ok:
        raise HTTPException(404, "session not found")
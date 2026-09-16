""" /api/skills 路由（最终版）。"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import SkillOut
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
async def list_skills(request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    return [
        SkillOut(
            name=s.name, description=s.description,
            enabled=s.enabled,
            required_tools=s.required_tools,
            optional_tools=s.optional_tools,
        )
        for s in sm.list_all()
    ]


@router.post("/{name}/enable", status_code=204)
async def enable_skill(name: str, request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    if sm.get(name) is None:
        raise HTTPException(404, "skill not found")
    sm.enable(name)


@router.post("/{name}/disable", status_code=204)
async def disable_skill(name: str, request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    if sm.get(name) is None:
        raise HTTPException(404, "skill not found")
    sm.disable(name)
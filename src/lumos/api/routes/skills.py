"""/api/skills 路由：list / CRUD / enable / disable / reload。"""
from __future__ import annotations
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from lumos.api.schemas import SkillCreate, SkillOut, SkillUpdate
from lumos.api.deps import get_current_user
from lumos.errors import LumosError
from lumos.persistence.models import User
from lumos.skills.manager import (
    InvalidSkillNameError,
    SkillAlreadyExistsError,
    SkillNotFoundError,
)


router = APIRouter(prefix="/api/skills", tags=["skills"])
_log = structlog.get_logger()


def _to_out(s) -> SkillOut:
    return SkillOut(
        name=s.name,
        description=s.description,
        version=s.version,
        tags=s.tags,
        required_tools=s.required_tools,
        optional_tools=s.optional_tools,
        max_steps=s.max_steps,
        instructions=s.instructions,
        enabled=s.enabled,
        dir_path=str(s.dir_path),
    )


@router.get("", response_model=list[SkillOut])
async def list_skills(request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    return [_to_out(s) for s in sm.list_all()]


@router.post("", response_model=SkillOut, status_code=201)
async def create_skill(
    req: SkillCreate,
    request: Request,
    user: User = Depends(get_current_user),
):
    sm = request.app.state.skill_manager
    try:
        created = sm.add(
            name=req.name,
            description=req.description,
            version=req.version,
            tags=req.tags,
            required_tools=req.required_tools,
            optional_tools=req.optional_tools,
            max_steps=req.max_steps,
            instructions=req.instructions,
        )
    except InvalidSkillNameError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SkillAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except LumosError as e:
        _log.error("skill.create_failed", name=req.name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    return _to_out(created)


@router.get("/{name}", response_model=SkillOut)
async def get_skill(name: str, request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    s = sm.get(name)
    if s is None:
        raise HTTPException(status_code=404, detail="skill not found")
    return _to_out(s)


@router.put("/{name}", response_model=SkillOut)
async def update_skill(
    name: str,
    req: SkillUpdate,
    request: Request,
    user: User = Depends(get_current_user),
):
    sm = request.app.state.skill_manager
    try:
        updated = sm.update(
            name,
            description=req.description,
            version=req.version,
            tags=req.tags,
            required_tools=req.required_tools,
            optional_tools=req.optional_tools,
            max_steps=req.max_steps,
            instructions=req.instructions,
        )
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LumosError as e:
        _log.error("skill.update_failed", name=name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    return _to_out(updated)


@router.delete("/{name}", status_code=204)
async def delete_skill(name: str, request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    try:
        sm.remove(name)
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LumosError as e:
        _log.error("skill.delete_failed", name=name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/reload", status_code=204)
async def reload_skills(request: Request, user: User = Depends(get_current_user)):
    """手动重新扫描所有配置的 skills 目录。"""
    request.app.state.skill_manager.reload()

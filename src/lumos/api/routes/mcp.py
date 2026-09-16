"""/api/mcp/servers 路由。"""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import McpServerCreate, McpServerOut
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User
from lumos.persistence.repositories.mcp_servers import McpServerRepository
from lumos.mcp.config import McpServerConfig
from lumos.mcp.client import McpClient
from lumos.errors import McpConnectionError


router = APIRouter(prefix="/api/mcp/servers", tags=["mcp"])


def _to_out(ms) -> McpServerOut:
    try:
        cfg = json.loads(ms.config)
    except Exception:
        cfg = {}
    return McpServerOut(
        id=ms.id, name=ms.name, transport=cfg.get("transport", "stdio"),
        enabled=ms.enabled, config=cfg,
    )


@router.get("", response_model=list[McpServerOut])
async def list_servers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    rows = await repo.list_by_user(user.id)
    return [_to_out(r) for r in rows]


@router.post("", response_model=McpServerOut, status_code=201)
async def create_server(
    req: McpServerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    cfg_dict = req.model_dump()
    ms = await repo.upsert(
        user_id=user.id, name=req.name,
        config_json=json.dumps(cfg_dict), enabled=req.enabled,
    )
    return _to_out(ms)


@router.patch("/{server_id}", response_model=McpServerOut)
async def update_server(
    server_id: str,
    req: McpServerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    existing = await repo.get(server_id, user.id)
    if existing is None:
        raise HTTPException(404, "server not found")
    cfg_dict = req.model_dump()
    ms = await repo.upsert(
        user_id=user.id, name=req.name,
        config_json=json.dumps(cfg_dict), enabled=req.enabled,
    )
    return _to_out(ms)


@router.delete("/{server_id}", status_code=204)
async def delete_server(
    server_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    ok = await repo.delete(server_id, user.id)
    if not ok:
        raise HTTPException(404, "server not found")


@router.post("/{server_id}/test")
async def test_server(
    server_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    ms = await repo.get(server_id, user.id)
    if ms is None:
        raise HTTPException(404, "server not found")
    cfg = json.loads(ms.config)
    mcp_cfg = McpServerConfig(
        name=ms.name, transport=cfg["transport"], enabled=True,
        command=cfg.get("command"), args=tuple(cfg.get("args", [])),
        env=cfg.get("env", {}),
        url=cfg.get("url"), headers=cfg.get("headers", {}),
    )
    client = McpClient(mcp_cfg)
    try:
        await client.connect()
        return {"ok": True, "tools_count": len(await client.list_tools())}
    except McpConnectionError as e:
        return {"ok": False, "error": str(e)}
    finally:
        await client.disconnect()
"""/api/health 端点。"""
from __future__ import annotations
from fastapi import APIRouter, Request
from sqlalchemy import text
from lumos.api.schemas import HealthResponse
from lumos import __version__


router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    # 检查DB
    from sqlalchemy.ext.asyncio import async_sessionmaker
    factory = async_sessionmaker(request.app.state.engine, expire_on_commit=False)
    db_status = "ok"
    try:
        async with factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    # 检查Provider/MCP
    providers = {"openai_compat": "ok"}
    mcp_statuses: dict[str, str] = {}
    mgr = getattr(request.app.state, "mcp_manager", None)
    if mgr is not None:
        for name, client in mgr._clients.items():
            mcp_statuses[name] = "connected" if client else "disconnected"
    overall = "ok" if db_status == "ok" else "degraded"
    return HealthResponse(
        status=overall, version=__version__,
        providers=providers, mcp_servers=mcp_statuses, db=db_status,
    )
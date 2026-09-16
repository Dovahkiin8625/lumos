"""FastAPI应用工厂（一阶段最小版，后续Task扩展）。"""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession
from lumos.config import LumosConfig, set_config
from lumos.persistence.db import get_engine, init_db
from lumos.providers.openai_compat import OpenAICompatProvider
from lumos.providers.base import BaseProvider
from lumos.tools.registry import ToolRegistry
from lumos.skills.manager import SkillManager
from lumos.mcp.manager import McpManager
from lumos.mcp.config import McpServerConfig
from lumos.api.routes.auth import router as auth_router
from lumos.api.runners import Runners
from lumos.api.middleware import register_middlewares


def create_app(config: LumosConfig, *, for_testing: bool = False) -> FastAPI:
    set_config(config)
    app = FastAPI(title="Lumos", version="0.1.0")
    register_middlewares(app)
    app.state.config = config

    @app.on_event("startup")
    async def _startup():
        eng = get_engine(config.db.url, echo=config.db.echo)
        app.state.engine = eng
        if for_testing:
            await init_db(eng)
        else:
            await init_db(eng)
        app.state.provider = OpenAICompatProvider(
            base_url=config.provider.base_url,
            api_key=config.provider.api_key,
            model=config.provider.model,
            timeout=config.provider.timeout,
        )
        app.state.tool_registry = ToolRegistry()
        app.state.tool_registry.discover()
        # 注入ToolsConfig到需要它的工具
        from lumos.tools.builtin.file_ops import FileReadTool, FileWriteTool
        for tool in app.state.tool_registry._tools.values():
            if isinstance(tool, (FileReadTool, FileWriteTool)):
                tool.config = config.tools
        app.state.skill_manager = SkillManager(discover_dirs=config.skills.dirs)
        app.state.skill_manager.discover()
        mcp_configs = [
            McpServerConfig(
                name=s.name, transport=s.transport, enabled=s.enabled,
                command=s.command, args=tuple(s.args), env=s.env,
                url=s.url, headers=s.headers,
            )
            for s in config.mcp.servers
        ]
        app.state.mcp_manager = McpManager(mcp_configs)
        await app.state.mcp_manager.connect_all()
        await app.state.mcp_manager.refresh_tools_cache()

    @app.on_event("shutdown")
    async def _shutdown():
        if hasattr(app.state, "mcp_manager"):
            await app.state.mcp_manager.shutdown()

    app.state.runners = Runners()
    app.include_router(auth_router)
    from lumos.api.routes.sessions import router as sessions_router
    from lumos.api.routes.messages import router as messages_router
    from lumos.api.routes.ws import router as ws_router
    from lumos.api.routes.skills import router as skills_router
    from lumos.api.routes.mcp import router as mcp_router
    from lumos.api.routes.health import router as health_router
    app.include_router(sessions_router)
    app.include_router(messages_router)
    app.include_router(ws_router)
    app.include_router(skills_router)
    app.include_router(mcp_router)
    app.include_router(health_router)
    return app
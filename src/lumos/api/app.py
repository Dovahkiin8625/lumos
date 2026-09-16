"""FastAPI应用工厂。"""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import async_sessionmaker
from lumos.config import LumosConfig, set_config
from lumos.persistence.db import get_engine, init_db
from lumos.providers.openai_compat import OpenAICompatProvider
from lumos.tools.registry import ToolRegistry
from lumos.tools.builtin.file_ops import FileReadTool, FileWriteTool
from lumos.skills.manager import SkillManager
from lumos.mcp.manager import McpManager
from lumos.mcp.config import McpServerConfig
from lumos.api.middleware import register_middlewares
from lumos.api.routes.auth import router as auth_router
from lumos.api.routes.sessions import router as sessions_router
from lumos.api.routes.messages import router as messages_router
from lumos.api.routes.skills import router as skills_router
from lumos.api.routes.mcp import router as mcp_router
from lumos.api.routes.health import router as health_router
from lumos.api.routes.ws import router as ws_router
from lumos.api.runners import Runners
from lumos.logging import configure_logging, get_logger


def create_app(config: LumosConfig, *, for_testing: bool = False) -> FastAPI:
    set_config(config)
    configure_logging(config.log_level)
    log = get_logger("app")
    app = FastAPI(title="Lumos", version="0.1.0")
    app.state.config = config
    register_middlewares(app)

    @app.on_event("startup")
    async def _startup():
        if not for_testing and not config.auth.jwt_secret:
            raise RuntimeError("auth.jwt_secret must be set")
        eng = get_engine(config.db.url, echo=config.db.echo)
        app.state.engine = eng
        await init_db(eng)
        # 首次启动创建默认admin
        from sqlalchemy import select
        from lumos.persistence.repositories.users import UserRepository
        from lumos.api.auth_utils import hash_password
        factory = async_sessionmaker(eng, expire_on_commit=False)
        async with factory() as db:
            repo = UserRepository(db)
            if (await repo.get_by_email(config.auth.default_admin_email or "")) is None:
                if config.auth.default_admin_email and config.auth.default_admin_password:
                    await repo.create(
                        email=config.auth.default_admin_email,
                        password_hash=hash_password(
                            config.auth.default_admin_password,
                            rounds=config.auth.bcrypt_rounds,
                        ),
                    )
                    log.info("default_admin_created", email=config.auth.default_admin_email)
        app.state.provider = OpenAICompatProvider(
            base_url=config.provider.base_url,
            api_key=config.provider.api_key,
            model=config.provider.model,
            timeout=config.provider.timeout,
        )
        app.state.tool_registry = ToolRegistry()
        app.state.tool_registry.discover()
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
        app.state.runners = Runners()
        log.info("app.startup_complete")

    @app.on_event("shutdown")
    async def _shutdown():
        if hasattr(app.state, "mcp_manager"):
            await app.state.mcp_manager.shutdown()
        if hasattr(app.state, "engine"):
            await app.state.engine.dispose()

    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(messages_router)
    app.include_router(skills_router)
    app.include_router(mcp_router)
    app.include_router(health_router)
    app.include_router(ws_router)

    # 静态前端
    web_dir = Path(__file__).parent.parent / "web"
    if web_dir.exists() and not for_testing:
        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(web_dir / "index.html")
        @app.get("/login", include_in_schema=False)
        async def serve_login():
            return FileResponse(web_dir / "login.html")
        app.mount("/static", StaticFiles(directory=web_dir), name="static")

    return app
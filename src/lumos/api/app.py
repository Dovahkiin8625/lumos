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
from lumos.api.routes.knowledge_bases import router as knowledge_bases_router
from lumos.knowledge.manager import KnowledgeManager
from lumos.knowledge.vector_client import VectorServiceClient
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

        # 知识库：构造 VectorServiceClient 与 KnowledgeManager（薄编排）
        app.state.vector_service_client = VectorServiceClient(config.knowledge_base)
        app.state.knowledge_manager = KnowledgeManager(
            config.knowledge_base,
            app.state.vector_service_client,
            factory,
        )
        # 异步后台：尝试加载 BGE-M3 + rerank 模型（失败仅记录日志，不阻塞启动）
        import asyncio
        async def _load_models() -> None:
            try:
                await app.state.vector_service_client.ensure_models_loaded()
            except Exception as e:
                log.warning("vector_service_load_models_failed", error=str(e))
        asyncio.create_task(_load_models())

        log.info("app.startup_complete")

    @app.on_event("shutdown")
    async def _shutdown():
        if hasattr(app.state, "mcp_manager"):
            await app.state.mcp_manager.shutdown()
        if hasattr(app.state, "vector_service_client"):
            await app.state.vector_service_client.close()
        if hasattr(app.state, "engine"):
            await app.state.engine.dispose()

    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(messages_router)
    app.include_router(skills_router)
    app.include_router(mcp_router)
    app.include_router(health_router)
    app.include_router(knowledge_bases_router)
    app.include_router(ws_router)

    # 静态前端（SPA，由 Vite 构建到 frontend/dist）
    # repo_root/src/lumos/api/app.py → 上溯三级到 repo_root
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    dist = repo_root / "frontend" / "dist"
    if dist.exists() and not for_testing:
        # 1) 真实静态文件（assets/*）—— StaticFiles 优先级最高
        assets_dir = dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # 2) favicon.svg 显式路由（避免被下面的 catch-all 误吞）
        if (dist / "favicon.svg").exists():
            @app.get("/favicon.svg", include_in_schema=False)
            async def favicon():
                return FileResponse(dist / "favicon.svg")

        # 3) 显式根路径与 SPA 路由 fallback（/chat、/login 等 Vue Router 路径）
        @app.get("/", include_in_schema=False)
        async def serve_spa_root():
            return FileResponse(dist / "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            # 兜底真正的 SPA 客户端路由。``/api/*`` / ``/ws/*`` / ``/assets/*`` / ``/favicon*``
            # 都在上面通过 ``include_router`` 或 ``StaticFiles`` 优先匹配，根本不会到这里。
            return FileResponse(dist / "index.html")

    return app
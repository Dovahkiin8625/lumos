"""API集成测试fixture：内存DB + FastAPI TestClient。"""
from __future__ import annotations
import os
from typing import AsyncIterator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lumos.config import (
    LumosConfig, ServerConfig, ProviderConfig, DbConfig,
    ToolsConfig, SkillsConfig, McpConfig, AuthConfig, AgentConfig, set_config,
)
from lumos.persistence.db import get_engine, init_db
from lumos.api.app import create_app


@pytest_asyncio.fixture
async def app() -> AsyncIterator:
    cfg = LumosConfig(
        server=ServerConfig(host="127.0.0.1", port=8000),
        provider=ProviderConfig(
            type="openai_compat",
            base_url="http://localhost/v1",
            api_key="test",
            model="gpt-test",
        ),
        db=DbConfig(url="sqlite+aiosqlite:///:memory:"),
        tools=ToolsConfig(),
        skills=SkillsConfig(dirs=[]),
        mcp=McpConfig(servers=[]),
        auth=AuthConfig(jwt_secret="test-secret-32-bytes-long-string", access_ttl=3600, refresh_ttl=7200),
        agent=AgentConfig(),
    )
    set_config(cfg)
    application = create_app(cfg, for_testing=True)
    # ASGITransport 不会自动触发 startup/shutdown 事件，需手动运行 lifespan。
    async with application.router.lifespan_context(application):
        yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
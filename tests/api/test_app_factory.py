"""测试应用工厂。"""
from __future__ import annotations
from pathlib import Path
import pytest
from fastapi.routing import APIRoute
from lumos.config import (
    LumosConfig, ServerConfig, ProviderConfig, DbConfig,
    ToolsConfig, SkillsConfig, McpConfig, AuthConfig, AgentConfig,
)
from lumos.api.app import create_app


def _all_paths(app):
    """递归收集所有路由路径，兼容嵌套的 _IncludedRouter。"""
    paths = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            paths.append(r.path)
        else:
            sub_routes = getattr(r, "routes", None) or []
            if not sub_routes:
                sub_routes = getattr(getattr(r, "original_router", None), "routes", []) or []
            for sub in sub_routes:
                if isinstance(sub, APIRoute):
                    paths.append(sub.path)
    return paths


def test_create_app_smoke(tmp_path: Path):
    cfg = LumosConfig(
        server=ServerConfig(),
        provider=ProviderConfig(
            type="openai_compat", base_url="http://localhost",
            api_key="k", model="m",
        ),
        db=DbConfig(url="sqlite+aiosqlite:///:memory:"),
        tools=ToolsConfig(),
        skills=SkillsConfig(dirs=[]),
        mcp=McpConfig(),
        auth=AuthConfig(jwt_secret="test-secret-32-bytes-long-string"),
        agent=AgentConfig(),
    )
    app = create_app(cfg, for_testing=True)
    assert app.title == "Lumos"
    routes = _all_paths(app)
    assert "/api/auth/register" in routes
    assert "/api/sessions" in routes
    assert "/api/health" in routes
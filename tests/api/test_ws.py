"""测试WebSocket流式协议（使用mock provider）。"""
from __future__ import annotations
import asyncio
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def mock_provider(monkeypatch):
    """替换OpenAICompatProvider.chat为脚本化响应。"""
    from lumos.agent.message import ToolCall, Usage

    class FakeProvider:
        async def chat(self, messages, *, system, tools, temperature,
                       max_tokens, cancel, on_text):
            if on_text:
                await on_text("Hello")
                await on_text(" world")
            return "Hello world", [], Usage(10, 5, 15)

    # 重启app的provider为FakeProvider
    yield FakeProvider


@pytest.mark.asyncio
async def test_ws_simple_chat(mock_provider):
    """WebSocket流式对话：替换provider，验证text事件流和done。"""
    from lumos.config import (
        LumosConfig, ServerConfig, ProviderConfig, DbConfig,
        ToolsConfig, SkillsConfig, McpConfig, AuthConfig, AgentConfig, set_config,
    )
    from lumos.api.app import create_app
    from fastapi.testclient import TestClient

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
        auth=AuthConfig(
            jwt_secret="test-secret-32-bytes-long-string",
            access_ttl=3600,
            refresh_ttl=7200,
        ),
        agent=AgentConfig(),
    )
    set_config(cfg)
    application = create_app(cfg, for_testing=True)
    # 用TestClient上下文管理器驱动lifespan；进入后再替换provider避免被startup覆盖。
    with TestClient(application) as client:
        application.state.provider = mock_provider()
        # 注册并创建session
        r = client.post("/api/auth/register", json={
            "email": "a@b.com", "password": "hunter22pass",
        })
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        H = {"Authorization": f"Bearer {token}"}
        r = client.post("/api/sessions", json={}, headers=H)
        assert r.status_code == 201, r.text
        sid = r.json()["id"]

        with client.websocket_connect(f"/ws/sessions/{sid}?token={token}") as ws:
            ws.send_text(json.dumps({
                "type": "user_message", "content": "hi", "enabled_skills": [],
            }))
            events: list[dict] = []
            for _ in range(50):
                try:
                    msg = ws.receive_text()
                except Exception:
                    break
                e = json.loads(msg)
                events.append(e)
                if e["type"] == "done":
                    break
            text_events = [e for e in events if e["type"] == "text"]
            assert any(e["data"]["delta"] == "Hello" for e in text_events)
            assert any(e["data"]["delta"] == " world" for e in text_events)
            assert any(e["type"] == "done" for e in events)
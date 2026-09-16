"""测试MCP管理路由。"""
from __future__ import annotations
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _auth(c: AsyncClient) -> str:
    r = await c.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_list_delete_mcp_server(client: AsyncClient):
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/mcp/servers", json={
        "name": "fs", "transport": "stdio",
        "command": "echo", "args": ["hello"],
    }, headers=H)
    assert r.status_code == 201
    sid = r.json()["id"]

    r = await client.get("/api/mcp/servers", headers=H)
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    r = await client.delete(f"/api/mcp/servers/{sid}", headers=H)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_update_mcp_server(client: AsyncClient):
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/mcp/servers", json={
        "name": "fs", "transport": "stdio",
        "command": "echo", "args": ["hello"],
    }, headers=H)
    assert r.status_code == 201
    sid = r.json()["id"]

    r = await client.patch(f"/api/mcp/servers/{sid}", json={
        "name": "fs", "transport": "stdio",
        "command": "echo", "args": ["world"],
        "enabled": False,
    }, headers=H)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == sid
    assert data["enabled"] is False


@pytest.mark.asyncio
async def test_test_mcp_server_connection(client: AsyncClient):
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/mcp/servers", json={
        "name": "fs", "transport": "stdio",
        "command": "echo", "args": ["hello"],
    }, headers=H)
    assert r.status_code == 201
    sid = r.json()["id"]

    r = await client.post(f"/api/mcp/servers/{sid}/test", headers=H)
    assert r.status_code == 200
    body = r.json()
    # echo 不实现 MCP 协议，所以会返回 ok=False（连接/初始化失败）
    assert "ok" in body
    if not body["ok"]:
        assert "error" in body
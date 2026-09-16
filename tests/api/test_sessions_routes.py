"""测试会话路由。"""
from __future__ import annotations
import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    r = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_list_get_delete_session(client: AsyncClient):
    token = await _register(client)
    H = {"Authorization": f"Bearer {token}"}

    # 创建
    r = await client.post("/api/sessions", json={"title": "测试会话"}, headers=H)
    assert r.status_code == 201
    sid = r.json()["id"]

    # 列出
    r = await client.get("/api/sessions", headers=H)
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    # 详情
    r = await client.get(f"/api/sessions/{sid}", headers=H)
    assert r.status_code == 200

    # 删除
    r = await client.delete(f"/api/sessions/{sid}", headers=H)
    assert r.status_code == 204

    # 删除后再访问
    r = await client.get(f"/api/sessions/{sid}", headers=H)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_session_user_isolation(client: AsyncClient):
    token_a = await _register(client)
    # 第二个用户
    await client.post("/api/auth/register", json={
        "email": "b@b.com", "password": "hunter22pass",
    })
    r = await client.post("/api/auth/login", json={
        "email": "b@b.com", "password": "hunter22pass",
    })
    token_b = r.json()["access_token"]

    # A创建一个session
    r = await client.post("/api/sessions", json={}, headers={"Authorization": f"Bearer {token_a}"})
    sid_a = r.json()["id"]

    # B尝试访问应403/404
    r = await client.get(f"/api/sessions/{sid_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code in (403, 404)
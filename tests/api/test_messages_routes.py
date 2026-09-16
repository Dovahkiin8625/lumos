"""测试消息路由（同步发送会失败因为需要LLM，仅测试history）。"""
from __future__ import annotations
import pytest
from httpx import AsyncClient


async def _auth_and_session(client: AsyncClient):
    r = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    token = r.json()["access_token"]
    r = await client.post("/api/sessions", json={}, headers={"Authorization": f"Bearer {token}"})
    return token, r.json()["id"]


@pytest.mark.asyncio
async def test_list_messages_empty(client: AsyncClient):
    token, sid = await _auth_and_session(client)
    r = await client.get(f"/api/sessions/{sid}/messages", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []
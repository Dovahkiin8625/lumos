"""测试认证路由。"""
from __future__ import annotations
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_me(client: AsyncClient):
    # 注册
    r = await client.post("/api/auth/register", json={
        "email": "alice@example.com", "password": "hunter22pass",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert "access_token" in data
    access = data["access_token"]

    # /me
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    r = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    r = await client.post("/api/auth/login", json={
        "email": "a@b.com", "password": "wrong-password",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    refresh = reg.json()["refresh_token"]
    r = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_logout_revokes_refresh(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    refresh = reg.json()["refresh_token"]
    r = await client.post("/api/auth/logout", json={"refresh_token": refresh})
    assert r.status_code == 204
    # 再用同一个refresh刷新应失败
    r2 = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_unauthorized_me(client: AsyncClient):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
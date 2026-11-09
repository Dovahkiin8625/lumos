"""测试Skills管理路由。"""
from __future__ import annotations
from pathlib import Path
import textwrap
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def app_with_skill(app, tmp_path):
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()
    (skill_dir / "demo").mkdir()
    (skill_dir / "demo" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: demo
        description: Demo skill
        ---
        Demo instructions.
    """), encoding="utf-8")
    app.state.skill_manager = app.state.skill_manager.__class__(
        discover_dirs=[skill_dir],
    )
    app.state.skill_manager.discover()
    yield app, skill_dir


async def _register_and_token(client) -> str:
    r = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_list_skills(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _skill_dir = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.get("/api/skills", headers=H)
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "demo" in names

        r = await client.post("/api/skills/demo/disable", headers=H)
        assert r.status_code == 204

        r = await client.post("/api/skills/demo/enable", headers=H)
        assert r.status_code == 204


@pytest.mark.asyncio
async def test_create_skill(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, skill_dir = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.post("/api/skills", headers=H, json={
            "name": "newone",
            "description": "created via api",
            "instructions": "do the work",
        })
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "newone"
        assert body["description"] == "created via api"
        assert body["enabled"] is True
        # file is on disk in the first configured skills dir
        assert (skill_dir / "newone" / "SKILL.md").is_file()
        # and visible in list
        r = await client.get("/api/skills", headers=H)
        assert any(s["name"] == "newone" for s in r.json())


@pytest.mark.asyncio
async def test_create_skill_rejects_negative_max_steps(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.post("/api/skills", headers=H, json={
            "name": "negstep", "max_steps": 0,
        })
        assert r.status_code == 422
        r = await client.post("/api/skills", headers=H, json={
            "name": "negstep", "max_steps": -3,
        })
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_skill_rejects_oversized_max_steps(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.post("/api/skills", headers=H, json={
            "name": "bigstep", "max_steps": 9999,
        })
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_skill_rejects_negative_max_steps(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.put("/api/skills/demo", headers=H, json={"max_steps": -1})
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_skill_rejects_bad_name(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.post("/api/skills", headers=H, json={
            "name": "Has Spaces",
            "description": "x",
        })
        assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_skill_rejects_duplicate(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        payload = {"name": "demo", "description": "dup"}
        r = await client.post("/api/skills", headers=H, json=payload)
        assert r.status_code == 409


@pytest.mark.asyncio
async def test_get_single_skill(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.get("/api/skills/demo", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "demo"
        assert "instructions" in body and "Demo instructions" in body["instructions"]


@pytest.mark.asyncio
async def test_get_unknown_skill_returns_404(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.get("/api/skills/ghost", headers=H)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_skill(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, skill_dir = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.put("/api/skills/demo", headers=H, json={
            "description": "updated",
            "instructions": "new body",
            "version": "2.0.0",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["description"] == "updated"
        assert body["version"] == "2.0.0"
        assert "new body" in body["instructions"]
        # persisted
        raw = (skill_dir / "demo" / "SKILL.md").read_text(encoding="utf-8")
        assert "new body" in raw


@pytest.mark.asyncio
async def test_update_unknown_skill_returns_404(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.put("/api/skills/ghost", headers=H, json={"description": "x"})
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_skill(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, skill_dir = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.delete("/api/skills/demo", headers=H)
        assert r.status_code == 204
        assert not (skill_dir / "demo").exists()
        # and 404 thereafter
        r = await client.get("/api/skills/demo", headers=H)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_unknown_skill_returns_404(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, _ = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.delete("/api/skills/ghost", headers=H)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_skill_returns_500_when_no_dirs_configured(app, tmp_path):
    """空 dirs 配置触发 LumosError（'no skills dirs configured'），应转为 500 而不是 traceback。"""
    from httpx import ASGITransport, AsyncClient
    app.state.skill_manager = app.state.skill_manager.__class__(discover_dirs=[])
    app.state.skill_manager.reload()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        r = await client.post("/api/skills", headers=H, json={"name": "x"})
        assert r.status_code == 500
        assert "no skills dirs configured" in r.json()["detail"]


@pytest.mark.asyncio
async def test_reload_endpoint(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    app, skill_dir = app_with_skill
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_token(client)
        H = {"Authorization": f"Bearer {token}"}
        # write a new skill directly to disk
        (skill_dir / "ondisk").mkdir()
        (skill_dir / "ondisk" / "SKILL.md").write_text(
            "---\nname: ondisk\ndescription: external\n---\nbody\n",
            encoding="utf-8",
        )
        # before reload, manager doesn't see it
        r = await client.get("/api/skills", headers=H)
        assert "ondisk" not in [s["name"] for s in r.json()]
        # after reload, visible
        r = await client.post("/api/skills/reload", headers=H)
        assert r.status_code == 204
        r = await client.get("/api/skills", headers=H)
        assert any(s["name"] == "ondisk" for s in r.json())
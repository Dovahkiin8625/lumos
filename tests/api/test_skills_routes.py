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
    yield app


@pytest.mark.asyncio
async def test_list_skills(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_with_skill)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/auth/register", json={
            "email": "a@b.com", "password": "hunter22pass",
        })
        token = r.json()["access_token"]
        H = {"Authorization": f"Bearer {token}"}
        r = await client.get("/api/skills", headers=H)
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "demo" in names

        r = await client.post("/api/skills/demo/disable", headers=H)
        assert r.status_code == 204

        r = await client.post("/api/skills/demo/enable", headers=H)
        assert r.status_code == 204
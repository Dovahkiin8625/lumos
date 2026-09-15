"""测试DB初始化和Session工厂。"""
from __future__ import annotations
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from lumos.persistence.db import get_engine, get_session_factory, init_db, drop_db


@pytest.fixture
async def engine():
    eng = get_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield eng
    await eng.dispose()


@pytest.mark.asyncio
async def test_init_and_drop_db(engine: AsyncEngine):
    await init_db(engine)
    factory = get_session_factory(engine)
    async with factory() as session:
        from sqlalchemy import text
        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = {row[0] for row in result}
    assert "users" in tables
    assert "chat_sessions" in tables
    assert "messages" in tables
    assert "mcp_servers" in tables
    assert "revoked_tokens" in tables
    await drop_db(engine)
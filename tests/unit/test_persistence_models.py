"""测试ORM模型定义和基本CRUD。"""
from __future__ import annotations
import pytest
from datetime import datetime
from lumos.persistence.db import get_engine, get_session_factory, init_db
from lumos.persistence.models import User, ChatSession, Message, McpServer


@pytest.fixture
async def session():
    eng = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(eng)
    factory = get_session_factory(eng)
    async with factory() as s:
        yield s
    await eng.dispose()


@pytest.mark.asyncio
async def test_create_user(session):
    user = User(
        id="u1", email="a@b.com", password_hash="h", is_active=True,
        created_at=datetime.now(),
    )
    session.add(user)
    await session.commit()
    found = await session.get(User, "u1")
    assert found is not None
    assert found.email == "a@b.com"


@pytest.mark.asyncio
async def test_create_session_and_message(session):
    user = User(
        id="u1", email="a@b.com", password_hash="h",
        is_active=True, created_at=datetime.now(),
    )
    session.add(user)
    chat = ChatSession(
        id="c1", user_id="u1", title="test",
        enabled_skills="[]", model_config="{}",
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    session.add(chat)
    msg = Message(
        id="m1", session_id="c1", role="user",
        content='{"text":"hi"}', tool_calls=None,
        tool_call_id=None, name=None,
        created_at=datetime.now(), prompt_tokens=0, completion_tokens=0,
    )
    session.add(msg)
    await session.commit()

    found = await session.get(Message, "m1")
    assert found is not None
    assert found.role == "user"

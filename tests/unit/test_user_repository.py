"""测试UserRepository。"""
from __future__ import annotations
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.persistence.db import get_engine, get_session_factory, init_db
from lumos.persistence.repositories.users import UserRepository


@pytest.fixture
async def session() -> AsyncSession:
    eng = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(eng)
    factory = get_session_factory(eng)
    async with factory() as s:
        yield s
    await eng.dispose()


@pytest.mark.asyncio
async def test_create_and_get(session: AsyncSession):
    repo = UserRepository(session)
    user = await repo.create(email="a@b.com", password_hash="h")
    assert user.id
    assert user.email == "a@b.com"

    found = await repo.get_by_email("a@b.com")
    assert found is not None
    assert found.id == user.id

    by_id = await repo.get_by_id(user.id)
    assert by_id is not None
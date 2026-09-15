"""DB引擎和Session工厂。"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
)
from lumos.persistence.models import Base


def get_engine(url: str, echo: bool = False) -> AsyncEngine:
    """创建异步SQLAlchemy引擎。"""
    return create_async_engine(url, echo=echo, future=True)


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """创建Session工厂。"""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine) -> None:
    """创建所有表（一阶段使用，二阶段切换Alembic）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db(engine: AsyncEngine) -> None:
    """删除所有表（仅测试用）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

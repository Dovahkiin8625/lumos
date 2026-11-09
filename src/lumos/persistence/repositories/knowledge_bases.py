"""知识库仓储。"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lumos.persistence.models import KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: str) -> list[KnowledgeBase]:
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.user_id == user_id)
            .order_by(KnowledgeBase.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, kb_id: str, user_id: str) -> KnowledgeBase | None:
        kb = await self.session.get(KnowledgeBase, kb_id)
        if kb is None or kb.user_id != user_id:
            return None
        return kb

    async def get_by_id(self, kb_id: str) -> KnowledgeBase | None:
        """后台任务使用，不校验 user_id。"""
        return await self.session.get(KnowledgeBase, kb_id)

    async def get_by_name(self, user_id: str, name: str) -> KnowledgeBase | None:
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.user_id == user_id, KnowledgeBase.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: str,
        name: str,
        description: str,
        embedding_model: str,
        rerank_model: str,
        chunk_size: int,
        chunk_overlap: int,
        milvus_collection: str,
        enabled: bool = True,
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            embedding_model=embedding_model,
            rerank_model=rerank_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            milvus_collection=milvus_collection,
            enabled=enabled,
        )
        self.session.add(kb)
        await self.session.commit()
        await self.session.refresh(kb)
        return kb

    async def update(
        self,
        kb_id: str,
        user_id: str,
        *,
        description: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        enabled: bool | None = None,
    ) -> KnowledgeBase | None:
        kb = await self.get(kb_id, user_id)
        if kb is None:
            return None
        if description is not None:
            kb.description = description
        if chunk_size is not None:
            kb.chunk_size = chunk_size
        if chunk_overlap is not None:
            kb.chunk_overlap = chunk_overlap
        if enabled is not None:
            kb.enabled = enabled
        await self.session.commit()
        await self.session.refresh(kb)
        return kb

    async def delete(self, kb_id: str, user_id: str) -> KnowledgeBase | None:
        kb = await self.get(kb_id, user_id)
        if kb is None:
            return None
        await self.session.delete(kb)
        await self.session.commit()
        return kb

    async def touch(self, kb_id: str) -> None:
        await self.session.execute(
            update(KnowledgeBase)
            .where(KnowledgeBase.id == kb_id)
            .values(updated_at=func.now())
        )
        await self.session.commit()

    async def list_by_collection(self, milvus_collection: str) -> list[KnowledgeBase]:
        """根据 milvus collection 名查找 KB（用于后台任务，不限用户）。"""
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.milvus_collection == milvus_collection,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

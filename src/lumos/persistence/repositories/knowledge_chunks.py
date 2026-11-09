"""知识库 chunk 元数据缓存仓储。

实际向量存储在 vector-service / Milvus 中；本表只保留可读字段以便：
- 列表查询 / 统计
- 在向量服务不可用时仍能展示文档结构
- 调试与审计
"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lumos.persistence.models import KnowledgeChunk


class KnowledgeChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_insert(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        self.session.add_all(chunks)
        await self.session.commit()

    async def list_by_doc(self, doc_id: str) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.doc_id == doc_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_kb(self, kb_id: str) -> int:
        from sqlalchemy import func as sqlfunc
        stmt = select(sqlfunc.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.kb_id == kb_id,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def delete_by_doc(self, doc_id: str) -> int:
        stmt = delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return int(result.rowcount or 0)

    async def delete_by_kb(self, kb_id: str) -> int:
        stmt = delete(KnowledgeChunk).where(KnowledgeChunk.kb_id == kb_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return int(result.rowcount or 0)

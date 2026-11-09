"""知识库文档仓储。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lumos.persistence.models import KnowledgeDocument


class KnowledgeDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        kb_id: str,
        filename: str,
        mime_type: str,
        file_path: str,
        file_size: int,
        doc_metadata: dict | None = None,
        page_count: int | None = None,
    ) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            id=str(uuid.uuid4()),
            kb_id=kb_id,
            filename=filename,
            mime_type=mime_type,
            file_path=file_path,
            file_size=file_size,
            page_count=page_count,
            doc_metadata=_json_dumps(doc_metadata or {}),
            status="pending",
        )
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def get(self, doc_id: str, kb_id: str) -> KnowledgeDocument | None:
        doc = await self.session.get(KnowledgeDocument, doc_id)
        if doc is None or doc.kb_id != kb_id:
            return None
        return doc

    async def list_by_kb(self, kb_id: str) -> list[KnowledgeDocument]:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.kb_id == kb_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        doc_id: str,
        status: str,
        *,
        error: str | None = None,
        chunk_count: int | None = None,
        page_count: int | None = None,
    ) -> None:
        values: dict[str, object] = {"status": status}
        if error is not None:
            values["error"] = error
        if chunk_count is not None:
            values["chunk_count"] = chunk_count
        if page_count is not None:
            values["page_count"] = page_count
        if status == "ready":
            values["indexed_at"] = datetime.utcnow()
            values["error"] = None
        await self.session.execute(
            update(KnowledgeDocument)
            .where(KnowledgeDocument.id == doc_id)
            .values(**values)
        )
        await self.session.commit()

    async def delete(self, doc_id: str, kb_id: str) -> KnowledgeDocument | None:
        doc = await self.get(doc_id, kb_id)
        if doc is None:
            return None
        await self.session.delete(doc)
        await self.session.commit()
        return doc

    async def count_by_kb(self, kb_id: str) -> int:
        from sqlalchemy import func as sqlfunc
        stmt = select(sqlfunc.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.kb_id == kb_id,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)


def _json_dumps(obj: object) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)


def parse_doc_metadata(raw: str) -> dict:
    import json
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

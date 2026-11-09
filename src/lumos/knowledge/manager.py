"""知识库管理器。

负责：
  - KB CRUD（含 Milvus collection / DB 的创建与删除）
  - 文档保存到磁盘
  - 异步触发索引任务（通过 BackgroundTasks）
  - 检索委托给 Retriever
  - 文档删除时同时清理 Milvus 向量与本地文件
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lumos.config import KnowledgeBaseConfig
from lumos.errors import (
    DocumentTooLargeError,
    KnowledgeBaseAlreadyExistsError,
    KnowledgeBaseNotFoundError,
    KnowledgeDocumentNotFoundError,
    UnsupportedMimeTypeError,
)
from lumos.knowledge.retriever import Retriever
from lumos.knowledge.vector_client import VectorServiceClient
from lumos.persistence.models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from lumos.persistence.repositories.knowledge_bases import KnowledgeBaseRepository
from lumos.persistence.repositories.knowledge_chunks import KnowledgeChunkRepository
from lumos.persistence.repositories.knowledge_documents import (
    KnowledgeDocumentRepository,
    parse_doc_metadata,
)

log = logging.getLogger(__name__)


# 知识库名称允许字符（字母/数字/下划线/连字符/空格）
_KB_NAME_RE = re.compile(r"^[a-zA-Z0-9_\- ]{1,64}$")


class KnowledgeManager:
    """单例：构造时接收 vector_client + config + session_factory。

    session_factory 用于 BackgroundTask 中创建独立 session（请求 session 已关闭）。"""

    def __init__(
        self,
        config: KnowledgeBaseConfig,
        vector_client: VectorServiceClient,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._config = config
        self._vector = vector_client
        self._session_factory = session_factory
        self._retriever = Retriever(vector_client, config)
        self._storage_root = Path(config.storage_dir).resolve()
        self._storage_root.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------- public

    @property
    def config(self) -> KnowledgeBaseConfig:
        return self._config

    @property
    def retriever(self) -> Retriever:
        return self._retriever

    def _milvus_collection_name(self, kb_id: str) -> str:
        # Milvus 限制：^[A-Za-z_][A-Za-z0-9_]{0,63}$，长度 64
        # 用 kb_ 前缀 + 取 uuid 前 12 位 hex，保证唯一 + 合规
        suffix = kb_id.replace("-", "")[:12]
        return f"kb_{suffix}"

    def _doc_storage_dir(self, kb_id: str, doc_id: str) -> Path:
        d = self._storage_root / kb_id / "documents" / doc_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _kb_storage_dir(self, kb_id: str) -> Path:
        d = self._storage_root / kb_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------------------------ CRUD

    async def create_kb(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        name: str,
        description: str,
        embedding_model: str,
        rerank_model: str,
        chunk_size: int,
        chunk_overlap: int,
        enabled: bool,
    ) -> KnowledgeBase:
        if not _KB_NAME_RE.match(name):
            raise KnowledgeBaseAlreadyExistsError(
                "name 仅允许字母/数字/下划线/连字符/空格，长度 1-64"
            )
        repo = KnowledgeBaseRepository(db)
        if await repo.get_by_name(user_id, name) is not None:
            raise KnowledgeBaseAlreadyExistsError(f"同名知识库已存在: {name}")

        kb_id = str(uuid.uuid4())
        collection = self._milvus_collection_name(kb_id)

        # 在 vector-service 创建 DB + collection（DB 已存在视为成功）
        try:
            await self._vector.ensure_database(self._config.database_name)
            await self._vector.ensure_collection(
                database=self._config.database_name,
                name=collection,
                dim=1024,  # bge-m3
                metric_type="cosine",
            )
        except Exception as e:
            log.warning("ensure_vector_collection_failed kb_id=%s err=%s", kb_id, e)
            raise

        kb = await repo.create(
            user_id=user_id,
            name=name,
            description=description,
            embedding_model=embedding_model,
            rerank_model=rerank_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            milvus_collection=collection,
            enabled=enabled,
        )
        return kb

    async def delete_kb(self, db: AsyncSession, kb_id: str, user_id: str) -> None:
        repo = KnowledgeBaseRepository(db)
        kb = await repo.delete(kb_id, user_id)
        if kb is None:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: {kb_id}")
        # 删除 Milvus collection（不影响其他 KB）
        try:
            await self._vector.delete_collection(
                self._config.database_name, kb.milvus_collection,
            )
        except Exception as e:
            log.warning("delete_vector_collection_failed kb_id=%s err=%s", kb_id, e)
        # 清理磁盘
        kb_dir = self._storage_root / kb_id
        if kb_dir.exists():
            _rm_tree(kb_dir)

    # ---------------------------------------------------------- documents

    async def upload_document(
        self,
        db: AsyncSession,
        *,
        kb_id: str,
        user_id: str,
        filename: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> KnowledgeDocument:
        kb_repo = KnowledgeBaseRepository(db)
        kb = await kb_repo.get(kb_id, user_id)
        if kb is None:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: {kb_id}")
        if mime_type not in self._config.allowed_mime_types:
            raise UnsupportedMimeTypeError(f"不支持的文档类型: {mime_type}")
        max_bytes = self._config.max_file_size_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise DocumentTooLargeError(
                f"文档超过大小限制 {self._config.max_file_size_mb} MB"
            )

        doc_repo = KnowledgeDocumentRepository(db)
        # 保存到磁盘
        doc_id = str(uuid.uuid4())
        storage_dir = self._doc_storage_dir(kb_id, doc_id)
        safe_name = _safe_filename(filename) or f"document-{doc_id[:8]}"
        file_path = storage_dir / safe_name
        file_path.write_bytes(file_bytes)

        doc = await doc_repo.create(
            kb_id=kb_id,
            filename=safe_name,
            mime_type=mime_type,
            file_path=str(file_path),
            file_size=len(file_bytes),
            doc_metadata={"original_filename": filename},
        )
        await kb_repo.touch(kb_id)
        return doc

    async def index_document(self, doc_id: str, kb_id: str) -> None:
        """Background task: 读取已落盘的文档，调用 /v1/ingest，保存 chunk 元数据。

        使用独立 session（请求 session 已关闭）。"""
        async with self._session_factory() as db:
            doc_repo = KnowledgeDocumentRepository(db)
            kb_repo = KnowledgeBaseRepository(db)
            chunk_repo = KnowledgeChunkRepository(db)

            doc = await doc_repo.get(doc_id, kb_id)
            if doc is None:
                log.warning("index_doc_missing", doc_id=doc_id)
                return
            kb = await kb_repo.get_by_id(kb_id)
            if kb is None:
                await doc_repo.update_status(doc_id, "failed", error="kb not found")
                return

            file_path = Path(doc.file_path)
            # 文件存在性检查 + 读字节都在线程池执行，避免阻塞事件循环
            loop = asyncio.get_running_loop()
            try:
                file_bytes = await loop.run_in_executor(
                    None,
                    lambda p=file_path: p.read_bytes() if p.exists() else None,
                )
            except Exception as e:
                log.warning("read_source_file_failed doc_id=%s err=%s", doc_id, e)
                await doc_repo.update_status(doc_id, "failed", error=f"read failed: {e}")
                return
            if file_bytes is None:
                await doc_repo.update_status(doc_id, "failed", error="source file missing")
                return

            metadata = parse_doc_metadata(doc.doc_metadata)
            metadata.setdefault("filename", doc.filename)

            try:
                await doc_repo.update_status(doc_id, "parsing")
                # /v1/ingest 是原子化的：内部完成解析+分片+嵌入+存储
                result = await self._vector.ingest(
                    file_bytes=file_bytes,
                    filename=doc.filename,
                    mime_type=doc.mime_type,
                    database=self._config.database_name,
                    collection=kb.milvus_collection,
                    chunk_size=kb.chunk_size,
                    chunk_overlap=kb.chunk_overlap,
                    embed_model=kb.embedding_model,
                    metadata=metadata,
                )
            except Exception as e:
                log.exception("ingest_failed doc_id=%s err=%s", doc_id, e)
                await doc_repo.update_status(doc_id, "failed", error=str(e)[:1000])
                return

            chunk_count = int(result.get("chunk_count", 0))
            page_count = result.get("page_count")
            await doc_repo.update_status(
                doc_id,
                "ready",
                chunk_count=chunk_count,
                page_count=int(page_count) if page_count is not None else None,
            )
            await kb_repo.touch(kb_id)

            # 向 chunks 元数据缓存插入占位记录（id 与 Milvus 一致：{doc_id}:{i}）
            # 不复制 text，节省空间；如需做列表查询可再调一次 /vectors/get 拉详情
            # 这里只保证 (doc_id, chunk_index, kb_id) 可用于后续清理与统计
            chunks = [
                KnowledgeChunk(
                    id=f"{doc_id}:{i}",
                    kb_id=kb_id,
                    doc_id=doc_id,
                    chunk_index=i,
                    text="",
                    token_count=0,
                )
                for i in range(chunk_count)
            ]
            try:
                await chunk_repo.bulk_insert(chunks)
            except Exception as e:
                log.warning("chunks_cache_insert_failed doc_id=%s err=%s", doc_id, e)

    async def delete_document(self, db: AsyncSession, kb_id: str, doc_id: str, user_id: str) -> None:
        kb_repo = KnowledgeBaseRepository(db)
        kb = await kb_repo.get(kb_id, user_id)
        if kb is None:
            raise KnowledgeBaseNotFoundError(f"知识库不存在: {kb_id}")
        doc_repo = KnowledgeDocumentRepository(db)
        doc = await doc_repo.get(doc_id, kb_id)
        if doc is None:
            raise KnowledgeDocumentNotFoundError(f"文档不存在: {doc_id}")

        # 删除 Milvus 向量
        try:
            filter_expr = f'doc_id == "{doc_id}"'
            await self._vector.delete_vectors(
                database=self._config.database_name,
                collection=kb.milvus_collection,
                filter_expr=filter_expr,
            )
        except Exception as e:
            log.warning("delete_vectors_failed doc_id=%s err=%s", doc_id, e)

        # 删除 chunk 元数据缓存
        chunk_repo = KnowledgeChunkRepository(db)
        try:
            await chunk_repo.delete_by_doc(doc_id)
        except Exception as e:
            log.warning("delete_chunks_failed doc_id=%s err=%s", doc_id, e)

        await doc_repo.delete(doc_id, kb_id)
        # 清理磁盘文件
        doc_dir = Path(doc.file_path).parent
        if doc_dir.exists():
            _rm_tree(doc_dir)
        await kb_repo.touch(kb_id)


# --------------------------------------------------------------------- utils


def _safe_filename(name: str) -> str:
    """保留 Unicode 字母/数字/常见符号；去除路径分隔符与控制字符。"""
    name = name.strip().replace("\\", "/").split("/")[-1]
    if not name:
        return ""
    cleaned = "".join(c for c in name if c.isprintable() and c not in '<>:"/\\|?*')
    return cleaned[:200]


def _rm_tree(p: Path) -> None:
    import shutil
    try:
        shutil.rmtree(p, ignore_errors=True)
    except Exception as e:
        log.warning("rm_tree_failed path=%s err=%s", p, e)

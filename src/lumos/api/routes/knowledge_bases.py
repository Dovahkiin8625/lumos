"""/api/knowledge_bases 路由。

端点设计：
  GET    /api/knowledge_bases                       列出当前用户的 KB
  POST   /api/knowledge_bases                       新建 KB（同步创建 Milvus collection）
  GET    /api/knowledge_bases/{kb_id}               获取 KB 详情
  PATCH  /api/knowledge_bases/{kb_id}               更新 KB 元数据
  DELETE /api/knowledge_bases/{kb_id}               删除 KB（含 Milvus collection、磁盘文件、chunks）

  GET    /api/knowledge_bases/{kb_id}/documents               列出 KB 内文档
  POST   /api/knowledge_bases/{kb_id}/documents               上传文档（multipart）
                                                            返回 doc，背景任务索引
  GET    /api/knowledge_bases/{kb_id}/documents/{doc_id}      获取文档详情
  DELETE /api/knowledge_bases/{kb_id}/documents/{doc_id}      删除文档（含 Milvus 向量）
  GET    /api/knowledge_bases/{kb_id}/documents/{doc_id}/status  轮询文档索引状态

  POST   /api/knowledge_bases/{kb_id}/search         检索接口

设计原则：
  - 所有路由需 get_current_user；user-scoped（KB 通过 user_id 隔离）
  - 错误映射：KnowledgeBaseNotFoundError→404、KnowledgeBaseAlreadyExistsError→409、
              KnowledgeDocumentNotFoundError→404、UnsupportedMimeTypeError→415、
              DocumentTooLargeError→413、其余 LumosError→500
  - 上传后通过 FastAPI BackgroundTasks 异步索引，立即返回 status=pending
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from lumos.api.deps import get_current_user, get_db
from lumos.api.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
    KnowledgeDocumentOut,
    KnowledgeDocumentStatusOut,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from lumos.errors import (
    DocumentTooLargeError,
    KnowledgeBaseAlreadyExistsError,
    KnowledgeBaseError,
    KnowledgeBaseNotFoundError,
    KnowledgeDocumentNotFoundError,
    UnsupportedMimeTypeError,
)
from lumos.knowledge.manager import KnowledgeManager
from lumos.persistence.models import User
from lumos.persistence.repositories.knowledge_bases import KnowledgeBaseRepository
from lumos.persistence.repositories.knowledge_chunks import KnowledgeChunkRepository
from lumos.persistence.repositories.knowledge_documents import (
    KnowledgeDocumentRepository,
    parse_doc_metadata,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge_bases", tags=["knowledge_base"])


def _manager(request: Request) -> KnowledgeManager:
    return request.app.state.knowledge_manager


async def _to_out(db: AsyncSession, kb) -> KnowledgeBaseOut:
    doc_repo = KnowledgeDocumentRepository(db)
    chunk_repo = KnowledgeChunkRepository(db)
    doc_count = await doc_repo.count_by_kb(kb.id)
    chunk_count = await chunk_repo.count_by_kb(kb.id)
    return KnowledgeBaseOut(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        embedding_model=kb.embedding_model,
        rerank_model=kb.rerank_model,
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        milvus_collection=kb.milvus_collection,
        enabled=kb.enabled,
        document_count=doc_count,
        indexed_chunk_count=chunk_count,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


def _doc_to_out(doc) -> KnowledgeDocumentOut:
    return KnowledgeDocumentOut(
        id=doc.id,
        kb_id=doc.kb_id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        status=doc.status,
        error=doc.error,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        doc_metadata=parse_doc_metadata(doc.doc_metadata),
        created_at=doc.created_at,
        indexed_at=doc.indexed_at,
    )


def _map_error(e: KnowledgeBaseError) -> HTTPException:
    if isinstance(e, (KnowledgeBaseNotFoundError, KnowledgeDocumentNotFoundError)):
        return HTTPException(404, str(e))
    if isinstance(e, KnowledgeBaseAlreadyExistsError):
        return HTTPException(409, str(e))
    if isinstance(e, UnsupportedMimeTypeError):
        return HTTPException(415, str(e))
    if isinstance(e, DocumentTooLargeError):
        return HTTPException(413, str(e))
    return HTTPException(500, str(e))


# ---------------------------------------------------------------- KB CRUD


@router.get("", response_model=list[KnowledgeBaseOut])
async def list_knowledge_bases(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeBaseOut]:
    repo = KnowledgeBaseRepository(db)
    kbs = await repo.list_by_user(user.id)
    return [await _to_out(db, kb) for kb in kbs]


@router.post("", response_model=KnowledgeBaseOut, status_code=201)
async def create_knowledge_base(
    req: KnowledgeBaseCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseOut:
    mgr = _manager(request)
    try:
        kb = await mgr.create_kb(
            db,
            user_id=user.id,
            name=req.name,
            description=req.description,
            embedding_model=req.embedding_model,
            rerank_model=req.rerank_model,
            chunk_size=req.chunk_size,
            chunk_overlap=req.chunk_overlap,
            enabled=req.enabled,
        )
    except KnowledgeBaseError as e:
        raise _map_error(e) from e
    return await _to_out(db, kb)


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
async def get_knowledge_base(
    kb_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseOut:
    repo = KnowledgeBaseRepository(db)
    kb = await repo.get(kb_id, user.id)
    if kb is None:
        raise HTTPException(404, "knowledge base not found")
    return await _to_out(db, kb)


@router.patch("/{kb_id}", response_model=KnowledgeBaseOut)
async def update_knowledge_base(
    kb_id: str,
    req: KnowledgeBaseUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseOut:
    repo = KnowledgeBaseRepository(db)
    if (
        req.chunk_size is not None
        and req.chunk_overlap is not None
        and req.chunk_overlap >= req.chunk_size
    ):
        raise HTTPException(422, "chunk_overlap must be smaller than chunk_size")
    kb = await repo.update(
        kb_id,
        user.id,
        description=req.description,
        chunk_size=req.chunk_size,
        chunk_overlap=req.chunk_overlap,
        enabled=req.enabled,
    )
    if kb is None:
        raise HTTPException(404, "knowledge base not found")
    return await _to_out(db, kb)


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    mgr = _manager(request)
    try:
        await mgr.delete_kb(db, kb_id, user.id)
    except KnowledgeBaseError as e:
        raise _map_error(e) from e


# -------------------------------------------------------------- Documents


@router.get("/{kb_id}/documents", response_model=list[KnowledgeDocumentOut])
async def list_documents(
    kb_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeDocumentOut]:
    kb_repo = KnowledgeBaseRepository(db)
    if await kb_repo.get(kb_id, user.id) is None:
        raise HTTPException(404, "knowledge base not found")
    doc_repo = KnowledgeDocumentRepository(db)
    docs = await doc_repo.list_by_kb(kb_id)
    return [_doc_to_out(d) for d in docs]


@router.post("/{kb_id}/documents", response_model=KnowledgeDocumentOut, status_code=201)
async def upload_document(
    kb_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentOut:
    mgr = _manager(request)
    file_bytes = await file.read()
    try:
        doc = await mgr.upload_document(
            db,
            kb_id=kb_id,
            user_id=user.id,
            filename=file.filename or "untitled",
            mime_type=file.content_type or "application/octet-stream",
            file_bytes=file_bytes,
        )
    except KnowledgeBaseError as e:
        raise _map_error(e) from e

    background_tasks.add_task(mgr.index_document, doc.id, kb_id)
    return _doc_to_out(doc)


@router.get(
    "/{kb_id}/documents/{doc_id}",
    response_model=KnowledgeDocumentOut,
)
async def get_document(
    kb_id: str,
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentOut:
    kb_repo = KnowledgeBaseRepository(db)
    if await kb_repo.get(kb_id, user.id) is None:
        raise HTTPException(404, "knowledge base not found")
    doc_repo = KnowledgeDocumentRepository(db)
    doc = await doc_repo.get(doc_id, kb_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    return _doc_to_out(doc)


@router.delete("/{kb_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    kb_id: str,
    doc_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    mgr = _manager(request)
    try:
        await mgr.delete_document(db, kb_id, doc_id, user.id)
    except KnowledgeBaseError as e:
        raise _map_error(e) from e


@router.get(
    "/{kb_id}/documents/{doc_id}/status",
    response_model=KnowledgeDocumentStatusOut,
)
async def get_document_status(
    kb_id: str,
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentStatusOut:
    kb_repo = KnowledgeBaseRepository(db)
    if await kb_repo.get(kb_id, user.id) is None:
        raise HTTPException(404, "knowledge base not found")
    doc_repo = KnowledgeDocumentRepository(db)
    doc = await doc_repo.get(doc_id, kb_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    return KnowledgeDocumentStatusOut(
        id=doc.id,
        status=doc.status,
        error=doc.error,
        chunk_count=doc.chunk_count,
        indexed_at=doc.indexed_at,
    )


# ----------------------------------------------------------------- Search


@router.post("/{kb_id}/search", response_model=KnowledgeSearchResponse)
async def search_knowledge_base(
    kb_id: str,
    req: KnowledgeSearchRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeSearchResponse:
    kb_repo = KnowledgeBaseRepository(db)
    kb = await kb_repo.get(kb_id, user.id)
    if kb is None:
        raise HTTPException(404, "knowledge base not found")
    if not kb.enabled:
        raise HTTPException(403, "knowledge base is disabled")
    mgr = _manager(request)
    result = await mgr.retriever.search(
        kb=kb,
        query=req.query,
        top_k=req.top_k,
        search_top_k=req.search_top_k,
        use_rerank=req.use_rerank,
        filter_filename=req.filter_filename,
    )
    return result.to_response()

"""检索逻辑：embed query → 向量检索 → 重排 → 引用格式化。

设计要点：
  - 单一入口 retriever.search(kb, query, top_k) -> KnowledgeSearchResponse
  - is_query=True 让 vector-service 自动添加 BGE-M3 中文检索前缀
  - 默认开启重排；可用 use_rerank=False 跳过
  - citation 字段由 section_header + page_number + filename 拼装，前端直接展示
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from lumos.api.schemas import KnowledgeSearchResponse, RetrievalHit
from lumos.config import KnowledgeBaseConfig
from lumos.knowledge.vector_client import VectorServiceClient
from lumos.persistence.models import KnowledgeBase

_SEARCH_OUTPUT_FIELDS = (
    "doc_id", "chunk_index", "section_header", "page_number",
    "filename", "title", "text",
)


@dataclass
class RetrievalResult:
    query: str
    hits: list[RetrievalHit]
    rerank_used: bool
    took_ms: int

    def to_response(self) -> KnowledgeSearchResponse:
        return KnowledgeSearchResponse(
            query=self.query,
            hits=self.hits,
            rerank_used=self.rerank_used,
            took_ms=self.took_ms,
        )


class Retriever:
    def __init__(self, client: VectorServiceClient, config: KnowledgeBaseConfig) -> None:
        self._client = client
        self._config = config

    async def search(
        self,
        *,
        kb: KnowledgeBase,
        query: str,
        top_k: int = 8,
        search_top_k: int | None = None,
        use_rerank: bool = True,
        filter_filename: str | None = None,
    ) -> RetrievalResult:
        start = time.perf_counter()
        search_top_k = search_top_k or self._config.search_top_k

        # 1) embed query（vector-service 自动加检索前缀）
        vectors = await self._client.embed_texts([query], model=kb.embedding_model, is_query=True)
        query_vector = vectors[0]

        # 2) 向量检索
        filter_expr = None
        if filter_filename:
            # Milvus 字符串字面量需单引号转义
            safe = filter_filename.replace("'", "\\'")
            filter_expr = f"filename == '{safe}'"
        hits = await self._client.search(
            database=self._config.database_name,
            collection=kb.milvus_collection,
            query_vector=query_vector,
            top_k=min(search_top_k, 200),
            output_fields=_SEARCH_OUTPUT_FIELDS,
            filter_expr=filter_expr,
        )

        if not hits:
            return RetrievalResult(
                query=query, hits=[], rerank_used=False, took_ms=_elapsed_ms(start),
            )

        # 3) 重排（可选）
        rerank_used = False
        if use_rerank and len(hits) > 1:
            documents = [_field_text(h) for h in hits]
            reranked = await self._client.rerank(
                query=query,
                documents=documents,
                top_n=min(top_k, len(hits)),
                model=kb.rerank_model,
            )
            rerank_used = True
            final: list[RetrievalHit] = []
            for item in reranked:
                src_idx = item.get("index", -1)
                if src_idx < 0 or src_idx >= len(hits):
                    continue
                final.append(_build_hit(hits[src_idx], score=float(item.get("score", 0.0))))
        else:
            final = [
                _build_hit(h, score=float(h.get("score", 0.0)))
                for h in hits[:top_k]
            ]

        return RetrievalResult(
            query=query, hits=final, rerank_used=rerank_used, took_ms=_elapsed_ms(start),
        )


def _field_text(hit: dict) -> str:
    return (hit.get("fields") or {}).get("text") or ""


def _build_hit(hit: dict, *, score: float) -> RetrievalHit:
    fields = hit.get("fields") or {}
    filename = fields.get("filename") or ""
    section = fields.get("section_header") or ""
    page = fields.get("page_number")
    citation = _format_citation(filename=filename, section=section, page=page)
    return RetrievalHit(
        text=fields.get("text") or "",
        score=score,
        doc_id=fields.get("doc_id") or "",
        chunk_index=int(fields.get("chunk_index") or 0),
        section_header=section or None,
        page_number=int(page) if page is not None else None,
        filename=filename,
        title=fields.get("title"),
        citation=citation,
    )


def _format_citation(*, filename: str, section: str, page: int | None) -> str:
    parts: list[str] = []
    if filename:
        parts.append(filename)
    if section:
        parts.append(section)
    if page is not None:
        parts.append(f"第 {page} 页")
    return " · ".join(parts) if parts else "未知来源"


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)

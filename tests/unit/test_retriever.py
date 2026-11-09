"""Retriever 单元测试（mock VectorServiceClient）。"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from lumos.config import KnowledgeBaseConfig
from lumos.knowledge.retriever import Retriever
from lumos.knowledge.vector_client import VectorServiceClient


@pytest.fixture
def fake_client() -> VectorServiceClient:
    client = VectorServiceClient(KnowledgeBaseConfig(
        vector_service_url="http://vs.test",
        database_name="lumos",
    ))
    client.embed_texts = AsyncMock(return_value=[[0.1, 0.2]])
    client.search = AsyncMock(return_value=[
        {
            "id": "doc1:0",
            "score": 0.9,
            "fields": {
                "doc_id": "doc1",
                "chunk_index": 0,
                "section_header": "1. Intro",
                "page_number": 1,
                "filename": "a.pdf",
                "title": "Test",
                "text": "The quick brown fox",
            },
        },
        {
            "id": "doc1:1",
            "score": 0.7,
            "fields": {
                "doc_id": "doc1",
                "chunk_index": 1,
                "section_header": "2. Details",
                "page_number": 2,
                "filename": "a.pdf",
                "title": "Test",
                "text": "jumps over the lazy dog",
            },
        },
    ])
    client.rerank = AsyncMock(return_value=[
        {"index": 1, "score": 0.95},
        {"index": 0, "score": 0.6},
    ])
    return client


def _fake_kb() -> SimpleNamespace:
    return SimpleNamespace(
        id="kb1",
        milvus_collection="kb_x",
        embedding_model="bge-m3",
        rerank_model="bge-reranker-v2-m3",
        enabled=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_search_with_rerank(fake_client: VectorServiceClient) -> None:
    r = Retriever(fake_client, KnowledgeBaseConfig())
    result = await r.search(kb=_fake_kb(), query="brown fox", top_k=2, use_rerank=True)
    assert result.rerank_used is True
    assert len(result.hits) == 2
    # rerank 把 idx=1 排到前面
    assert result.hits[0].doc_id == "doc1"
    assert result.hits[0].chunk_index == 1
    assert result.hits[0].citation.startswith("a.pdf")
    assert "第 2 页" in result.hits[0].citation


@pytest.mark.asyncio
async def test_search_without_rerank(fake_client: VectorServiceClient) -> None:
    fake_client.rerank = AsyncMock()  # 不调用
    r = Retriever(fake_client, KnowledgeBaseConfig())
    result = await r.search(kb=_fake_kb(), query="brown fox", top_k=2, use_rerank=False)
    assert result.rerank_used is False
    assert len(result.hits) == 2
    # 没有 rerank 时按原始 search 顺序
    assert result.hits[0].chunk_index == 0


@pytest.mark.asyncio
async def test_search_empty_hits(fake_client: VectorServiceClient) -> None:
    fake_client.search = AsyncMock(return_value=[])
    r = Retriever(fake_client, KnowledgeBaseConfig())
    result = await r.search(kb=_fake_kb(), query="nothing", use_rerank=True)
    assert result.hits == []
    assert result.rerank_used is False
    fake_client.rerank.assert_not_called()


@pytest.mark.asyncio
async def test_search_applies_filename_filter(fake_client: VectorServiceClient) -> None:
    r = Retriever(fake_client, KnowledgeBaseConfig())
    await r.search(
        kb=_fake_kb(), query="x", use_rerank=False, filter_filename="a.pdf",
    )
    call = fake_client.search.await_args
    assert call.kwargs["filter_expr"] == "filename == 'a.pdf'"


@pytest.mark.asyncio
async def test_search_escapes_filename_quote(fake_client: VectorServiceClient) -> None:
    r = Retriever(fake_client, KnowledgeBaseConfig())
    await r.search(
        kb=_fake_kb(), query="x", use_rerank=False, filter_filename="it's.pdf",
    )
    call = fake_client.search.await_args
    assert call.kwargs["filter_expr"] == "filename == 'it\\'s.pdf'"

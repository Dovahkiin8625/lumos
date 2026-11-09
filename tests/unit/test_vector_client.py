"""vector-service 客户端单元测试（httpx 调用使用 respx mock）。"""
from __future__ import annotations

import httpx
import pytest
import respx

from lumos.config import KnowledgeBaseConfig
from lumos.errors import (
    KnowledgeBaseError,
    VectorServiceUnavailableError,
)
from lumos.knowledge.vector_client import VectorServiceClient


@pytest.fixture
def client() -> VectorServiceClient:
    """返回一个使用 respx mock URL 的 VectorServiceClient。

    注意：respx 必须在客户端创建前或同上下文内激活。
    """
    cfg = KnowledgeBaseConfig(
        vector_service_url="http://vs.test",
        database_name="lumos",
        request_timeout=30,
    )
    return VectorServiceClient(cfg)


def _make_client(url: str = "http://vs.test") -> VectorServiceClient:
    """为单个测试创建新客户端（避免 respx 拦截问题）。"""
    cfg = KnowledgeBaseConfig(
        vector_service_url=url,
        database_name="lumos",
        request_timeout=30,
    )
    return VectorServiceClient(cfg)


@pytest.mark.asyncio
async def test_ready_returns_true_on_200() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        mock.get("/readyz").mock(return_value=httpx.Response(200, text="ready"))
        c = _make_client()
        assert await c.ready() is True


@pytest.mark.asyncio
async def test_ready_returns_false_on_error() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        mock.get("/readyz").mock(side_effect=httpx.ConnectError("nope"))
        c = _make_client()
        assert await c.ready() is False


@pytest.mark.asyncio
async def test_ensure_database_idempotent_on_409() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        route = mock.post("/v1/databases").mock(
            return_value=httpx.Response(409, json={"detail": "exists"}),
        )
        c = _make_client()
        await c.ensure_database("lumos")
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_ensure_database_raises_on_other_errors() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        mock.post("/v1/databases").mock(
            return_value=httpx.Response(500, text="server error"),
        )
        c = _make_client()
        with pytest.raises(KnowledgeBaseError):
            await c.ensure_database("lumos")


@pytest.mark.asyncio
async def test_ensure_collection_creates_when_missing() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        mock.get("/v1/databases/lumos/collections/kb_x").mock(
            return_value=httpx.Response(404),
        )
        create = mock.post("/v1/databases/lumos/collections").mock(
            return_value=httpx.Response(201, json={"name": "kb_x"}),
        )
        c = _make_client()
        await c.ensure_collection(
            database="lumos", name="kb_x", dim=1024, metric_type="cosine",
        )
        assert create.call_count == 1
        sent = create.calls.last.request
        import json as _json
        body = _json.loads(sent.content)
        assert body["name"] == "kb_x"
        assert body["vector_field"]["dim"] == 1024
        assert body["scalar_fields"][0]["name"] == "id"


@pytest.mark.asyncio
async def test_ensure_collection_skips_when_exists() -> None:
    with respx.mock(base_url="http://vs.test", assert_all_called=False) as mock:
        get = mock.get("/v1/databases/lumos/collections/kb_x").mock(
            return_value=httpx.Response(200, json={"name": "kb_x"}),
        )
        mock.post("/v1/databases/lumos/collections").mock(
            return_value=httpx.Response(201, json={"name": "kb_x"}),
        )
        c = _make_client()
        await c.ensure_collection(
            database="lumos", name="kb_x", dim=1024, metric_type="cosine",
        )
        assert get.call_count == 1


@pytest.mark.asyncio
async def test_embed_texts_returns_vectors_in_order() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        mock.post("/v1/embeddings").mock(
            return_value=httpx.Response(200, json={
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2]},
                    {"index": 1, "embedding": [0.3, 0.4]},
                ],
            }),
        )
        c = _make_client()
        result = await c.embed_texts(["hello", "world"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_embed_texts_empty_returns_empty() -> None:
    c = _make_client()
    assert await c.embed_texts([]) == []


@pytest.mark.asyncio
async def test_embed_texts_wraps_unavailable() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        mock.post("/v1/embeddings").mock(side_effect=httpx.ConnectError("down"))
        c = _make_client()
        with pytest.raises(VectorServiceUnavailableError):
            await c.embed_texts(["x"])


@pytest.mark.asyncio
async def test_search_passes_output_fields_and_filter() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        route = mock.post(
            "/v1/databases/lumos/collections/kb_x/search",
        ).mock(return_value=httpx.Response(200, json={"hits": []}))
        c = _make_client()
        await c.search(
            database="lumos",
            collection="kb_x",
            query_vector=[0.1, 0.2, 0.3],
            top_k=10,
            output_fields=["text", "filename"],
            filter_expr='filename == "a.pdf"',
        )
        import json as _json
        body = _json.loads(route.calls.last.request.content)
        assert body["top_k"] == 10
        assert body["output_fields"] == ["text", "filename"]
        assert body["filter_expr"] == 'filename == "a.pdf"'
        assert body["query_vector"] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_rerank_passes_top_n() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        route = mock.post("/v1/rerank").mock(
            return_value=httpx.Response(200, json={
                "results": [{"index": 0, "score": 0.9}],
            }),
        )
        c = _make_client()
        out = await c.rerank(
            query="q",
            documents=["a", "b", "c"],
            top_n=5,
        )
        import json as _json
        body = _json.loads(route.calls.last.request.content)
        assert body["top_n"] == 3  # capped at len(documents)
        assert body["documents"] == ["a", "b", "c"]
        assert out == [{"index": 0, "score": 0.9}]


@pytest.mark.asyncio
async def test_ingest_sends_multipart() -> None:
    with respx.mock(base_url="http://vs.test") as mock:
        route = mock.post("/v1/ingest").mock(
            return_value=httpx.Response(200, json={"doc_id": "abc", "chunk_count": 5}),
        )
        c = _make_client()
        out = await c.ingest(
            file_bytes=b"PDFDATA",
            filename="doc.pdf",
            mime_type="application/pdf",
            database="lumos",
            collection="kb_x",
            chunk_size=500,
            chunk_overlap=75,
            embed_model="bge-m3",
            metadata={"filename": "doc.pdf"},
        )
        assert out["doc_id"] == "abc"
        assert route.call_count == 1

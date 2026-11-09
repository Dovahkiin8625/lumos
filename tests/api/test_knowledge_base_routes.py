"""测试知识库 API 路由（mock vector-service HTTP 调用）。"""
from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient


async def _auth(c: AsyncClient) -> str:
    r = await c.post("/api/auth/register", json={
        "email": "kb@test.com", "password": "hunter22pass",
    })
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def vector_mock():
    """为所有 vector-service 调用安装默认 mock（空响应）。

    测试可在 fixture 之后覆盖特定路由以返回期望数据。
    """
    with respx.mock(assert_all_called=False, base_url="http://localhost:8080") as m:
        # health
        m.get("/readyz").mock(return_value=httpx.Response(200, text="ready"))
        # startup background task: load models
        m.post(url__regex=r"/v1/models/[^/]+/load").mock(
            return_value=httpx.Response(200, json={"id": "x", "type": "embedder", "status": "loaded"}),
        )
        # database
        m.post("/v1/databases").mock(
            return_value=httpx.Response(201, json={"name": "lumos"}),
        )
        # collection - exists check
        m.get(url__regex=r"/v1/databases/[^/]+/collections/[^/]+").mock(
            return_value=httpx.Response(200, json={"name": "kb_x"}),
        )
        # collection - create
        m.post(url__regex=r"/v1/databases/[^/]+/collections").mock(
            return_value=httpx.Response(201, json={"name": "kb_x"}),
        )
        # collection - delete
        m.delete(url__regex=r"/v1/databases/[^/]+/collections/[^/]+").mock(
            return_value=httpx.Response(200, json={"deleted": "kb_x"}),
        )
        # delete vectors
        m.post(url__regex=r"/v1/databases/[^/]+/collections/[^/]+/vectors/delete").mock(
            return_value=httpx.Response(200, json={"deleted": 0}),
        )
        # ingest
        m.post("/v1/ingest").mock(
            return_value=httpx.Response(200, json={"doc_id": "stub", "chunk_count": 5}),
        )
        # search + embeddings + rerank：使用 side_effect 支持测试覆盖
        # 默认实现：返回合理空响应
        async def _search_handler(request):
            return httpx.Response(200, json={"hits": []})
        m.post(url__regex=r"/v1/databases/[^/]+/collections/[^/]+/search").mock(
            side_effect=_search_handler,
        )
        async def _embed_handler(request):
            return httpx.Response(200, json={"data": []})
        m.post("/v1/embeddings").mock(side_effect=_embed_handler)
        async def _rerank_handler(request):
            return httpx.Response(200, json={"results": []})
        m.post("/v1/rerank").mock(side_effect=_rerank_handler)
        yield m


def _replace_side_effect(router, pattern: str, method: str = "post", **match_kwargs):
    """辅助函数：在 router 上替换已有路由的 side_effect。"""
    import re as _re
    for route in router.routes:
        if route.method.upper() != method.upper():
            continue
        # 检查是否匹配
        url_re = match_kwargs.get("url__regex")
        url = match_kwargs.get("url", match_kwargs.get("path"))
        if url_re:
            if route._url_pattern and _re.search(url_re, route._url_pattern.pattern):
                return route
        elif url:
            if str(url) in str(route):
                return route
    return None


@pytest.mark.asyncio
async def test_list_kb_empty(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/knowledge_bases", headers=H)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_create_and_get_kb(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/knowledge_bases", json={
        "name": "my-kb",
        "description": "测试 KB",
        "chunk_size": 500,
        "chunk_overlap": 75,
    }, headers=H)
    assert r.status_code == 201
    kb = r.json()
    assert kb["name"] == "my-kb"
    assert kb["milvus_collection"].startswith("kb_")
    assert kb["document_count"] == 0

    kb_id = kb["id"]
    r = await client.get(f"/api/knowledge_bases/{kb_id}", headers=H)
    assert r.status_code == 200
    assert r.json()["id"] == kb_id


@pytest.mark.asyncio
async def test_create_kb_duplicate_returns_409(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    payload = {"name": "dup"}
    r1 = await client.post("/api/knowledge_bases", json=payload, headers=H)
    assert r1.status_code == 201
    r2 = await client.post("/api/knowledge_bases", json=payload, headers=H)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_kb_invalid_overlap(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/knowledge_bases", json={
        "name": "bad", "chunk_size": 100, "chunk_overlap": 100,
    }, headers=H)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_kb(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/knowledge_bases", json={"name": "u"}, headers=H)
    kb_id = r.json()["id"]

    r = await client.patch(f"/api/knowledge_bases/{kb_id}", json={
        "description": "新描述", "enabled": False,
    }, headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["description"] == "新描述"
    assert body["enabled"] is False


@pytest.mark.asyncio
async def test_delete_kb(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/knowledge_bases", json={"name": "del"}, headers=H)
    kb_id = r.json()["id"]

    r = await client.delete(f"/api/knowledge_bases/{kb_id}", headers=H)
    assert r.status_code == 204

    r = await client.get(f"/api/knowledge_bases/{kb_id}", headers=H)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_upload_document_unsupported_mime(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/knowledge_bases", json={"name": "u"}, headers=H)
    kb_id = r.json()["id"]

    files = {"file": ("x.bin", b"data", "application/octet-stream")}
    r = await client.post(
        f"/api/knowledge_bases/{kb_id}/documents",
        files=files, headers=H,
    )
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_upload_document_success(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/knowledge_bases", json={"name": "u"}, headers=H)
    kb_id = r.json()["id"]

    files = {"file": ("hello.txt", b"hello world", "text/plain")}
    r = await client.post(
        f"/api/knowledge_bases/{kb_id}/documents",
        files=files, headers=H,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["kb_id"] == kb_id

    # list docs
    r = await client.get(f"/api/knowledge_bases/{kb_id}/documents", headers=H)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/knowledge_bases", json={"name": "u"}, headers=H)
    kb_id = r.json()["id"]

    files = {"file": ("hello.txt", b"hi", "text/plain")}
    r = await client.post(
        f"/api/knowledge_bases/{kb_id}/documents", files=files, headers=H,
    )
    doc_id = r.json()["id"]

    r = await client.delete(
        f"/api/knowledge_bases/{kb_id}/documents/{doc_id}", headers=H,
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_search_kb_not_found(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/knowledge_bases/nonexistent/search",
        json={"query": "x"}, headers=H,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_kb_disabled(client: AsyncClient, vector_mock) -> None:
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/knowledge_bases", json={"name": "u"}, headers=H)
    kb_id = r.json()["id"]

    await client.patch(
        f"/api/knowledge_bases/{kb_id}", json={"enabled": False}, headers=H,
    )

    r = await client.post(
        f"/api/knowledge_bases/{kb_id}/search",
        json={"query": "x"}, headers=H,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_search_kb_ok() -> None:
    """直接控制 respx 上下文，避免 fixture 状态污染。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from lumos.config import (
        LumosConfig, ServerConfig, ProviderConfig, DbConfig,
        ToolsConfig, SkillsConfig, McpConfig, AuthConfig, AgentConfig, set_config,
        KnowledgeBaseConfig,
    )
    from lumos.persistence.db import get_engine
    from lumos.api.app import create_app

    # 创建独立的 app（独立 vector-service 配置 + auto_load_models=False）
    cfg = LumosConfig(
        server=ServerConfig(),
        provider=ProviderConfig(type="openai_compat", base_url="http://x", api_key="x", model="x"),
        db=DbConfig(url="sqlite+aiosqlite:///:memory:"),
        tools=ToolsConfig(),
        skills=SkillsConfig(dirs=[]),
        mcp=McpConfig(servers=[]),
        auth=AuthConfig(jwt_secret="test-secret-32-bytes-long-string", access_ttl=3600, refresh_ttl=7200),
        agent=AgentConfig(),
        knowledge_base=KnowledgeBaseConfig(
            vector_service_url="http://vs.test:9999",
            auto_load_models=False,
        ),
    )
    set_config(cfg)
    app = create_app(cfg, for_testing=True)
    async with app.router.lifespan_context(app):
        async with respx.mock(assert_all_called=False, base_url="http://vs.test:9999") as m:
            # health
            m.get("/readyz").mock(return_value=httpx.Response(200, text="ready"))
            # load models
            m.post(url__regex=r"/v1/models/[^/]+/load").mock(
                return_value=httpx.Response(200, json={"id": "x"}),
            )
            # database
            m.post("/v1/databases").mock(return_value=httpx.Response(201, json={"name": "lumos"}))
            # collection exists check
            m.get(url__regex=r"/v1/databases/[^/]+/collections/[^/]+$").mock(
                return_value=httpx.Response(200, json={"name": "kb_x"}),
            )
            # collection create
            m.post(url__regex=r"/v1/databases/[^/]+/collections$").mock(
                return_value=httpx.Response(201, json={"name": "kb_x"}),
            )
            # collection delete
            m.delete(url__regex=r"/v1/databases/[^/]+/collections/[^/]+$").mock(
                return_value=httpx.Response(200, json={"deleted": "kb_x"}),
            )
            # delete vectors
            m.post(url__regex=r"/v1/databases/[^/]+/collections/[^/]+/vectors/delete$").mock(
                return_value=httpx.Response(200, json={"deleted": 0}),
            )
            # ingest
            m.post("/v1/ingest").mock(
                return_value=httpx.Response(200, json={"doc_id": "stub", "chunk_count": 5}),
            )
            # search: 返回两个 hits（确保 rerank 会被触发）
            search_route = m.post(url__regex=r"/v1/databases/[^/]+/collections/[^/]+/search$")
            search_route.mock(
                return_value=httpx.Response(200, json={
                    "hits": [
                        {
                            "id": "d:0",
                            "score": 0.9,
                            "fields": {
                                "doc_id": "d",
                                "chunk_index": 0,
                                "section_header": "1. Intro",
                                "page_number": 1,
                                "filename": "a.pdf",
                                "text": "hello world",
                            },
                        },
                        {
                            "id": "d:1",
                            "score": 0.7,
                            "fields": {
                                "doc_id": "d",
                                "chunk_index": 1,
                                "section_header": "2. Body",
                                "page_number": 2,
                                "filename": "a.pdf",
                                "text": "second chunk",
                            },
                        },
                    ],
                }),
            )
            # rerank: 直接路径，避免被 search regex 误匹配
            m.post("/v1/rerank").mock(
                return_value=httpx.Response(200, json={
                    "results": [
                        {"index": 1, "score": 0.95},
                        {"index": 0, "score": 0.5},
                    ],
                }),
            )
            # embeddings
            m.post("/v1/embeddings").mock(
                return_value=httpx.Response(200, json={
                    "data": [{"index": 0, "embedding": [0.1] * 1024}],
                }),
            )

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # 登录
                r = await client.post("/api/auth/register", json={
                    "email": "kb@test.com", "password": "hunter22pass",
                })
                token = r.json()["access_token"]
                H = {"Authorization": f"Bearer {token}"}

                # 创建 KB
                r = await client.post("/api/knowledge_bases", json={"name": "u"}, headers=H)
                assert r.status_code == 201, r.text
                kb_id = r.json()["id"]

                # 检索
                r = await client.post(
                    f"/api/knowledge_bases/{kb_id}/search",
                    json={"query": "hello", "top_k": 5}, headers=H,
                )
                assert r.status_code == 200, r.text
                body = r.json()
                assert body["query"] == "hello"
                assert len(body["hits"]) == 2
                assert body["hits"][0]["filename"] == "a.pdf"
                assert body["rerank_used"] is True

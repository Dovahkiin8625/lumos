"""vector-service HTTP 客户端。

仅封装 Lumos 真正用到的端点：
  - GET  /readyz                   健康检查
  - POST /v1/models/{id}/load      模型懒加载（启动时调用一次）
  - POST /v1/embeddings             文本嵌入
  - POST /v1/rerank                候选重排
  - POST /v1/databases / collections / vectors   集合与向量管理
  - POST .../vectors/delete         按主键或 filter_expr 删除
  - POST .../search                 相似度检索
  - POST /v1/ingest                 一体化摄取（multipart）

设计要点：
  - 单一 httpx.AsyncClient 实例，进程级复用连接池
  - 所有端点 timeout = config.request_timeout（默认 300s；/v1/ingest 可能很长）
  - 启动时调用 ensure_models_loaded() 自动加载 embed + rerank
  - 错误封装为 LumosError 层级（VectorServiceUnavailableError 等）
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import httpx

from lumos.config import KnowledgeBaseConfig
from lumos.errors import (
    KnowledgeBaseError,
    VectorServiceUnavailableError,
)

log = logging.getLogger(__name__)


def _check_response(r: httpx.Response) -> None:
    """对响应做状态码检查：4xx/5xx 抛出 KnowledgeBaseError。

    除特定幂等状态码（如 409 表示已存在）外，所有错误统一转换。
    """
    if r.status_code >= 400:
        snippet = (r.text or "")[:500]
        raise KnowledgeBaseError(
            f"vector-service {r.request.method} {r.request.url.path} "
            f"failed: {r.status_code} {snippet}"
        )


class VectorServiceClient:
    def __init__(self, config: KnowledgeBaseConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.vector_service_url,
            timeout=httpx.Timeout(config.request_timeout, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
        )

    @property
    def config(self) -> KnowledgeBaseConfig:
        return self._config

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> VectorServiceClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ------------------------------------------------------------------ health

    async def ready(self) -> bool:
        try:
            r = await self._client.get("/readyz", timeout=5.0)
            return r.status_code == 200
        except Exception as e:  # noqa: BLE001 — probe endpoint, swallow all errors
            log.warning("vector_service_ready_failed: %s", e)
            return False

    async def ensure_models_loaded(self) -> None:
        """启动时调用一次：尝试加载 embed + rerank 模型。失败仅记录日志。"""
        if not self._config.auto_load_models:
            return
        for model_id in (self._config.embed_model, self._config.rerank_model):
            try:
                await self._client.post(f"/v1/models/{model_id}/load", timeout=120.0)
            except httpx.HTTPError as e:
                log.warning("vector_service_model_load_failed model=%s err=%s", model_id, e)

    # --------------------------------------------------------------- databases

    async def ensure_database(self, name: str) -> None:
        """确保数据库存在。409 视为幂等成功。"""
        try:
            r = await self._client.post("/v1/databases", json={"name": name})
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service /v1/databases 请求失败: {e}"
            ) from e
        if r.status_code == 409:
            return
        _check_response(r)

    async def delete_database(self, name: str) -> None:
        try:
            r = await self._client.delete(f"/v1/databases/{name}")
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service /v1/databases/{name} 删除失败: {e}"
            ) from e
        if r.status_code == 404:
            return
        _check_response(r)

    # ------------------------------------------------------------- collections

    async def ensure_collection(
        self,
        *,
        database: str,
        name: str,
        dim: int,
        metric_type: str = "cosine",
    ) -> None:
        """确保 collection 存在。若不存在则创建（BGE-M3 = 1024 维）。"""
        try:
            r = await self._client.get(f"/v1/databases/{database}/collections/{name}")
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            # 网络错误：继续尝试创建（最终在 POST 处报错）
            pass
        payload = {
            "name": name,
            "primary_field": "id",
            "scalar_fields": [
                {"name": "id", "dtype": "varchar", "is_primary": True, "max_length": 128},
                {"name": "doc_id", "dtype": "varchar", "max_length": 64},
                {"name": "chunk_index", "dtype": "int64"},
                {"name": "section_header", "dtype": "varchar", "max_length": 512},
                {"name": "page_number", "dtype": "int64"},
                {"name": "filename", "dtype": "varchar", "max_length": 256},
                {"name": "title", "dtype": "varchar", "max_length": 256},
                {"name": "text", "dtype": "varchar", "max_length": 8192},
            ],
            "vector_field": {"name": "vector", "dim": dim, "metric_type": metric_type},
            "index_params": [
                {
                    "field_name": "vector",
                    "metric_type": metric_type,
                    "index_type": "HNSW",
                    "params": {"M": 16, "efConstruction": 200},
                }
            ],
        }
        try:
            r = await self._client.post(f"/v1/databases/{database}/collections", json=payload)
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service collection create 失败: {e}"
            ) from e
        _check_response(r)

    async def delete_collection(self, database: str, name: str) -> None:
        try:
            r = await self._client.delete(f"/v1/databases/{database}/collections/{name}")
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service collection delete 失败: {e}"
            ) from e
        if r.status_code == 404:
            return
        _check_response(r)

    # ------------------------------------------------------------------ ingest

    async def ingest(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        database: str,
        collection: str,
        chunk_size: int,
        chunk_overlap: int,
        embed_model: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """调用 vector-service /v1/ingest：解析 + 分片 + 嵌入 + 存储。

        返回 {"doc_id": str, "chunk_count": int, "page_count": int?, "tokens_used": int?}
        """
        files = {"file": (filename, file_bytes, mime_type)}
        data: dict[str, str] = {
            "database": database,
            "collection": collection,
            "chunk_size": str(chunk_size),
            "chunk_overlap": str(chunk_overlap),
            "embed_model": embed_model,
        }
        if metadata:
            import json as _json
            data["metadata"] = _json.dumps(metadata, ensure_ascii=False)
        try:
            r = await self._client.post("/v1/ingest", files=files, data=data)
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service /v1/ingest 请求失败: {e}"
            ) from e
        if r.status_code >= 400:
            raise KnowledgeBaseError(
                f"vector-service /v1/ingest 失败: {r.status_code} {r.text}"
            )
        return r.json()

    # ------------------------------------------------------------------ search

    async def embed_texts(
        self,
        texts: Sequence[str],
        *,
        model: str | None = None,
        is_query: bool = False,
    ) -> list[list[float]]:
        """调用 /v1/embeddings 获取文本向量。

        is_query=True 时由 vector-service 自动添加 BGE-M3 中文检索前缀；
        文档路径不添加。客户端无需自行处理前缀。
        """
        if not texts:
            return []
        payload = {
            "input": list(texts),
            "model": model or self._config.embed_model,
            "encoding_format": "float",
        }
        try:
            r = await self._client.post("/v1/embeddings", json=payload)
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service /v1/embeddings 请求失败: {e}"
            ) from e
        if r.status_code >= 400:
            raise KnowledgeBaseError(
                f"vector-service /v1/embeddings 失败: {r.status_code} {r.text}"
            )
        data = r.json().get("data", [])
        data = r.json().get("data", [])
        # 按 index 排序后返回
        data_sorted = sorted(data, key=lambda x: x.get("index", 0))
        return [item["embedding"] for item in data_sorted]

    async def search(
        self,
        *,
        database: str,
        collection: str,
        query_vector: Sequence[float],
        top_k: int,
        output_fields: Sequence[str] | None = None,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "primary_field": "id",
            "vector_field": "vector",
            "query_vector": list(query_vector),
            "top_k": top_k,
        }
        if output_fields:
            payload["output_fields"] = list(output_fields)
        if filter_expr:
            payload["filter_expr"] = filter_expr
        try:
            r = await self._client.post(
                f"/v1/databases/{database}/collections/{collection}/search",
                json=payload,
            )
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service search 请求失败: {e}"
            ) from e
        if r.status_code >= 400:
            raise KnowledgeBaseError(
                f"vector-service search 失败: {r.status_code} {r.text}"
            )
        body = r.json()
        if "hits" not in body:
            print(f"DEBUG vector_client.search: response body = {body}")
        return body.get("hits", [])

    async def delete_vectors(
        self,
        *,
        database: str,
        collection: str,
        filter_expr: str,
    ) -> int:
        """通过 filter_expr 删除向量（如 doc_id == 'xxx'）。返回删除数量。"""
        payload = {"primary_field": "id", "filter_expr": filter_expr}
        try:
            r = await self._client.post(
                f"/v1/databases/{database}/collections/{collection}/vectors/delete",
                json=payload,
            )
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service delete 请求失败: {e}"
            ) from e
        if r.status_code >= 400:
            raise KnowledgeBaseError(
                f"vector-service delete 失败: {r.status_code} {r.text}"
            )
        return int(r.json().get("deleted", 0))

    # ------------------------------------------------------------------ rerank

    async def rerank(
        self,
        *,
        query: str,
        documents: Sequence[str],
        top_n: int,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        if not documents:
            return []
        payload = {
            "query": query,
            "documents": list(documents),
            "top_n": min(top_n, len(documents)),
            "model": model or self._config.rerank_model,
        }
        try:
            r = await self._client.post("/v1/rerank", json=payload)
        except httpx.HTTPError as e:
            raise VectorServiceUnavailableError(
                f"vector-service /v1/rerank 请求失败: {e}"
            ) from e
        if r.status_code >= 400:
            raise KnowledgeBaseError(
                f"vector-service /v1/rerank 失败: {r.status_code} {r.text}"
            )
        return r.json().get("results", [])

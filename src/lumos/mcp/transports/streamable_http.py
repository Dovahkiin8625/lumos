"""Streamable HTTP传输（MCP 2025协议）。"""
from __future__ import annotations
import asyncio
import json
from typing import Any
import httpx
from lumos.errors import McpConnectionError


class StreamableHttpTransport:
    """MCP Streamable HTTP传输。

    协议要点：
    - 客户端POST JSON-RPC消息到endpoint
    - 服务端响应SSE流或单条JSON
    - 双向通信通过持续HTTP连接
    """

    def __init__(self, *, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=60))

    async def read_message(self) -> dict[str, Any]:
        """Streamable HTTP的read语义：阻塞等待下一个SSE事件。"""
        if not self._client:
            raise McpConnectionError("streamable_http transport not started")
        # 由客户端主动POST+读取响应，因此read_message通常不单独调用。
        # 这里提供基线实现：读取self._client上的最近响应
        # 实际使用中由McpClient在write_message后处理响应
        raise NotImplementedError(
            "Streamable HTTP is request-response; use write_message which returns response"
        )

    async def write_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """发送JSON-RPC消息，返回响应。"""
        if not self._client:
            raise McpConnectionError("streamable_http transport not started")
        try:
            resp = await self._client.post(
                self.url,
                json=msg,
                headers={
                    **self.headers,
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "text/event-stream" in ct:
                # 解析SSE格式响应
                data_lines: list[str] = []
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        data_lines.append(line.split(":", 1)[1].strip())
                if data_lines:
                    return json.loads("\n".join(data_lines))
                raise McpConnectionError("Empty SSE response")
            return resp.json()
        except Exception as e:
            raise McpConnectionError(
                f"streamable_http POST failed: {e}", cause=e,
            ) from e

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
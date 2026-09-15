"""SSE传输：远程MCP服务器。"""
from __future__ import annotations
import asyncio
import json
from typing import Any
import httpx
from lumos.errors import McpConnectionError


class SseTransport:
    def __init__(self, *, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None
        self._response: httpx.Response | None = None
        self._post_url: str | None = None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._reader_task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(None, connect=10.0, read=None),
            )
            req = self._client.build_request("GET", self.url, headers=self.headers)
            self._response = await self._client.send(req, stream=True)
            self._response.raise_for_status()
        except Exception as e:
            raise McpConnectionError(
                f"Failed to connect SSE MCP {self.url}: {e}", cause=e,
            ) from e
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def _reader_loop(self) -> None:
        assert self._response is not None
        event_type = ""
        data_lines: list[str] = []
        try:
            async for line in self._response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data_lines.append(line.split(":", 1)[1].strip())
                elif line == "":
                    if event_type == "endpoint" and data_lines:
                        endpoint = data_lines[-1]
                        base = str(self._response.request.url)
                        from urllib.parse import urljoin
                        self._post_url = urljoin(base, endpoint)
                    elif event_type in ("message", "") and data_lines:
                        try:
                            payload = json.loads("\n".join(data_lines))
                            await self._queue.put(payload)
                        except json.JSONDecodeError:
                            pass
                    event_type = ""
                    data_lines = []
        except Exception as e:
            import structlog
            structlog.get_logger().error("mcp.sse.reader_failed", error=str(e))
        finally:
            await self._response.aclose()

    async def read_message(self) -> dict[str, Any]:
        return await asyncio.wait_for(self._queue.get(), timeout=60.0)

    async def write_message(self, msg: dict[str, Any]) -> None:
        if not self._client:
            raise McpConnectionError("SSE transport not started")
        if not self._post_url:
            raise McpConnectionError("SSE endpoint not yet announced")
        try:
            resp = await self._client.post(
                self._post_url,
                json=msg,
                headers={**self.headers, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
        except Exception as e:
            raise McpConnectionError(f"SSE POST failed: {e}", cause=e) from e

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None
        if self._client:
            await self._client.aclose()
            self._client = None
        self._response = None
        self._post_url = None
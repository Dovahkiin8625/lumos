"""单个MCP服务器连接的封装。"""
from __future__ import annotations
import asyncio
import json
from typing import Any
from lumos.mcp.config import McpServerConfig
from lumos.mcp.transports import (
    BaseTransport, StdioTransport, SseTransport, StreamableHttpTransport,
)
from lumos.errors import McpConnectionError


class McpClient:
    """单个MCP服务器的JSON-RPC客户端。"""

    def __init__(self, config: McpServerConfig) -> None:
        self.config = config
        self.transport: BaseTransport = self._build_transport()
        self._initialized = False
        self._request_id = 0
        self._lock = asyncio.Lock()
        self._tools_cache: list[dict[str, Any]] = []

    def _build_transport(self) -> BaseTransport:
        if self.config.transport == "stdio":
            return StdioTransport(
                command=self.config.command or "",
                args=self.config.args, env=self.config.env,
            )
        if self.config.transport == "sse":
            return SseTransport(
                url=self.config.url or "", headers=self.config.headers,
            )
        if self.config.transport == "streamable_http":
            return StreamableHttpTransport(
                url=self.config.url or "", headers=self.config.headers,
            )
        raise ValueError(f"Unknown transport: {self.config.transport}")

    async def connect(self) -> None:
        await self.transport.start()
        # MCP初始化握手
        try:
            await self._request_unlocked("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "lumos", "version": "0.1.0"},
            })
            await self._send_notification("notifications/initialized", {})
            self._initialized = True
        except Exception as e:
            await self.transport.close()
            raise McpConnectionError(
                f"MCP initialize failed for {self.config.name}: {e}",
                cause=e,
            ) from e
        # 缓存工具列表
        try:
            self._tools_cache = await self.list_tools()
        except Exception:
            self._tools_cache = []

    async def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _send_notification(
        self, method: str, params: dict[str, Any],
    ) -> None:
        """发送一个JSON-RPC notification（无id，无响应）。"""
        notification = {"jsonrpc": "2.0", "method": method, "params": params}
        async with self._lock:
            await self.transport.write_message(notification)

    async def list_tools(self) -> list[dict[str, Any]]:
        resp = await self._request_unlocked("tools/list", {})
        return resp.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        resp = await self._request_unlocked(
            "tools/call", {"name": name, "arguments": arguments},
        )
        content = resp.get("result", {}).get("content", [])
        parts: list[str] = []
        for c in content:
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
        return "\n".join(parts) if parts else json.dumps(resp.get("result"))

    async def _request_unlocked(
        self, method: str, params: dict[str, Any],
    ) -> dict[str, Any]:
        """根据传输类型分派的request实现。"""
        msg_id = await self._next_id()
        request = {
            "jsonrpc": "2.0", "id": msg_id, "method": method, "params": params,
        }
        if isinstance(self.transport, StreamableHttpTransport):
            response = await self.transport.write_message(request)
            if "error" in response:
                raise McpConnectionError(f"MCP error: {response['error']}")
            return response
        # stdio / SSE: write then read
        async with self._lock:
            await self.transport.write_message(request)
            while True:
                msg = await self.transport.read_message()
                if msg.get("id") == msg_id:
                    if "error" in msg:
                        raise McpConnectionError(f"MCP error: {msg['error']}")
                    return msg

    async def disconnect(self) -> None:
        await self.transport.close()
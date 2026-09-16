"""MCP Manager：管理多个MCP服务器连接。"""
from __future__ import annotations
from typing import Any
import asyncio
from lumos.agent.message import ToolSpec
from lumos.errors import McpConnectionError
from lumos.mcp.client import McpClient
from lumos.mcp.config import McpServerConfig


class McpManager:
    """管理所有MCP服务器连接。"""

    def __init__(self, configs: list[McpServerConfig]) -> None:
        self.configs = [c for c in configs if c.enabled]
        self._clients: dict[str, McpClient] = {}

    async def connect_all(self) -> None:
        """并发连接所有enabled服务器，单个失败不影响其他。"""
        results = await asyncio.gather(
            *[self._connect_one(c) for c in self.configs],
            return_exceptions=True,
        )
        for c, r in zip(self.configs, results):
            if isinstance(r, Exception):
                import structlog
                structlog.get_logger().error(
                    "mcp.connect_failed", name=c.name, error=str(r),
                )

    async def _connect_one(self, config: McpServerConfig) -> None:
        client = McpClient(config)
        await client.connect()
        self._clients[config.name] = client

    async def shutdown(self) -> None:
        await asyncio.gather(
            *[c.disconnect() for c in self._clients.values()],
            return_exceptions=True,
        )
        self._clients.clear()

    def all_tools(self) -> list[ToolSpec]:
        specs: list[ToolSpec] = []
        for server_name, client in self._clients.items():
            # 同步遍历已缓存的工具（连接时调用list_tools）
            for t in getattr(client, "_tools_cache", []):
                specs.append(ToolSpec(
                    name=f"{server_name}__{t['name']}",
                    description=t.get("description", ""),
                    parameters=t.get("inputSchema", {}),
                    source="mcp",
                ))
        return specs

    async def call_tool(self, full_name: str, arguments: dict[str, Any]) -> str:
        if "__" not in full_name:
            raise ValueError(f"Invalid MCP tool name: {full_name}")
        server_name, tool_name = full_name.split("__", 1)
        client = self._clients.get(server_name)
        if client is None:
            raise McpConnectionError(f"MCP server not connected: {server_name}")
        return await client.call_tool(tool_name, arguments)

    def get_client(self, name: str) -> McpClient | None:
        return self._clients.get(name)

    async def refresh_tools_cache(self) -> None:
        """每个客户端连接后调用list_tools并缓存。"""
        for client in self._clients.values():
            try:
                client._tools_cache = await client.list_tools()
            except Exception as e:
                import structlog
                structlog.get_logger().warning(
                    "mcp.list_tools_failed", name=client.config.name, error=str(e),
                )
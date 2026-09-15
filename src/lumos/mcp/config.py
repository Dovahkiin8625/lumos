"""MCP服务器配置。"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class McpServerConfig:
    name: str
    transport: str  # stdio | sse | streamable_http
    enabled: bool = True
    # stdio
    command: str | None = None
    args: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    # sse / streamable_http
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
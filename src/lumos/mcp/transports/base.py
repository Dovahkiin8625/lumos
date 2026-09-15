"""MCP传输抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseTransport(ABC):
    """所有MCP传输的抽象接口。"""

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def read_message(self) -> dict[str, Any]:
        """读取下一个JSON-RPC消息。"""
        ...

    @abstractmethod
    async def write_message(self, msg: dict[str, Any]) -> None:
        """发送一个JSON-RPC消息。"""
        ...

    @abstractmethod
    async def close(self) -> None:
        ...
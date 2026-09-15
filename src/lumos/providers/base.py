"""LLM Provider抽象基类。"""
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Awaitable, Callable
from lumos.agent.message import Message, ToolCall, Usage, ToolSpec


OnTextCallback = Callable[[str], Awaitable[None]]


class BaseProvider(ABC):
    """所有LLM Provider的抽象接口。"""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        cancel: asyncio.Event | None = None,
        on_text: OnTextCallback | None = None,
    ) -> tuple[str, list[ToolCall], Usage]:
        """单次完整调用，返回(text, tool_calls, usage)。"""
        ...

    async def stream_chat(self, **kwargs) -> tuple[str, list[ToolCall], Usage]:
        """流式调用：默认实现为on_text累加 + chat()。"""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """文本嵌入接口（一阶段不实现，二阶段RAG时由VectorServiceProvider覆盖）。"""
        raise NotImplementedError(
            "embed() not implemented in phase 1; "
            "use VectorServiceProvider in phase 2"
        )

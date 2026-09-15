"""OpenAI兼容Provider（覆盖OpenAI官方 + 所有兼容服务）。"""
from __future__ import annotations
import asyncio
import json
from typing import Any
from openai import AsyncOpenAI
from lumos.agent.message import Message, ToolCall, ToolSpec, Usage
from lumos.providers.base import BaseProvider, OnTextCallback
from lumos.errors import ProviderError, ContextLengthExceededError


class OpenAICompatProvider(BaseProvider):
    """OpenAI兼容实现。

    支持OpenAI官方及所有OpenAI兼容服务（DeepSeek/Qwen/Moonshot/Ollama/vLLM等）。
    通过指定base_url切换。
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 60,
        **client_kwargs: Any,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            **client_kwargs,
        )

    def _convert_messages(
        self, messages: list[Message], system: str | None,
    ) -> list[dict[str, Any]]:
        oai: list[dict[str, Any]] = []
        if system:
            oai.append({"role": "system", "content": system})
        for msg in messages:
            if isinstance(msg.content, str):
                oai.append({"role": msg.role, "content": msg.content})
            else:
                content_parts: list[dict[str, Any]] = []
                tool_calls_list: list[dict[str, Any]] = []
                for c in msg.content:
                    if c.type == "text":
                        content_parts.append({"type": "text", "text": c.text})
                    elif c.type == "tool_call":
                        tool_calls_list.append({
                            "id": c.id,
                            "type": "function",
                            "function": {
                                "name": c.name,
                                "arguments": json.dumps(c.arguments),
                            },
                        })
                d: dict[str, Any] = {"role": msg.role}
                if tool_calls_list:
                    if content_parts:
                        d["content"] = "".join(
                            p["text"] for p in content_parts
                        )
                    else:
                        d["content"] = None
                    d["tool_calls"] = tool_calls_list
                else:
                    d["content"] = "".join(p["text"] for p in content_parts)
                if msg.name:
                    d["name"] = msg.name
                if msg.tool_call_id:
                    d["tool_call_id"] = msg.tool_call_id
                oai.append(d)
        return oai

    def _convert_tools(self, tools: list[ToolSpec] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

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
        oai_messages = self._convert_messages(messages, system)
        oai_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
            "temperature": temperature,
            "stream": True,
        }
        if oai_tools is not None:
            kwargs["tools"] = oai_tools
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            msg = str(e).lower()
            retryable = any(
                x in msg for x in ("timeout", "rate", "5xx", "server error")
            )
            if "context_length" in msg or "maximum context" in msg:
                raise ContextLengthExceededError(str(e), cause=e) from e
            raise ProviderError(str(e), retryable=retryable, cause=e) from e

        text_chunks: list[str] = []
        tool_calls_acc: dict[int, dict[str, Any]] = {}
        usage = Usage()

        async for chunk in response:
            if cancel and cancel.is_set():
                raise asyncio.CancelledError()
            if chunk.usage is not None:
                usage = Usage(
                    prompt_tokens=getattr(chunk.usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(chunk.usage, "completion_tokens", 0) or 0,
                    total_tokens=getattr(chunk.usage, "total_tokens", 0) or 0,
                )
            for choice in chunk.choices:
                delta = choice.delta
                if delta.content:
                    text_chunks.append(delta.content)
                    if on_text is not None:
                        await on_text(delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc.id or "",
                                "name": (tc.function.name if tc.function else "") or "",
                                "arguments": "",
                            }
                        if tc.function and tc.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc.function.arguments

        tool_calls: list[ToolCall] = []
        for idx in sorted(tool_calls_acc):
            tc = tool_calls_acc[idx]
            raw_args = tc["arguments"]
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                args = {"_raw": raw_args, "_parse_error": True}
            tool_calls.append(ToolCall(id=tc["id"], name=tc["name"], arguments=args))

        return "".join(text_chunks), tool_calls, usage

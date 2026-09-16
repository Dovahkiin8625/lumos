"""上下文窗口管理与压缩。"""
from __future__ import annotations
from typing import Awaitable, Callable
from lumos.agent.message import Message, TextContent


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for c in content:
        if c.type == "text":
            parts.append(c.text)
        elif c.type == "tool_call":
            parts.append(f"tool_call({c.name}, {c.arguments})")
    return " ".join(parts)


def estimate_tokens(messages: list[Message]) -> int:
    """粗略估算token数（4字符/token近似）。"""
    total = 0
    for m in messages:
        total += len(_content_text(m.content)) // 4 + 4  # 每条消息加4 token开销
    return total


Summarizer = Callable[[str], Awaitable[str]]


async def compress_history(
    history: list[Message],
    *,
    summarizer: Summarizer,
    threshold: int,
) -> list[Message]:
    """当总token数超过threshold时，将前半部分user/assistant消息压缩为一条summary。"""
    if estimate_tokens(history) <= threshold:
        return history

    # 找到第一个非system消息的位置，保留首条user消息不动
    keep_count = 1
    head = history[:keep_count]
    body = history[keep_count:]

    # 合并body为单个文本
    body_text = "\n".join(
        f"{m.role}: {_content_text(m.content)}" for m in body
    )
    summary = await summarizer(body_text)
    summary_msg = Message(
        role="system",
        content=f"[Earlier messages summary]\n{summary}",
    )
    return list(head) + [summary_msg]

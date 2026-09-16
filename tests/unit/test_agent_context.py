"""测试上下文压缩。"""
from __future__ import annotations
import pytest
from lumos.agent.context import estimate_tokens, compress_history
from lumos.agent.message import Message, TextContent


@pytest.mark.asyncio
async def test_compress_under_threshold():
    history = [Message(role="user", content="hi")]
    async def summarizer(text):
        return f"summary: {text}"
    result = await compress_history(
        history, summarizer=summarizer, threshold=10000,
    )
    assert result == history


@pytest.mark.asyncio
async def test_compress_over_threshold():
    # 制造长历史
    history = [
        Message(role="user", content="x" * 5000),
        Message(role="assistant", content="y" * 5000),
        Message(role="user", content="z" * 5000),
        Message(role="assistant", content="w" * 5000),
    ]
    called = []
    async def summarizer(text):
        called.append(len(text))
        return f"[summary of {len(text)} chars]"

    result = await compress_history(
        history, summarizer=summarizer, threshold=1000,
    )
    assert len(result) < len(history)
    assert len(called) > 0


def test_estimate_tokens():
    msgs = [
        Message(role="user", content="hello"),  # 5 chars ≈ 2 tokens
        Message(role="assistant", content="hi there"),  # 8 chars ≈ 2 tokens
    ]
    tokens = estimate_tokens(msgs)
    assert tokens > 0

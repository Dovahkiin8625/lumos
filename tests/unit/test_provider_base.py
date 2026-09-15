"""测试Provider抽象基类的embed预留接口。"""
from __future__ import annotations
import pytest
from lumos.providers.base import BaseProvider


def test_embed_raises_not_implemented():
    class FakeProvider(BaseProvider):
        async def chat(self, messages, *, system, tools, temperature,
                       max_tokens, cancel, on_text):
            return "", [], Usage()

    p = FakeProvider()
    with pytest.raises(NotImplementedError, match="RAG"):
        import asyncio
        asyncio.run(p.embed(["text"]))

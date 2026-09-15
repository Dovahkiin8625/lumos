"""测试OpenAI兼容Provider（含流式tool_calls累积）。"""
from __future__ import annotations
import pytest
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import (
    Choice as ChunkChoice, ChoiceDelta, ChoiceDeltaToolCall,
)
from lumos.providers.openai_compat import OpenAICompatProvider
from lumos.agent.message import Message, ToolSpec, Usage


def _make_chunk(
    *, content="", tool_calls=None, finish_reason=None, usage=None,
):
    delta = ChoiceDelta(content=content or None, role="assistant")
    if tool_calls:
        delta.tool_calls = [
            ChoiceDeltaToolCall(
                index=tc.get("index", 0),
                id=tc.get("id"),
                function=tc.get("function"),
            )
            for tc in tool_calls
        ]
    return ChatCompletionChunk(
        id="chunk",
        object="chat.completion.chunk",
        created=0,
        model="test",
        choices=[ChunkChoice(index=0, delta=delta, finish_reason=finish_reason)],
        usage=usage,
    )


@pytest.fixture
def mock_openai_client(mocker):
    """用mocker替换AsyncOpenAI的chat.completions.create。"""
    pass


@pytest.mark.asyncio
async def test_streaming_text_accumulation(mocker):
    chunks = [
        _make_chunk(content="Hello"),
        _make_chunk(content=" world"),
        _make_chunk(content="!", finish_reason="stop"),
    ]
    async def fake_create(**kwargs):
        for c in chunks:
            yield c

    provider = OpenAICompatProvider(
        base_url="https://api.test/v1",
        api_key="k",
        model="m",
    )
    mocker.patch.object(
        provider.client.chat.completions, "create", side_effect=fake_create
    )

    text_parts: list[str] = []
    async def on_text(t: str) -> None:
        text_parts.append(t)

    text, tool_calls, usage = await provider.chat(
        messages=[Message(role="user", content="hi")],
        system=None,
        tools=None,
        temperature=0.5,
        max_tokens=None,
        cancel=None,
        on_text=on_text,
    )
    assert text == "Hello world!"
    assert tool_calls == []
    assert text_parts == ["Hello", " world", "!"]


@pytest.mark.asyncio
async def test_streaming_tool_calls_fragmented(mocker):
    """OpenAI分片返回tool_calls，按index累积。"""
    chunks = [
        _make_chunk(tool_calls=[
            {"index": 0, "id": "call_1", "function": {"name": "web_search", "arguments": ""}},
        ]),
        _make_chunk(tool_calls=[
            {"index": 0, "function": {"arguments": '{"q":'}},
        ]),
        _make_chunk(tool_calls=[
            {"index": 0, "function": {"arguments": '"AI"}'}},
        ]),
        _make_chunk(finish_reason="tool_calls"),
    ]
    async def fake_create(**kwargs):
        for c in chunks:
            yield c

    provider = OpenAICompatProvider(
        base_url="https://api.test/v1", api_key="k", model="m",
    )
    mocker.patch.object(
        provider.client.chat.completions, "create", side_effect=fake_create
    )

    text, tool_calls, usage = await provider.chat(
        messages=[Message(role="user", content="hi")],
        system=None, tools=None,
        temperature=0.5, max_tokens=None, cancel=None, on_text=None,
    )
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "web_search"
    assert tool_calls[0].arguments == {"q": "AI"}


@pytest.mark.asyncio
async def test_usage_from_final_chunk(mocker):
    chunks = [
        _make_chunk(content="done", finish_reason="stop"),
    ]
    usage_obj = type("U", (), {
        "prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30,
    })()
    chunks[0].usage = usage_obj

    async def fake_create(**kw):
        for c in chunks:
            yield c

    provider = OpenAICompatProvider(
        base_url="https://api.test/v1", api_key="k", model="m",
    )
    mocker.patch.object(
        provider.client.chat.completions, "create", side_effect=fake_create
    )

    _, _, usage = await provider.chat(
        messages=[Message(role="user", content="hi")],
        system=None, tools=None,
        temperature=0.5, max_tokens=None, cancel=None, on_text=None,
    )
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 20
    assert usage.total_tokens == 30


@pytest.mark.asyncio
async def test_cancel_raises(mocker):
    cancel = __import__("asyncio").Event()
    cancel.set()

    async def fake_create(**kw):
        yield _make_chunk(content="x")
        if False:
            yield

    provider = OpenAICompatProvider(
        base_url="https://api.test/v1", api_key="k", model="m",
    )
    mocker.patch.object(
        provider.client.chat.completions, "create", side_effect=fake_create
    )

    import asyncio
    with pytest.raises(asyncio.CancelledError):
        await provider.chat(
            messages=[Message(role="user", content="hi")],
            system=None, tools=None,
            temperature=0.5, max_tokens=None, cancel=cancel, on_text=None,
        )

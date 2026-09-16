"""测试Agent主循环。"""
from __future__ import annotations
import asyncio
import pytest
from lumos.agent.core import Agent
from lumos.agent.message import Message, ToolCall, ToolSpec, Usage
from lumos.tools.base import Tool
from lumos.tools.registry import ToolRegistry, register_tool


@register_tool(
    name="mytool",
    description="test tool",
    parameters={
        "type": "object",
        "properties": {"q": {"type": "string"}},
        "required": ["q"],
    },
)
class MyTool(Tool):
    async def execute(self, *, q: str) -> str:
        return f"result for {q}"


class FakeProvider:
    def __init__(self, scripted: list[tuple[str, list[ToolCall]]]):
        self.scripted = list(scripted)
        self.calls: list[list[Message]] = []

    async def chat(self, messages, *, system, tools, temperature,
                   max_tokens, cancel, on_text):
        self.calls.append(list(messages))
        # 返回下一个脚本响应
        text, tool_calls = self.scripted.pop(0)
        if cancel:
            cancel.set()
        return text, tool_calls, Usage(10, 5, 15)


@pytest.mark.asyncio
async def test_agent_runs_until_no_tool_calls():
    provider = FakeProvider([("Hello!", [])])
    registry = ToolRegistry()
    registry.discover_globals([MyTool])

    agent = Agent(
        provider=provider,
        tool_registry=registry,
        skills=None,
        mcp=None,
        config=type("Cfg", (), {"max_steps": 5, "system_prompt": "BASE"})(),
    )

    events: list[str] = []
    async def on_event(e):
        events.append(e.type)

    usage = await agent.run("hi", on_event=on_event)
    assert usage.total_tokens == 15
    assert "done" in events


@pytest.mark.asyncio
async def test_agent_runs_tool_then_done():
    provider = FakeProvider([
        ("Searching...", [ToolCall(id="t1", name="mytool", arguments={"q": "AI"})]),
        ("Done", []),
    ])
    registry = ToolRegistry()
    registry.discover_globals([MyTool])

    agent = Agent(
        provider=provider,
        tool_registry=registry,
        skills=None,
        mcp=None,
        config=type("Cfg", (), {"max_steps": 5, "system_prompt": "BASE"})(),
    )

    events: list[dict] = []
    async def on_event(e):
        events.append({"type": e.type, "data": e.data})

    usage = await agent.run("hi", on_event=on_event)
    assert any(e["type"] == "tool_call_start" for e in events)
    assert any(e["type"] == "tool_call_result" for e in events)
    assert usage.total_tokens == 30


@pytest.mark.asyncio
async def test_agent_respects_max_steps():
    provider = FakeProvider([
        ("step1", [ToolCall(id="t1", name="mytool", arguments={"q": "a"})]),
        ("step2", [ToolCall(id="t2", name="mytool", arguments={"q": "b"})]),
        ("step3", [ToolCall(id="t3", name="mytool", arguments={"q": "c"})]),
    ])
    registry = ToolRegistry()
    registry.discover_globals([MyTool])

    agent = Agent(
        provider=provider,
        tool_registry=registry,
        skills=None,
        mcp=None,
        config=type("Cfg", (), {"max_steps": 2, "system_prompt": "BASE"})(),
    )

    with pytest.raises(Exception, match="[Mm]ax"):
        await agent.run("hi", on_event=lambda e: asyncio.sleep(0))

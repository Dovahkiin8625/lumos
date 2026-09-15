"""测试消息数据类。"""
from __future__ import annotations
import json
from lumos.agent.message import (
    Message, TextContent, ToolCall, ToolResult, Usage, AgentEvent,
)


def test_message_to_dict_roundtrip():
    msg = Message(
        role="assistant",
        content=[TextContent(text="hello")],
    )
    d = msg.to_dict()
    assert d["role"] == "assistant"
    assert d["content"] == [{"type": "text", "text": "hello"}]


def test_message_with_tool_calls():
    msg = Message(
        role="assistant",
        content=[
            TextContent(text="let me search"),
            ToolCall(id="t1", name="web_search", arguments={"q": "AI"}),
        ],
    )
    d = msg.to_dict()
    assert len(d["content"]) == 2
    assert d["content"][1]["type"] == "tool_call"
    assert d["content"][1]["name"] == "web_search"


def test_usage_defaults():
    u = Usage()
    assert u.prompt_tokens == 0
    assert u.total_tokens == 0


def test_agent_event_serialization():
    e = AgentEvent(
        type="text", session_id="s1",
        data={"delta": "hi"},
    )
    j = e.to_json()
    parsed = json.loads(j)
    assert parsed["type"] == "text"
    assert parsed["data"]["delta"] == "hi"

"""测试Tool注册中心。"""
from __future__ import annotations
import pytest
from lumos.tools.base import Tool
from lumos.tools.registry import ToolRegistry, register_tool


@register_tool(
    name="echo",
    description="echoes back",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)
class EchoTool(Tool):
    async def execute(self, *, text: str) -> str:
        return text


def test_decorator_registers():
    reg = ToolRegistry()
    reg.discover()
    spec = reg.get_spec("echo")
    assert spec is not None
    assert spec.name == "echo"


@pytest.mark.asyncio
async def test_execute():
    reg = ToolRegistry()
    reg.discover()
    tool = reg.get("echo")
    result = await tool.execute(text="hi")
    assert result == "hi"


def test_unregister():
    reg = ToolRegistry()
    reg.discover()
    assert reg.get("echo") is not None
    reg.unregister("echo")
    assert reg.get("echo") is None


def test_to_openai_format():
    reg = ToolRegistry()
    reg.discover()
    oai = reg.to_openai_tools()
    assert len(oai) >= 1
    assert any(t["function"]["name"] == "echo" for t in oai)

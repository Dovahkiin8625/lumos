"""Echo工具（测试discover机制用，Task 6移除）。"""
from __future__ import annotations
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool


@register_tool(
    name="echo",
    description="Echoes back the input text.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)
class EchoTool(Tool):
    async def execute(self, *, text: str) -> str:
        return text

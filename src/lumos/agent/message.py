"""统一的消息、工具调用、流式事件数据类。"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Literal, Any


@dataclass
class TextContent:
    text: str
    type: Literal["text"] = "text"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "text", "text": self.text}


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    type: Literal["tool_call"] = "tool_call"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "tool_call",
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }


@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False
    name: str | None = None

    def to_message(self) -> "Message":
        return Message(
            role="tool",
            content=[TextContent(text=self.content)],
            tool_call_id=self.tool_call_id,
            name=self.name,
        )


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    requires_confirmation: bool = False
    source: Literal["builtin", "mcp", "skill"] = "builtin"


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: list[TextContent | ToolCall | ToolResult] | str
    name: str | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if isinstance(self.content, str):
            content_val: Any = self.content
        else:
            content_val = [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in self.content
            ]
        d: dict[str, Any] = {"role": self.role, "content": content_val}
        if self.name is not None:
            d["name"] = self.name
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


EventType = Literal[
    "text", "tool_call_start", "tool_call_result",
    "tool_call_end", "confirm_required", "error", "usage", "done", "cancelled",
]


@dataclass
class AgentEvent:
    type: EventType
    session_id: str
    data: Any = None

    def to_json(self) -> str:
        return json.dumps(
            {"type": self.type, "session_id": self.session_id, "data": self.data},
            ensure_ascii=False,
        )

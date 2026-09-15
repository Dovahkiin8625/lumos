"""文件读写工具（受路径限制）。"""
from __future__ import annotations
from pathlib import Path
from lumos.config import ToolsConfig
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


def _resolve_safe(path_str: str, allowed: list[str]) -> Path:
    target = Path(path_str).expanduser().resolve()
    for prefix in allowed:
        try:
            target.relative_to(Path(prefix).expanduser().resolve())
            return target
        except ValueError:
            continue
    raise PermissionError(
        f"Path not allowed: {path_str}. Allowed: {allowed}"
    )


@register_tool(
    name="file_read",
    description="Read the contents of a local file. Path must be in allowed_paths.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "max_bytes": {"type": "integer", "default": 100000, "maximum": 1000000},
        },
        "required": ["path"],
    },
)
class FileReadTool(Tool):
    config: ToolsConfig | None = None

    async def execute(self, *, path: str, max_bytes: int = 100000) -> str:
        try:
            allowed = (self.config.allowed_paths if self.config else []) or []
            p = _resolve_safe(path, allowed)
            content = p.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_bytes:
                content = content[:max_bytes] + f"\n...[truncated, total {len(content)} chars]"
            return content
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="file_read", cause=e) from e


@register_tool(
    name="file_write",
    description="Write content to a local file. Path must be in allowed_paths.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    },
    requires_confirmation=True,
)
class FileWriteTool(Tool):
    config: ToolsConfig | None = None

    async def execute(self, *, path: str, content: str) -> str:
        try:
            allowed = (self.config.allowed_paths if self.config else []) or []
            p = _resolve_safe(path, allowed)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} chars to {p}"
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="file_write", cause=e) from e
"""受限shell执行。"""
from __future__ import annotations
import asyncio
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


@register_tool(
    name="shell_exec",
    description="Execute a shell command. Disabled by default; requires confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "default": 10, "minimum": 1, "maximum": 60},
        },
        "required": ["command"],
    },
    requires_confirmation=True,
)
class ShellTool(Tool):
    async def execute(self, *, command: str, timeout: int = 10) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout,
                )
            except asyncio.TimeoutError as e:
                proc.kill()
                raise ToolExecutionError(
                    f"Command timed out after {timeout}s",
                    tool_name="shell_exec", cause=e,
                ) from e
            output = (stdout or b"").decode("utf-8", errors="replace")
            err = (stderr or b"").decode("utf-8", errors="replace")
            result = output + (("\n[stderr] " + err) if err else "")
            if proc.returncode != 0:
                raise ToolExecutionError(
                    f"Exit code {proc.returncode}: {result}",
                    tool_name="shell_exec",
                )
            return result or "(no output)"
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                str(e), tool_name="shell_exec", cause=e,
            ) from e
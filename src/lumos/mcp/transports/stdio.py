"""stdio传输：本地子进程。"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from typing import Any
from lumos.errors import McpConnectionError


class StdioTransport:
    def __init__(
        self, *, command: str, args: tuple[str, ...] = (), env: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.args = args
        self.env = env or {}
        self.proc: asyncio.subprocess.Process | None = None
        self._stderr_task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            full_env = {**os.environ, **self.env}
            self.proc = await asyncio.create_subprocess_exec(
                self.command, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
            )
        except Exception as e:
            raise McpConnectionError(
                f"Failed to start stdio MCP: {self.command} {self.args}: {e}",
                cause=e,
            ) from e
        self._stderr_task = asyncio.create_task(self._drain_stderr())

    async def _drain_stderr(self) -> None:
        if self.proc and self.proc.stderr:
            while True:
                line = await self.proc.stderr.readline()
                if not line:
                    return
                import structlog
                structlog.get_logger().warning(
                    "mcp.stderr", server=self.command, line=line.decode(errors="replace").rstrip(),
                )

    async def read_message(self) -> dict[str, Any]:
        if not self.proc or not self.proc.stdout:
            raise McpConnectionError("stdio transport not started")
        line = await self.proc.stdout.readline()
        if not line:
            raise McpConnectionError("stdio MCP closed stdout")
        try:
            return json.loads(line.decode("utf-8").strip())
        except json.JSONDecodeError as e:
            raise McpConnectionError(f"Invalid JSON from stdio MCP: {e}") from e

    async def write_message(self, msg: dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise McpConnectionError("stdio transport not started")
        data = (json.dumps(msg) + "\n").encode("utf-8")
        self.proc.stdin.write(data)
        await self.proc.stdin.drain()

    async def close(self) -> None:
        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
                await asyncio.wait_for(self.proc.wait(), timeout=5.0)
            except (ProcessLookupError, asyncio.TimeoutError):
                self.proc.kill()
            self.proc = None
        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass
            self._stderr_task = None
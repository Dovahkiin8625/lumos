"""Agent主循环（ReAct风格）。"""
from __future__ import annotations
import asyncio
from typing import Awaitable, Callable
from lumos.agent.message import (
    Message, TextContent, ToolCall, ToolResult, Usage, AgentEvent, ToolSpec,
)
from lumos.tools.registry import ToolRegistry
from lumos.skills.manager import SkillManager
from lumos.mcp.manager import McpManager
from lumos.errors import MaxStepsExceededError, CancelledError, ToolExecutionError
from lumos.config import AgentConfig


OnEvent = Callable[[AgentEvent], Awaitable[None]]


class Agent:
    def __init__(
        self,
        *,
        provider,
        tool_registry: ToolRegistry,
        skills: SkillManager | None = None,
        mcp: McpManager | None = None,
        config: AgentConfig | None = None,
        skill_manager: SkillManager | None = None,
        mcp_manager: McpManager | None = None,
        agent_config: AgentConfig | None = None,
        history: list[Message] | None = None,
    ) -> None:
        self.provider = provider
        self.tools = tool_registry
        self.skills = skills if skills is not None else skill_manager
        self.mcp = mcp if mcp is not None else mcp_manager
        self.config = config if config is not None else agent_config
        self.history: list[Message] = list(history or [])

    def _collect_tool_specs(self) -> list[ToolSpec]:
        specs = self.tools.all_specs()
        if self.mcp is not None:
            specs.extend(self.mcp.all_tools())
        return specs

    async def _build_system_prompt(self) -> str:
        base = self.config.system_prompt
        if self.skills is None:
            return base
        return self.skills.build_system_prompt(base=base)

    async def _execute_tool(
        self, tc: ToolCall, on_event: OnEvent,
    ) -> ToolResult:
        try:
            if "__" in tc.name and self.mcp is not None:
                result_text = await self.mcp.call_tool(tc.name, tc.arguments)
            else:
                tool = self.tools.get(tc.name)
                result_text = await tool.execute(**tc.arguments)
            return ToolResult(
                tool_call_id=tc.id, content=result_text,
                is_error=False, name=tc.name,
            )
        except CancelledError:
            raise
        except Exception as e:
            error_text = f"Error: {type(e).__name__}: {e}"
            return ToolResult(
                tool_call_id=tc.id, content=error_text,
                is_error=True, name=tc.name,
            )

    async def run(
        self,
        user_input: str,
        *,
        on_event: OnEvent,
        cancel: asyncio.Event | None = None,
    ) -> Usage:
        cancel = cancel or asyncio.Event()
        total_usage = Usage()
        self.history.append(Message(role="user", content=user_input))

        for step in range(self.config.max_steps):
            system = await self._build_system_prompt()
            tool_specs = self._collect_tool_specs()

            async def on_text(delta: str) -> None:
                if cancel.is_set():
                    raise asyncio.CancelledError()
                await on_event(AgentEvent(
                    type="text", session_id="", data={"delta": delta},
                ))

            text, tool_calls, usage = await self.provider.chat(
                messages=self.history,
                system=system,
                tools=tool_specs,
                temperature=0.7,
                max_tokens=None,
                cancel=cancel,
                on_text=on_text,
            )
            total_usage.prompt_tokens += usage.prompt_tokens
            total_usage.completion_tokens += usage.completion_tokens
            total_usage.total_tokens += usage.total_tokens

            content: list = []
            if text:
                content.append(TextContent(text=text))
            for tc in tool_calls:
                content.append(tc)
            self.history.append(Message(role="assistant", content=content))

            await on_event(AgentEvent(
                type="usage", session_id="",
                data={
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                },
            ))

            if not tool_calls:
                await on_event(AgentEvent(
                    type="done", session_id="",
                    data={"usage": total_usage.__dict__},
                ))
                return total_usage

            # 并行执行所有tool_calls
            await on_event(AgentEvent(
                type="tool_call_start", session_id="",
                data={"calls": [tc.to_dict() for tc in tool_calls]},
            ))
            results = await asyncio.gather(
                *[self._execute_tool(tc, on_event) for tc in tool_calls],
                return_exceptions=False,
            )
            for tc, r in zip(tool_calls, results):
                self.history.append(r.to_message())
                await on_event(AgentEvent(
                    type="tool_call_result", session_id="",
                    data={
                        "tool_call_id": r.tool_call_id,
                        "name": tc.name,
                        "result": r.content,
                        "is_error": r.is_error,
                    },
                ))
            await on_event(AgentEvent(
                type="tool_call_end", session_id="", data=None,
            ))

        raise MaxStepsExceededError(
            f"Agent exceeded max_steps={self.config.max_steps}"
        )

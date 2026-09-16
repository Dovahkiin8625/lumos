"""单session Agent运行器：管理cancel事件、on_event回调、生命周期。"""
from __future__ import annotations
import asyncio
from typing import Awaitable, Callable
from lumos.agent.core import Agent
from lumos.agent.message import AgentEvent
from lumos.tools.registry import ToolRegistry
from lumos.skills.manager import SkillManager
from lumos.mcp.manager import McpManager
from lumos.providers.base import BaseProvider
from lumos.config import AgentConfig


OnEvent = Callable[[AgentEvent], Awaitable[None]]


class AgentRunner:
    """一个session对应一个AgentRunner实例。"""

    def __init__(
        self,
        *,
        session_id: str,
        provider: BaseProvider,
        tool_registry: ToolRegistry,
        skill_manager: SkillManager | None,
        mcp_manager: McpManager | None,
        agent_config: AgentConfig,
        history: list | None = None,
    ) -> None:
        self.session_id = session_id
        self.cancel = asyncio.Event()
        self.agent = Agent(
            provider=provider,
            tool_registry=tool_registry,
            skill_manager=skill_manager,
            mcp_manager=mcp_manager,
            agent_config=agent_config,
            history=list(history or []),
        )

    async def run(self, user_input: str, on_event: OnEvent) -> None:
        self.cancel.clear()
        await self.agent.run(user_input, on_event=on_event, cancel=self.cancel)

    def request_cancel(self) -> None:
        self.cancel.set()

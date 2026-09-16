"""Session→AgentRunner 池（单例）。"""
from __future__ import annotations
import asyncio
from lumos.agent.runner import AgentRunner


class Runners:
    """每个session一个AgentRunner，惰性创建。"""

    def __init__(self) -> None:
        self._runners: dict[str, AgentRunner] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self, session_id: str, *, app,
    ) -> AgentRunner:
        async with self._lock:
            if session_id in self._runners:
                return self._runners[session_id]
            from lumos.persistence.repositories.messages import MessageRepository
            from sqlalchemy.ext.asyncio import async_sessionmaker
            factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
            async with factory() as db:
                msg_repo = MessageRepository(db)
                history = await msg_repo.load_history(session_id)
            runner = AgentRunner(
                session_id=session_id,
                provider=app.state.provider,
                tool_registry=app.state.tool_registry,
                skill_manager=app.state.skill_manager,
                mcp_manager=app.state.mcp_manager,
                agent_config=app.state.config.agent,
                history=history,
            )
            self._runners[session_id] = runner
            return runner

    async def discard(self, session_id: str) -> None:
        self._runners.pop(session_id, None)
"""MCP服务器配置仓储。"""
from __future__ import annotations
import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.persistence.models import McpServer


class McpServerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: str) -> list[McpServer]:
        stmt = (
            select(McpServer)
            .where(McpServer.user_id == user_id)
            .order_by(McpServer.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, server_id: str, user_id: str) -> McpServer | None:
        ms = await self.session.get(McpServer, server_id)
        if ms is None or ms.user_id != user_id:
            return None
        return ms

    async def upsert(
        self, *, user_id: str, name: str, config_json: str, enabled: bool = True,
    ) -> McpServer:
        existing = await self.get_by_name(user_id, name)
        if existing is not None:
            existing.config = config_json
            existing.enabled = enabled
            await self.session.commit()
            return existing
        ms = McpServer(
            id=str(uuid.uuid4()), user_id=user_id, name=name,
            config=config_json, enabled=enabled,
        )
        self.session.add(ms)
        await self.session.commit()
        await self.session.refresh(ms)
        return ms

    async def get_by_name(self, user_id: str, name: str) -> McpServer | None:
        stmt = select(McpServer).where(
            McpServer.user_id == user_id, McpServer.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, server_id: str, user_id: str) -> bool:
        ms = await self.get(server_id, user_id)
        if ms is None:
            return False
        await self.session.delete(ms)
        await self.session.commit()
        return True
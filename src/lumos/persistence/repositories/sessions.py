"""聊天会话仓储。"""
from __future__ import annotations
import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.persistence.models import ChatSession


class ChatSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, user_id: str, title: str = "新会话") -> ChatSession:
        cs = ChatSession(
            id=str(uuid.uuid4()), user_id=user_id,
            title=title, enabled_skills="[]", model_config="{}",
        )
        self.session.add(cs)
        await self.session.commit()
        await self.session.refresh(cs)
        return cs

    async def list_by_user(
        self, user_id: str, *, limit: int = 50, offset: int = 0,
    ) -> list[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit).offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, session_id: str, user_id: str) -> ChatSession | None:
        cs = await self.session.get(ChatSession, session_id)
        if cs is None or cs.user_id != user_id:
            return None
        return cs

    async def update_title(self, session_id: str, title: str) -> None:
        cs = await self.session.get(ChatSession, session_id)
        if cs is not None:
            cs.title = title
            await self.session.commit()

    async def update_skills(self, session_id: str, skills_json: str) -> None:
        cs = await self.session.get(ChatSession, session_id)
        if cs is not None:
            cs.enabled_skills = skills_json
            await self.session.commit()

    async def delete(self, session_id: str, user_id: str) -> bool:
        cs = await self.get(session_id, user_id)
        if cs is None:
            return False
        await self.session.delete(cs)
        await self.session.commit()
        return True
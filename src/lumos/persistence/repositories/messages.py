"""消息仓储。"""
from __future__ import annotations
import json
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.agent.message import Message, TextContent, ToolCall as TC
from lumos.persistence.models import Message as MsgModel


def _serialize_message(msg: Message) -> dict:
    if isinstance(msg.content, str):
        content_str = msg.content
    else:
        content_str = json.dumps(
            [c.to_dict() for c in msg.content],
            ensure_ascii=False,
        )
    tool_calls_json = None
    if isinstance(msg.content, list):
        tcs = [c for c in msg.content if c.type == "tool_call"]
        if tcs:
            tool_calls_json = json.dumps(
                [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in tcs],
                ensure_ascii=False,
            )
    return {
        "content": content_str,
        "tool_calls": tool_calls_json,
        "name": msg.name,
        "tool_call_id": msg.tool_call_id,
    }


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        *,
        session_id: str,
        role: str,
        message: Message,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> MsgModel:
        data = _serialize_message(message)
        m = MsgModel(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=data["content"],
            tool_calls=data["tool_calls"],
            tool_call_id=data["tool_call_id"],
            name=data["name"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        self.session.add(m)
        await self.session.commit()
        await self.session.refresh(m)
        return m

    async def list_by_session(
        self, session_id: str, *, limit: int = 200, before_id: str | None = None,
    ) -> list[MsgModel]:
        stmt = (
            select(MsgModel)
            .where(MsgModel.session_id == session_id)
            .order_by(MsgModel.created_at.asc())
            .limit(limit)
        )
        if before_id is not None:
            before = await self.session.get(MsgModel, before_id)
            if before:
                stmt = stmt.where(MsgModel.created_at < before.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def load_history(self, session_id: str) -> list[Message]:
        rows = await self.list_by_session(session_id, limit=1000)
        out: list[Message] = []
        for r in rows:
            if r.role == "tool":
                out.append(Message(
                    role="tool",
                    content=[TextContent(text=r.content)],
                    tool_call_id=r.tool_call_id,
                    name=r.name,
                ))
            elif r.tool_calls:
                try:
                    parts_raw = json.loads(r.content)
                    tc_raws = json.loads(r.tool_calls)
                    parts = [TextContent(text=p["text"]) for p in parts_raw if p.get("type") == "text"]
                    parts.extend(
                        TC(id=t["id"], name=t["name"], arguments=t["arguments"])
                        for t in tc_raws
                    )
                    out.append(Message(role="assistant", content=parts))
                except Exception:
                    out.append(Message(role="assistant", content=r.content))
            else:
                out.append(Message(role=r.role, content=r.content))
        return out
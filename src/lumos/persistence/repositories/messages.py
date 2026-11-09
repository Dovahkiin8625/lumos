"""消息仓储。"""
from __future__ import annotations
import json
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.agent.message import Message, TextContent, ToolCall as TC
from lumos.persistence.models import Message as MsgModel


def _serialize_message(msg: Message) -> dict:
    # content 列只存 markdown 文本（来自 TextContent 拼接）。
    # tool_calls 单独存到 tool_calls 列。旧版会把所有 part JSON 化塞进 content，
    # 导致纯文本回复也被渲染成 `[{"type":"text","text":"..."}]`。
    if isinstance(msg.content, str):
        content_str = msg.content
    else:
        text_parts = [c.text for c in msg.content if c.type == "text"]
        content_str = "".join(text_parts)
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


def decode_legacy_json_content(raw: str) -> str | None:
    """旧版数据中 content 列是 JSON 列表（如 `[{"type":"text","text":"..."}]`），
    这里提取 text 段并拼接。

    返回值约定：
    - 解析失败 / 不是列表 / 没有 text 段 → ``None``。调用方按原值使用，
      避免覆盖可能含图片/文件/工具调用等非文本段的旧数据。
    - 至少有一个 text 段 → 拼接后的纯文本。
    """
    stripped = raw.lstrip()
    if not stripped.startswith("["):
        return None
    try:
        parts = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(parts, list):
        return None
    text_parts = [
        p.get("text", "")
        for p in parts
        if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text", ""), str)
    ]
    if not text_parts:
        return None
    return "".join(text_parts)


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
                # 优先使用新版纯文本格式；旧版回退到 JSON 列表解析。
                content_str = r.content
                # tool_calls 列偶有损坏（旧版本 bug、手动编辑、迁移失败）。
                # 一旦 json.loads 抛错，整个 session 的 history 都会读不出来——所以
                # 这里降级为：丢弃该行 tool_calls，按纯文本处理。绝不向调用方抛错。
                try:
                    tc_raws = json.loads(r.tool_calls)
                    tcs = [
                        TC(id=t["id"], name=t["name"], arguments=t["arguments"])
                        for t in tc_raws
                    ]
                except (ValueError, TypeError):
                    tc_raws = None
                    tcs = []
                legacy_text = decode_legacy_json_content(r.content)
                if legacy_text is not None:
                    content_str = legacy_text
                parts: list = []
                if content_str:
                    parts.append(TextContent(text=content_str))
                parts.extend(tcs)
                out.append(Message(role="assistant", content=parts))
            else:
                # 旧版可能把纯文本回复也 JSON 化了，这里同样兜底。
                legacy_text = decode_legacy_json_content(r.content)
                content_val = legacy_text if legacy_text is not None else r.content
                out.append(Message(role=r.role, content=content_val))
        return out
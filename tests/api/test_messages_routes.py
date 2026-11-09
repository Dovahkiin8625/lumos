"""测试消息路由 + assistant 消息持久化格式。"""
from __future__ import annotations
import pytest
from httpx import AsyncClient

from lumos.agent.message import Message, TextContent, ToolCall
from lumos.persistence.repositories.messages import MessageRepository, _serialize_message
from lumos.persistence.repositories.sessions import ChatSessionRepository
from lumos.persistence.repositories.users import UserRepository
from lumos.persistence.db import get_engine
from lumos.api.auth_utils import hash_password


async def _auth_and_session(client: AsyncClient):
    r = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    token = r.json()["access_token"]
    r = await client.post("/api/sessions", json={}, headers={"Authorization": f"Bearer {token}"})
    return token, r.json()["id"]


@pytest.mark.asyncio
async def test_list_messages_empty(client: AsyncClient):
    token, sid = await _auth_and_session(client)
    r = await client.get(f"/api/sessions/{sid}/messages", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


# ───────── 序列化层单元测试 ─────────

def test_serialize_text_only_assistant_message():
    """仅含 TextContent 的 assistant 消息，content 列应存纯文本而非 JSON 列表。"""
    msg = Message(role="assistant", content=[TextContent(text="你好世界")])
    data = _serialize_message(msg)
    assert data["content"] == "你好世界"
    assert data["tool_calls"] is None


def test_serialize_assistant_with_tool_calls():
    """含 TextContent + ToolCall 的 assistant 消息：content 存纯文本，tool_calls 存 JSON。"""
    msg = Message(
        role="assistant",
        content=[
            TextContent(text=""),
            ToolCall(id="c1", name="datetime_now", arguments={}),
        ],
    )
    data = _serialize_message(msg)
    assert data["content"] == ""
    assert data["tool_calls"] is not None
    import json
    parsed = json.loads(data["tool_calls"])
    assert parsed == [{"id": "c1", "name": "datetime_now", "arguments": {}}]


def test_serialize_user_message_string_content():
    """user 消息（content 为字符串）保持原样。"""
    msg = Message(role="user", content="写个函数")
    data = _serialize_message(msg)
    assert data["content"] == "写个函数"
    assert data["tool_calls"] is None


# ───────── API 端到端测试 ─────────

@pytest.mark.asyncio
async def test_api_returns_plain_text_for_assistant_without_tool_calls(
    app, client: AsyncClient,
):
    """核心回归测试：assistant 纯文本回复的 content 字段必须是 markdown 文本，
    不能是 JSON 列表。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    token, sid = await _auth_and_session(client)

    # 直接通过 repository 写入一条"完成态"的 assistant 消息（content 为 list 形式，
    # 模拟 agent.core.py 在 done 事件后持久化最后一条历史）。
    engine = app.state.engine
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        repo = MessageRepository(db)
        await repo.append(
            session_id=sid,
            role="assistant",
            message=Message(
                role="assistant",
                content=[TextContent(text="# 标题\n\n正文内容")],
            ),
            prompt_tokens=10,
            completion_tokens=20,
        )

    # GET 历史
    r = await client.get(
        f"/api/sessions/{sid}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 1
    content = msgs[0]["content"]
    assert content == "# 标题\n\n正文内容"
    assert not content.startswith("[")
    assert msgs[0]["tool_calls"] is None
    assert msgs[0]["prompt_tokens"] == 10
    assert msgs[0]["completion_tokens"] == 20


@pytest.mark.asyncio
async def test_api_returns_tool_calls_and_plain_text_for_assistant_with_tool_calls(
    app, client: AsyncClient,
):
    """assistant 消息同时含文本和 tool_calls：content 应是纯文本、tool_calls 是列表。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    token, sid = await _auth_and_session(client)

    factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with factory() as db:
        repo = MessageRepository(db)
        await repo.append(
            session_id=sid,
            role="assistant",
            message=Message(
                role="assistant",
                content=[
                    TextContent(text="我先查一下时间。"),
                    ToolCall(id="call_1", name="datetime_now", arguments={}),
                ],
            ),
        )

    r = await client.get(
        f"/api/sessions/{sid}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    msgs = r.json()
    assert len(msgs) == 1
    assert msgs[0]["content"] == "我先查一下时间。"
    assert msgs[0]["tool_calls"] == [
        {"id": "call_1", "name": "datetime_now", "arguments": {}}
    ]


@pytest.mark.asyncio
async def test_api_decodes_legacy_json_wrapped_assistant_content(
    app, client: AsyncClient,
):
    """向后兼容：旧数据（content 列里存的是 JSON 列表）也要正确提取 text。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    import json

    token, sid = await _auth_and_session(client)

    factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with factory() as db:
        # 模拟旧版写入：用 raw SQL 直接插一行 content 是 JSON 列表
        from lumos.persistence.models import Message as MsgModel
        import uuid
        async with factory() as db:
            m = MsgModel(
                id=str(uuid.uuid4()),
                session_id=sid,
                role="assistant",
                content=json.dumps(
                    [{"type": "text", "text": "旧数据：你好"}],
                    ensure_ascii=False,
                ),
                tool_calls=None,
                tool_call_id=None,
                name=None,
                prompt_tokens=0,
                completion_tokens=0,
            )
            db.add(m)
            await db.commit()

    r = await client.get(
        f"/api/sessions/{sid}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    msgs = r.json()
    assert len(msgs) == 1
    assert msgs[0]["content"] == "旧数据：你好"
    assert msgs[0]["tool_calls"] is None


@pytest.mark.asyncio
async def test_load_history_keeps_image_only_legacy_content_intact(
    app, client: AsyncClient,
):
    """旧数据若只有 image/file 等非 text 段（无 text 段），不能把 content 改成空串。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from lumos.persistence.models import Message as MsgModel
    from lumos.persistence.repositories.messages import MessageRepository
    import uuid, json

    _, sid = await _auth_and_session(client)

    factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with factory() as db:
        m = MsgModel(
            id=str(uuid.uuid4()),
            session_id=sid,
            role="assistant",
            content=json.dumps(
                [{"type": "image", "url": "https://example.com/x.png"}],
                ensure_ascii=False,
            ),
            tool_calls=None,
            tool_call_id=None,
            name=None,
            prompt_tokens=0,
            completion_tokens=0,
        )
        db.add(m)
        await db.commit()

    async with factory() as db:
        repo = MessageRepository(db)
        history = await repo.load_history(sid)

    # 不应被替换成空串——保留原 JSON 字符串以不丢失元数据
    assert len(history) == 1
    content = history[0].content
    if isinstance(content, list):
        text = "".join(c.text for c in content if c.type == "text")
        # 没有任何 text 段；content_str 仍保持原值（text 应等于原始 content）
        assert text == json.dumps(
            [{"type": "image", "url": "https://example.com/x.png"}],
            ensure_ascii=False,
        )
    else:
        # 纯文本 path：原 content 保留
        assert "image" in content and "https://example.com/x.png" in content


@pytest.mark.asyncio
async def test_load_history_tolerates_corrupt_tool_calls_json(
    app, client: AsyncClient,
):
    """DB 里有 tool_calls JSON 损坏的行时，load_history 必须不抛异常（否则全 session 不可用）。"""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from lumos.persistence.models import Message as MsgModel
    from lumos.persistence.repositories.messages import MessageRepository
    import uuid

    _, sid = await _auth_and_session(client)

    factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with factory() as db:
        m = MsgModel(
            id=str(uuid.uuid4()),
            session_id=sid,
            role="assistant",
            content="some text",
            tool_calls="{not valid json",  # 损坏的 JSON
            tool_call_id=None,
            name=None,
            prompt_tokens=0,
            completion_tokens=0,
        )
        db.add(m)
        await db.commit()

    async with factory() as db:
        repo = MessageRepository(db)
        history = await repo.load_history(sid)  # 不应抛 JSONDecodeError

    # 损坏行被丢弃（或降级为文本消息）；不应抛错阻断整个 history
    assert isinstance(history, list)
    # 至少要能返回空列表或正常助手消息
    assert all(isinstance(m, Message) for m in history)
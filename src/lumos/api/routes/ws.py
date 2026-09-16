"""WebSocket流式对话路由。"""
from __future__ import annotations
import asyncio
import json
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from lumos.api.auth_utils import decode_token
from lumos.config import get_config
from lumos.persistence.repositories.users import UserRepository
from lumos.persistence.repositories.sessions import ChatSessionRepository
from lumos.persistence.repositories.messages import MessageRepository
from lumos.api.runners import Runners
from lumos.agent.message import Message, TextContent, AgentEvent
from lumos.errors import CancelledError

router = APIRouter()


@router.websocket("/ws/sessions/{session_id}")
async def chat_ws(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
):
    cfg = get_config()
    try:
        payload = decode_token(token, secret=cfg.auth.jwt_secret, expected_type="access")
        user_id = payload["sub"]
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    app = websocket.app
    from sqlalchemy.ext.asyncio import async_sessionmaker
    factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with factory() as db:
        cs_repo = ChatSessionRepository(db)
        cs = await cs_repo.get(session_id, user_id)
        if cs is None:
            await websocket.send_text(json.dumps({
                "type": "error", "session_id": session_id,
                "data": {"message": "session not found"},
            }))
            await websocket.close()
            return

    runners: Runners = app.state.runners
    runner = await runners.get_or_create(session_id, app=app)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await websocket.send_text(json.dumps({
                    "type": "error", "session_id": session_id,
                    "data": {"message": "invalid JSON"},
                }))
                continue
            mtype = msg.get("type")
            if mtype == "cancel":
                runner.request_cancel()
                continue
            if mtype == "user_message":
                content = msg.get("content", "")
                # 持久化user消息
                async with factory() as db:
                    msg_repo = MessageRepository(db)
                    await msg_repo.append(
                        session_id=session_id, role="user",
                        message=Message(role="user", content=content),
                    )

                async def on_event(event: AgentEvent):
                    event.session_id = session_id
                    await websocket.send_text(event.to_json())
                    # 持久化assistant消息
                    if event.type == "done":
                        async with factory() as db2:
                            mr = MessageRepository(db2)
                            last = runner.agent.history[-1]
                            usage_data = event.data.get("usage", {})
                            await mr.append(
                                session_id=session_id, role="assistant",
                                message=last,
                                prompt_tokens=usage_data.get("prompt_tokens", 0),
                                completion_tokens=usage_data.get("completion_tokens", 0),
                            )

                try:
                    await runner.run(content, on_event=on_event)
                except CancelledError:
                    await websocket.send_text(AgentEvent(
                        type="cancelled", session_id=session_id,
                    ).to_json())
                except Exception as e:
                    await websocket.send_text(AgentEvent(
                        type="error", session_id=session_id,
                        data={"message": str(e)},
                    ).to_json())
    except WebSocketDisconnect:
        runner.request_cancel()
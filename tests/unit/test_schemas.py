"""测试Pydantic schema验证。"""
from __future__ import annotations
import pytest
from pydantic import ValidationError
from lumos.api.schemas import (
    RegisterRequest, LoginRequest, SessionCreate,
    McpServerCreate, ChatMessageRequest,
)


def test_register_request_valid():
    r = RegisterRequest(email="a@b.com", password="hunter22")
    assert r.email == "a@b.com"


def test_register_request_password_too_short():
    with pytest.raises(ValidationError):
        RegisterRequest(email="a@b.com", password="short")


def test_register_request_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="hunter22")


def test_mcp_server_create_stdio():
    s = McpServerCreate(
        name="fs", transport="stdio",
        command="npx", args=["-y", "fake"],
    )
    assert s.transport == "stdio"


def test_mcp_server_create_requires_url_for_http():
    with pytest.raises(ValidationError):
        McpServerCreate(name="x", transport="sse", url=None)


def test_chat_message_request():
    m = ChatMessageRequest(content="hi", enabled_skills=["web-research"])
    assert m.content == "hi"
    assert m.enabled_skills == ["web-research"]

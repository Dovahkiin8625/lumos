"""API Pydantic schemas。"""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SessionCreate(BaseModel):
    title: str | None = None
    enabled_skills: list[str] = Field(default_factory=list)


class SessionUpdate(BaseModel):
    title: str | None = None
    enabled_skills: list[str] | None = None
    model_config_json: str | None = None


class SessionOut(BaseModel):
    id: str
    title: str
    enabled_skills: list[str]
    created_at: datetime
    updated_at: datetime


class ChatMessageRequest(BaseModel):
    content: str
    enabled_skills: list[str] = Field(default_factory=list)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    tool_calls: list | None = None
    tool_call_id: str | None = None
    name: str | None = None
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime


class SkillOut(BaseModel):
    name: str
    description: str
    enabled: bool
    required_tools: list[str]
    optional_tools: list[str]


class McpServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    transport: Literal["stdio", "sse", "streamable_http"]
    enabled: bool = True
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def _url_required_for_http(cls, v: str | None, info) -> str | None:
        transport = info.data.get("transport")
        if transport in ("sse", "streamable_http") and not v:
            raise ValueError("url is required for http transports")
        return v

    @field_validator("command")
    @classmethod
    def _command_required_for_stdio(cls, v: str | None, info) -> str | None:
        transport = info.data.get("transport")
        if transport == "stdio" and not v:
            raise ValueError("command is required for stdio transport")
        return v


class McpServerOut(BaseModel):
    id: str
    name: str
    transport: str
    enabled: bool
    config: dict


class ToolConfirmRequest(BaseModel):
    tool_call_id: str
    confirmed: bool


class HealthResponse(BaseModel):
    status: str
    version: str
    providers: dict[str, str]
    mcp_servers: dict[str, str]
    db: str

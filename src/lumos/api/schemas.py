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
    version: str
    tags: list[str]
    required_tools: list[str]
    optional_tools: list[str]
    max_steps: int | None = None
    instructions: str
    enabled: bool
    dir_path: str


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    version: str = "0.0.0"
    tags: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    optional_tools: list[str] = Field(default_factory=list)
    max_steps: int | None = Field(default=None, ge=1, le=200)
    instructions: str = ""


class SkillUpdate(BaseModel):
    description: str | None = None
    version: str | None = None
    tags: list[str] | None = None
    required_tools: list[str] | None = None
    optional_tools: list[str] | None = None
    max_steps: int | None = Field(default=None, ge=1, le=200)
    instructions: str | None = None


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


# ---------------------------------------------------------------------------
# 知识库 (Knowledge Base) 相关 schemas
# ---------------------------------------------------------------------------


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=500)
    embedding_model: str = Field(default="bge-m3", max_length=64)
    rerank_model: str = Field(default="bge-reranker-v2-m3", max_length=64)
    chunk_size: int = Field(default=500, ge=64, le=4096)
    chunk_overlap: int = Field(default=75, ge=0, le=512)
    enabled: bool = True

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_less_than_size(cls, v: int, info) -> int:
        size = info.data.get("chunk_size")
        if size is not None and v >= size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return v


class KnowledgeBaseUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    chunk_size: int | None = Field(default=None, ge=64, le=4096)
    chunk_overlap: int | None = Field(default=None, ge=0, le=512)
    enabled: bool | None = None


class KnowledgeBaseOut(BaseModel):
    id: str
    name: str
    description: str
    embedding_model: str
    rerank_model: str
    chunk_size: int
    chunk_overlap: int
    milvus_collection: str
    enabled: bool
    document_count: int = 0
    indexed_chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


# 文档状态枚举
DOC_STATUS_PENDING = "pending"
DOC_STATUS_PARSING = "parsing"
DOC_STATUS_CHUNKING = "chunking"
DOC_STATUS_EMBEDDING = "embedding"
DOC_STATUS_READY = "ready"
DOC_STATUS_FAILED = "failed"
DOC_STATUS_DELETING = "deleting"

ALLOWED_DOC_STATUSES = frozenset({
    DOC_STATUS_PENDING,
    DOC_STATUS_PARSING,
    DOC_STATUS_CHUNKING,
    DOC_STATUS_EMBEDDING,
    DOC_STATUS_READY,
    DOC_STATUS_FAILED,
    DOC_STATUS_DELETING,
})


class KnowledgeDocumentOut(BaseModel):
    id: str
    kb_id: str
    filename: str
    mime_type: str
    file_size: int
    status: str
    error: str | None = None
    chunk_count: int
    page_count: int | None = None
    doc_metadata: dict = Field(default_factory=dict)
    created_at: datetime
    indexed_at: datetime | None = None


class KnowledgeDocumentStatusOut(BaseModel):
    id: str
    status: str
    error: str | None = None
    chunk_count: int
    indexed_at: datetime | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2048)
    top_k: int = Field(default=8, ge=1, le=50)
    search_top_k: int = Field(default=50, ge=1, le=200)
    use_rerank: bool = True
    filter_filename: str | None = None


class RetrievalHit(BaseModel):
    text: str
    score: float
    doc_id: str
    chunk_index: int
    section_header: str | None = None
    page_number: int | None = None
    filename: str
    title: str | None = None
    citation: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    hits: list[RetrievalHit]
    rerank_used: bool
    took_ms: int

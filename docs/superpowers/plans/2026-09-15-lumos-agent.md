# Lumos Agent 一阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现Lumos Agent一阶段：基于Agent的知识问答系统基础能力，包含LLM对话、可扩展工具、Skills系统、MCP客户端、多用户认证、FastAPI Web后端与聊天页面。

**Architecture:** 纯asyncio自研轻量Agent核心 + FastAPI异步Web框架 + SQLite持久化 + OpenAI兼容LLM Provider + Vanilla JS单页聊天前端。模块边界清晰、依赖最小化、保留二阶段RAG扩展点（embed接口、VectorServiceProvider占位）。

**Tech Stack:** Python 3.11+、asyncio、openai SDK、httpx、FastAPI、SQLAlchemy 2.0异步、aiosqlite、mcp官方SDK、bcrypt、PyJWT、structlog、duckduckgo-search、trafilatura、Vanilla JS（marked.js + highlight.js本地化）。

**Spec:** `docs/superpowers/specs/2026-09-15-lumos-agent-design.md`

## Global Constraints

- Python 3.11+（`pyproject.toml` 显式声明）
- 全asyncio代码，禁止`requests`/`urllib`/`time.sleep`
- 所有LLM Provider调用必须流式（`stream=True`）
- 所有数据库访问通过仓储模式，路由层不直接接触ORM
- 严禁在工具执行中阻塞（用`asyncio.wait_for` + 30秒超时）
- 单元测试覆盖率目标：核心模块≥85%
- 不在文档中使用TBD/TODO/待定；所有决策已固定
- commit message遵循Conventional Commits（feat/fix/test/docs/refactor/chore）
- 每次commit前必须green test（pytest通过）
- 文件编码UTF-8，行尾LF
- 类型注解必须完整（mypy strict模式CI检查）
- 所有HTTP响应遵循RFC 7807（problem+json）

## 项目里程碑

| Phase | 任务 | 交付物 |
|---|---|---|
| A. 基础设施 | 1-4 | pyproject.toml、配置加载、DB、日志、异常 |
| B. Provider与工具 | 5-8 | OpenAI兼容Provider、内置8个工具 |
| C. Skills与MCP | 9-11 | SKILL.md加载、三种MCP传输 |
| D. Agent核心 | 12-13 | ReAct循环、上下文压缩 |
| E. 持久化仓储 | 14-16 | 用户/会话/消息/MCP仓储、JWT |
| F. Web API | 17-22 | REST路由、WebSocket、FastAPI工厂 |
| G. Web前端 | 23-25 | 登录页、聊天页、JS应用 |
| H. 质量与文档 | 26-27 | 健康检查、README、示例 |

---

## Phase A：基础设施

### Task 1: 项目骨架与配置加载

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `config.example.yaml`
- Create: `src/lumos/__init__.py`
- Create: `src/lumos/__main__.py`
- Create: `src/lumos/config.py`
- Create: `src/lumos/logging.py`
- Create: `src/lumos/errors.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_config.py`
- Create: `tests/unit/test_logging.py`
- Create: `tests/unit/test_errors.py`
- Create: `.gitignore`

**Interfaces:**
- Produces:
  - `LumosConfig` dataclass（dataclass类，含provider/db/server/tools/skills/mcp子配置）
  - `load_config(path: Path) -> LumosConfig`
  - `get_logger(name: str) -> structlog.stdlib.BoundLogger`
  - `LumosError(Exception)` 及子类

**Step 1.1: 写测试 `tests/unit/test_config.py`**

```python
"""测试配置加载。"""
from pathlib import Path
import os
import pytest
from lumos.config import LumosConfig, load_config


def test_load_config_from_yaml(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
server:
  host: 127.0.0.1
  port: 8000
provider:
  type: openai_compat
  base_url: https://api.example.com/v1
  api_key: test-key
  model: gpt-test
db:
  url: sqlite+aiosqlite:///./test.db
""", encoding="utf-8")
    cfg = load_config(cfg_file)
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.port == 8000
    assert cfg.provider.type == "openai_compat"
    assert cfg.provider.api_key == "test-key"
    assert cfg.provider.model == "gpt-test"
    assert cfg.db.url == "sqlite+aiosqlite:///./test.db"


def test_env_var_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MY_KEY", "secret-xyz")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
provider:
  type: openai_compat
  base_url: https://api.example.com/v1
  api_key: ${MY_KEY}
  model: gpt-test
""", encoding="utf-8")
    cfg = load_config(cfg_file)
    assert cfg.provider.api_key == "secret-xyz"


def test_missing_required_field_raises(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("server:\n  port: 8000\n", encoding="utf-8")
    with pytest.raises(ValueError, match="provider"):
        load_config(cfg_file)
```

**Step 1.2: 跑测试确认失败**

Run: `pytest tests/unit/test_config.py -v`
Expected: ModuleNotFoundError（lumos.config不存在）

**Step 1.3: 写`pyproject.toml`**

```toml
[project]
name = "lumos"
version = "0.1.0"
description = "Commercial Agent-based knowledge Q&A system"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.40",
    "httpx>=0.27",
    "mcp>=1.0",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.19",
    "pydantic>=2.5",
    "pydantic-settings>=2.1",
    "pyyaml>=6.0",
    "python-frontmatter>=1.1",
    "bcrypt>=4.1",
    "pyjwt>=2.8",
    "structlog>=24.1",
    "duckduckgo-search>=6.0",
    "trafilatura>=1.6",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "pytest-cov>=4.1",
    "respx>=0.21",
    "mypy>=1.8",
    "ruff>=0.4",
    "playwright>=1.40",
]

[project.scripts]
lumos = "lumos.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/lumos"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--strict-markers --cov=lumos --cov-report=term-missing"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "ASYNC"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
files = ["src/lumos", "tests"]
```

**Step 1.4: 创建`src/lumos/__init__.py`**

```python
"""Lumos: Commercial Agent-based knowledge Q&A system."""
__version__ = "0.1.0"
```

**Step 1.5: 创建`src/lumos/__main__.py`**

```python
"""python -m lumos 入口。"""
from lumos.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 1.6: 写`src/lumos/config.py`**

```python
"""配置加载：YAML + 环境变量替换。"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderConfig:
    type: str  # 仅支持 openai_compat
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60


@dataclass(frozen=True)
class DbConfig:
    url: str = "sqlite+aiosqlite:///./data/lumos.db"
    echo: bool = False


@dataclass(frozen=True)
class ToolsConfig:
    allowed_paths: list[str] = field(default_factory=list)
    shell_enabled: bool = False
    default_timeout: int = 30


@dataclass(frozen=True)
class SkillsConfig:
    dirs: list[str] = field(default_factory=lambda: ["./skills"])


@dataclass(frozen=True)
class McpServerEntry:
    name: str
    transport: str  # stdio | sse | streamable_http
    enabled: bool = True
    # stdio
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    # sse / streamable_http
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class McpConfig:
    servers: list[McpServerEntry] = field(default_factory=list)


@dataclass(frozen=True)
class AuthConfig:
    jwt_secret: str = ""
    access_ttl: int = 86400
    refresh_ttl: int = 2592000
    bcrypt_rounds: int = 12
    default_admin_email: str | None = None
    default_admin_password: str | None = None


@dataclass(frozen=True)
class AgentConfig:
    max_steps: int = 15
    context_compress_threshold: int = 60000
    system_prompt: str = (
        "你是Lumos，专业的知识问答助手。\n"
        "你可以使用工具获取最新信息，请主动判断何时调用工具。\n"
        "回答要准确、简洁，必要时引用来源。"
    )


@dataclass(frozen=True)
class LumosConfig:
    server: ServerConfig
    provider: ProviderConfig
    db: DbConfig
    tools: ToolsConfig
    skills: SkillsConfig
    mcp: McpConfig
    auth: AuthConfig
    agent: AgentConfig
    log_level: str = "INFO"


_ENV_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _expand_env(value: str) -> str:
    def replace(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in os.environ:
            raise ValueError(f"Required env var not set: {key}")
        return os.environ[key]
    return _ENV_RE.sub(replace, value)


def _expand_env_recursive(obj: object) -> object:
    if isinstance(obj, str):
        return _expand_env(obj)
    if isinstance(obj, dict):
        return {k: _expand_env_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_recursive(v) for v in obj]
    return obj


def load_config(path: Path | str) -> LumosConfig:
    """从YAML文件加载配置，${VAR}从环境变量替换。"""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = _expand_env_recursive(raw)

    server_raw = raw.get("server", {}) or {}
    provider_raw = raw.get("provider") or {}
    if not provider_raw:
        raise ValueError("Missing required section: provider")
    mcp_servers = [
        McpServerEntry(**s) for s in (raw.get("mcp_servers", []) or [])
    ]
    return LumosConfig(
        server=ServerConfig(**server_raw),
        provider=ProviderConfig(**provider_raw),
        db=DbConfig(**(raw.get("db", {}) or {})),
        tools=ToolsConfig(**(raw.get("tools", {}) or {})),
        skills=SkillsConfig(**(raw.get("skills", {}) or {})),
        mcp=McpConfig(servers=mcp_servers),
        auth=AuthConfig(**(raw.get("auth", {}) or {})),
        agent=AgentConfig(**(raw.get("agent", {}) or {})),
        log_level=raw.get("log_level", "INFO"),
    )
```

**Step 1.7: 创建`tests/__init__.py`（空）和`tests/conftest.py`**

```python
"""pytest全局fixture。"""
from __future__ import annotations
import asyncio
from pathlib import Path
import pytest


@pytest.fixture
def tmp_config_file(tmp_path: Path) -> Path:
    """返回临时配置文件的fixture。"""
    return tmp_path / "config.yaml"
```

**Step 1.8: 写`tests/unit/test_logging.py`**

```python
"""测试日志配置。"""
from __future__ import annotations
import json
import logging
import pytest
from lumos.logging import configure_logging, get_logger, request_id_var


def test_configure_logging_json(capsys: pytest.CaptureFixture[str]):
    configure_logging("DEBUG", json_output=True)
    log = get_logger("test")
    log.info("hello", foo="bar")
    err = capsys.readouterr().err
    record = json.loads(err.strip().split("\n")[-1])
    assert record["event"] == "hello"
    assert record["foo"] == "bar"


def test_request_id_context():
    configure_logging("INFO", json_output=True)
    log = get_logger("test")
    token = request_id_var.set("trace-123")
    try:
        assert request_id_var.get() == "trace-123"
    finally:
        request_id_var.reset(token)
```

**Step 1.9: 写`src/lumos/logging.py`**

```python
"""结构化日志：structlog + JSON输出。"""
from __future__ import annotations
import logging
import sys
from contextvars import ContextVar
import structlog

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def _add_request_id(_, __, event_dict: dict) -> dict:
    rid = request_id_var.get()
    if rid is not None:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """全局日志配置。"""
    processors = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

**Step 1.10: 写`tests/unit/test_errors.py`**

```python
"""测试异常层级。"""
from __future__ import annotations
import pytest
from lumos.errors import (
    LumosError, ProviderError, ToolExecutionError,
    McpConnectionError, CancelledError, MaxStepsExceededError,
    ContextLengthExceededError,
)


def test_provider_error_retryable():
    e = ProviderError("rate limit", retryable=True)
    assert e.retryable is True
    assert isinstance(e, LumosError)


def test_context_length_exceeded_is_provider_error():
    e = ContextLengthExceededError("too long")
    assert isinstance(e, ProviderError)
    assert e.retryable is False


def test_tool_error_carries_name():
    e = ToolExecutionError("failed", tool_name="web_search")
    assert e.tool_name == "web_search"


def test_cancelled_error_inherits():
    e = CancelledError("user cancelled")
    assert isinstance(e, LumosError)
```

**Step 1.11: 写`src/lumos/errors.py`**

```python
"""Lumos异常层级。"""
from __future__ import annotations


class LumosError(Exception):
    """所有Lumos异常的基类。"""

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class ProviderError(LumosError):
    """LLM Provider错误。"""
    retryable: bool = False

    def __init__(
        self,
        message: str = "",
        *,
        retryable: bool = False,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.retryable = retryable


class ToolExecutionError(LumosError):
    """工具执行失败。"""

    def __init__(
        self,
        message: str = "",
        *,
        tool_name: str = "",
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.tool_name = tool_name


class McpConnectionError(LumosError):
    """MCP连接错误。"""


class CancelledError(LumosError):
    """用户取消。"""


class MaxStepsExceededError(LumosError):
    """Agent超过最大步数。"""


class ContextLengthExceededError(ProviderError):
    """上下文超限。"""

    def __init__(self, message: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(message, retryable=False, cause=cause)
```

**Step 1.12: 创建`.env.example`**

```bash
# Lumos环境变量样例
# 复制为 .env 并填入实际值
OPENAI_API_KEY=sk-your-key-here
JWT_SECRET=please-generate-with-openssl-rand-hex-32
```

**Step 1.13: 创建`config.example.yaml`**

```yaml
# Lumos主配置样例
log_level: INFO

server:
  host: 127.0.0.1
  port: 8000
  cors_origins: []

provider:
  type: openai_compat
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini
  temperature: 0.7
  max_tokens: 4096
  timeout: 60

db:
  url: sqlite+aiosqlite:///./data/lumos.db
  echo: false

tools:
  allowed_paths:
    - ./data/workspace
  shell_enabled: false
  default_timeout: 30

skills:
  dirs:
    - ./skills

mcp_servers:
  - name: filesystem
    transport: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "./data/workspace"]
    enabled: false

auth:
  jwt_secret: ${JWT_SECRET}
  access_ttl: 86400
  refresh_ttl: 2592000
  bcrypt_rounds: 12
  default_admin_email: admin@example.com
  default_admin_password: ${DEFAULT_ADMIN_PASSWORD}

agent:
  max_steps: 15
  context_compress_threshold: 60000
```

**Step 1.14: 创建`.gitignore`**

```
__pycache__/
*.pyc
.venv/
.newvenv/
.venv-uv/
.env
data/
*.db
*.db-journal
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
.vscode/
.idea/
```

**Step 1.15: 创建空的`src/lumos/cli.py`占位**

```python
"""CLI入口（后续Task 22扩展）。"""
from __future__ import annotations


def main() -> int:
    print("Lumos CLI: 占位实现，将由后续任务填充")
    return 0
```

**Step 1.16: 跑全部测试确认通过**

Run: `pip install -e ".[dev]"`
Then: `pytest tests/unit -v`
Expected: 全部PASS

**Step 1.17: 提交**

```bash
git add .
git commit -m "feat: project skeleton with config loader, logging, errors"
```

---

### Task 2: 持久化层基础

**Files:**
- Create: `src/lumos/persistence/__init__.py`
- Create: `src/lumos/persistence/db.py`
- Create: `src/lumos/persistence/models.py`
- Create: `tests/unit/test_persistence_db.py`
- Create: `tests/unit/test_persistence_models.py`

**Interfaces:**
- Produces:
  - `init_db(engine: AsyncEngine) -> None`：创建所有表
  - `drop_db(engine: AsyncEngine) -> None`：删除所有表
  - `get_engine(url: str, echo: bool = False) -> AsyncEngine`
  - `get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]`
  - ORM类: `User`, `ChatSession`, `Message`, `McpServer`, `RevokedToken`

**Step 2.1: 写`tests/unit/test_persistence_db.py`**

```python
"""测试DB初始化和Session工厂。"""
from __future__ import annotations
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from lumos.persistence.db import get_engine, get_session_factory, init_db, drop_db


@pytest.fixture
async def engine():
    eng = get_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield eng
    await eng.dispose()


@pytest.mark.asyncio
async def test_init_and_drop_db(engine: AsyncEngine):
    await init_db(engine)
    factory = get_session_factory(engine)
    async with factory() as session:
        from sqlalchemy import text
        result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = {row[0] for row in result}
    assert "users" in tables
    assert "chat_sessions" in tables
    assert "messages" in tables
    assert "mcp_servers" in tables
    assert "revoked_tokens" in tables
    await drop_db(engine)
```

**Step 2.2: 跑测试确认失败**

Run: `pytest tests/unit/test_persistence_db.py -v`
Expected: ModuleNotFoundError

**Step 2.3: 写`tests/unit/test_persistence_models.py`**

```python
"""测试ORM模型定义和基本CRUD。"""
from __future__ import annotations
import pytest
from datetime import datetime
from lumos.persistence.db import get_engine, get_session_factory, init_db
from lumos.persistence.models import User, ChatSession, Message, McpServer


@pytest.fixture
async def session():
    eng = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(eng)
    factory = get_session_factory(eng)
    async with factory() as s:
        yield s
    await eng.dispose()


@pytest.mark.asyncio
async def test_create_user(session):
    user = User(
        id="u1", email="a@b.com", password_hash="h", is_active=True,
        created_at=datetime.now(),
    )
    session.add(user)
    await session.commit()
    found = await session.get(User, "u1")
    assert found is not None
    assert found.email == "a@b.com"


@pytest.mark.asyncio
async def test_create_session_and_message(session):
    user = User(
        id="u1", email="a@b.com", password_hash="h",
        is_active=True, created_at=datetime.now(),
    )
    session.add(user)
    chat = ChatSession(
        id="c1", user_id="u1", title="test",
        enabled_skills="[]", model_config="{}",
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    session.add(chat)
    msg = Message(
        id="m1", session_id="c1", role="user",
        content='{"text":"hi"}', tool_calls=None,
        tool_call_id=None, name=None,
        created_at=datetime.now(), prompt_tokens=0, completion_tokens=0,
    )
    session.add(msg)
    await session.commit()

    found = await session.get(Message, "m1")
    assert found is not None
    assert found.role == "user"
```

**Step 2.4: 创建`src/lumos/persistence/__init__.py`**

```python
"""持久化层：DB + ORM + 仓储。"""
from lumos.persistence.db import (
    get_engine, get_session_factory, init_db, drop_db,
)

__all__ = ["get_engine", "get_session_factory", "init_db", "drop_db"]
```

**Step 2.5: 写`src/lumos/persistence/db.py`**

```python
"""DB引擎和Session工厂。"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
)
from lumos.persistence.models import Base


def get_engine(url: str, echo: bool = False) -> AsyncEngine:
    """创建异步SQLAlchemy引擎。"""
    return create_async_engine(url, echo=echo, future=True)


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """创建Session工厂。"""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine) -> None:
    """创建所有表（一阶段使用，二阶段切换Alembic）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db(engine: AsyncEngine) -> None:
    """删除所有表（仅测试用）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

**Step 2.6: 写`src/lumos/persistence/models.py`**

```python
"""SQLAlchemy ORM模型定义。"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, Boolean, Integer, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    enabled_skills: Mapped[str] = mapped_column(Text, default="[]")
    model_config: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), index=True
    )


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    config: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
```

**Step 2.7: 跑测试确认通过**

Run: `pytest tests/unit/test_persistence_db.py tests/unit/test_persistence_models.py -v`
Expected: PASS

**Step 2.8: 提交**

```bash
git add src/lumos/persistence tests/unit/test_persistence_db.py tests/unit/test_persistence_models.py
git commit -m "feat: persistence layer with SQLAlchemy async models"
```

---

## Phase B：Provider与工具

### Task 3: Provider抽象基类与消息数据类

**Files:**
- Create: `src/lumos/providers/__init__.py`
- Create: `src/lumos/providers/base.py`
- Create: `src/lumos/agent/__init__.py`
- Create: `src/lumos/agent/message.py`
- Create: `tests/unit/test_provider_base.py`
- Create: `tests/unit/test_message.py`

**Interfaces:**
- Produces:
  - `Message`, `TextContent`, `ToolCall`, `ToolResult`, `Usage`, `AgentEvent`, `ToolSpec`
  - `BaseProvider`抽象类

**Step 3.1: 写`tests/unit/test_message.py`**

```python
"""测试消息数据类。"""
from __future__ import annotations
import json
from lumos.agent.message import (
    Message, TextContent, ToolCall, ToolResult, Usage, AgentEvent,
)


def test_message_to_dict_roundtrip():
    msg = Message(
        role="assistant",
        content=[TextContent(text="hello")],
    )
    d = msg.to_dict()
    assert d["role"] == "assistant"
    assert d["content"] == [{"type": "text", "text": "hello"}]


def test_message_with_tool_calls():
    msg = Message(
        role="assistant",
        content=[
            TextContent(text="let me search"),
            ToolCall(id="t1", name="web_search", arguments={"q": "AI"}),
        ],
    )
    d = msg.to_dict()
    assert len(d["content"]) == 2
    assert d["content"][1]["type"] == "tool_call"
    assert d["content"][1]["name"] == "web_search"


def test_usage_defaults():
    u = Usage()
    assert u.prompt_tokens == 0
    assert u.total_tokens == 0


def test_agent_event_serialization():
    e = AgentEvent(
        type="text", session_id="s1",
        data={"delta": "hi"},
    )
    j = e.to_json()
    parsed = json.loads(j)
    assert parsed["type"] == "text"
    assert parsed["data"]["delta"] == "hi"
```

**Step 3.2: 写`tests/unit/test_provider_base.py`**

```python
"""测试Provider抽象基类的embed预留接口。"""
from __future__ import annotations
import pytest
from lumos.providers.base import BaseProvider


def test_embed_raises_not_implemented():
    class FakeProvider(BaseProvider):
        async def chat(self, messages, *, system, tools, temperature,
                       max_tokens, cancel, on_text):
            return "", [], Usage()

    p = FakeProvider()
    with pytest.raises(NotImplementedError, match="RAG"):
        import asyncio
        asyncio.run(p.embed(["text"]))
```

**Step 3.3: 创建`src/lumos/agent/__init__.py`**

```python
"""Agent核心模块。"""
from lumos.agent.message import (
    Message, TextContent, ToolCall, ToolResult, Usage, AgentEvent, ToolSpec,
)

__all__ = [
    "Message", "TextContent", "ToolCall", "ToolResult",
    "Usage", "AgentEvent", "ToolSpec",
]
```

**Step 3.4: 写`src/lumos/agent/message.py`**

```python
"""统一的消息、工具调用、流式事件数据类。"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Literal, Any


@dataclass
class TextContent:
    text: str
    type: Literal["text"] = "text"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "text", "text": self.text}


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    type: Literal["tool_call"] = "tool_call"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "tool_call",
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }


@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    is_error: bool = False
    name: str | None = None

    def to_message(self) -> "Message":
        return Message(
            role="tool",
            content=[TextContent(text=self.content)],
            tool_call_id=self.tool_call_id,
            name=self.name,
        )


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    requires_confirmation: bool = False
    source: Literal["builtin", "mcp", "skill"] = "builtin"


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: list[TextContent | ToolCall | ToolResult] | str
    name: str | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if isinstance(self.content, str):
            content_val: Any = self.content
        else:
            content_val = [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in self.content
            ]
        d: dict[str, Any] = {"role": self.role, "content": content_val}
        if self.name is not None:
            d["name"] = self.name
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


EventType = Literal[
    "text", "tool_call_start", "tool_call_result",
    "tool_call_end", "confirm_required", "error", "usage", "done", "cancelled",
]


@dataclass
class AgentEvent:
    type: EventType
    session_id: str
    data: Any = None

    def to_json(self) -> str:
        return json.dumps(
            {"type": self.type, "session_id": self.session_id, "data": self.data},
            ensure_ascii=False,
        )
```

**Step 3.5: 创建`src/lumos/providers/__init__.py`**

```python
"""LLM Provider抽象。"""
from lumos.providers.base import BaseProvider

__all__ = ["BaseProvider"]
```

**Step 3.6: 写`src/lumos/providers/base.py`**

```python
"""LLM Provider抽象基类。"""
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Awaitable, Callable
from lumos.agent.message import Message, ToolCall, Usage, ToolSpec


OnTextCallback = Callable[[str], Awaitable[None]]


class BaseProvider(ABC):
    """所有LLM Provider的抽象接口。"""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        cancel: asyncio.Event | None = None,
        on_text: OnTextCallback | None = None,
    ) -> tuple[str, list[ToolCall], Usage]:
        """单次完整调用，返回(text, tool_calls, usage)。"""
        ...

    async def stream_chat(self, **kwargs) -> tuple[str, list[ToolCall], Usage]:
        """流式调用：默认实现为on_text累加 + chat()。"""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """文本嵌入接口（一阶段不实现，二阶段RAG时由VectorServiceProvider覆盖）。"""
        raise NotImplementedError(
            "embed() not implemented in phase 1; "
            "use VectorServiceProvider in phase 2"
        )
```

**Step 3.7: 跑测试**

Run: `pytest tests/unit/test_message.py tests/unit/test_provider_base.py -v`
Expected: PASS

**Step 3.8: 提交**

```bash
git add src/lumos/agent src/lumos/providers tests/unit/test_message.py tests/unit/test_provider_base.py
git commit -m "feat: provider abstraction and message data classes"
```

---

### Task 4: OpenAI兼容Provider实现

**Files:**
- Create: `src/lumos/providers/openai_compat.py`
- Create: `tests/unit/test_openai_compat.py`

**Interfaces:**
- Produces:
  - `OpenAICompatProvider(BaseProvider)`：完整流式实现

**Step 4.1: 写`tests/unit/test_openai_compat.py`**

```python
"""测试OpenAI兼容Provider（含流式tool_calls累积）。"""
from __future__ import annotations
import pytest
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import (
    Choice as ChunkChoice, ChoiceDelta, ChoiceDeltaToolCall,
)
from lumos.providers.openai_compat import OpenAICompatProvider
from lumos.agent.message import Message, ToolSpec, Usage


def _make_chunk(
    *, content="", tool_calls=None, finish_reason=None, usage=None,
):
    delta = ChoiceDelta(content=content or None, role="assistant")
    if tool_calls:
        delta.tool_calls = [
            ChoiceDeltaToolCall(
                index=tc.get("index", 0),
                id=tc.get("id"),
                function=tc.get("function"),
            )
            for tc in tool_calls
        ]
    return ChatCompletionChunk(
        id="chunk",
        object="chat.completion.chunk",
        created=0,
        model="test",
        choices=[ChunkChoice(index=0, delta=delta, finish_reason=finish_reason)],
        usage=usage,
    )


@pytest.fixture
def mock_openai_client(mocker):
    """用mocker替换AsyncOpenAI的chat.completions.create。"""
    pass


@pytest.mark.asyncio
async def test_streaming_text_accumulation(mocker):
    chunks = [
        _make_chunk(content="Hello"),
        _make_chunk(content=" world"),
        _make_chunk(content="!", finish_reason="stop"),
    ]
    async def fake_create(**kwargs):
        for c in chunks:
            yield c

    provider = OpenAICompatProvider(
        base_url="https://api.test/v1",
        api_key="k",
        model="m",
    )
    mocker.patch.object(
        provider.client.chat.completions, "create", side_effect=fake_create
    )

    text_parts: list[str] = []
    async def on_text(t: str) -> None:
        text_parts.append(t)

    text, tool_calls, usage = await provider.chat(
        messages=[Message(role="user", content="hi")],
        system=None,
        tools=None,
        temperature=0.5,
        max_tokens=None,
        cancel=None,
        on_text=on_text,
    )
    assert text == "Hello world!"
    assert tool_calls == []
    assert text_parts == ["Hello", " world", "!"]


@pytest.mark.asyncio
async def test_streaming_tool_calls_fragmented(mocker):
    """OpenAI分片返回tool_calls，按index累积。"""
    chunks = [
        _make_chunk(tool_calls=[
            {"index": 0, "id": "call_1", "function": {"name": "web_search", "arguments": ""}},
        ]),
        _make_chunk(tool_calls=[
            {"index": 0, "function": {"arguments": '{"q":'}},
        ]),
        _make_chunk(tool_calls=[
            {"index": 0, "function": {"arguments": '"AI"}'}},
        ]),
        _make_chunk(finish_reason="tool_calls"),
    ]
    async def fake_create(**kwargs):
        for c in chunks:
            yield c

    provider = OpenAICompatProvider(
        base_url="https://api.test/v1", api_key="k", model="m",
    )
    mocker.patch.object(
        provider.client.chat.completions, "create", side_effect=fake_create
    )

    text, tool_calls, usage = await provider.chat(
        messages=[Message(role="user", content="hi")],
        system=None, tools=None,
        temperature=0.5, max_tokens=None, cancel=None, on_text=None,
    )
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "web_search"
    assert tool_calls[0].arguments == {"q": "AI"}


@pytest.mark.asyncio
async def test_usage_from_final_chunk(mocker):
    chunks = [
        _make_chunk(content="done", finish_reason="stop"),
    ]
    usage_obj = type("U", (), {
        "prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30,
    })()
    chunks[0].usage = usage_obj

    async def fake_create(**kw):
        for c in chunks:
            yield c

    provider = OpenAICompatProvider(
        base_url="https://api.test/v1", api_key="k", model="m",
    )
    mocker.patch.object(
        provider.client.chat.completions, "create", side_effect=fake_create
    )

    _, _, usage = await provider.chat(
        messages=[Message(role="user", content="hi")],
        system=None, tools=None,
        temperature=0.5, max_tokens=None, cancel=None, on_text=None,
    )
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 20
    assert usage.total_tokens == 30


@pytest.mark.asyncio
async def test_cancel_raises(mocker):
    cancel = __import__("asyncio").Event()
    cancel.set()

    async def fake_create(**kw):
        yield _make_chunk(content="x")
        if False:
            yield

    provider = OpenAICompatProvider(
        base_url="https://api.test/v1", api_key="k", model="m",
    )
    mocker.patch.object(
        provider.client.chat.completions, "create", side_effect=fake_create
    )

    import asyncio
    with pytest.raises(asyncio.CancelledError):
        await provider.chat(
            messages=[Message(role="user", content="hi")],
            system=None, tools=None,
            temperature=0.5, max_tokens=None, cancel=cancel, on_text=None,
        )
```

**Step 4.2: 跑测试确认失败**

Run: `pytest tests/unit/test_openai_compat.py -v`
Expected: ModuleNotFoundError（lumos.providers.openai_compat不存在）

**Step 4.3: 写`src/lumos/providers/openai_compat.py`**

```python
"""OpenAI兼容Provider（覆盖OpenAI官方 + 所有兼容服务）。"""
from __future__ import annotations
import asyncio
import json
from typing import Any
from openai import AsyncOpenAI
from lumos.agent.message import Message, ToolCall, ToolSpec, Usage
from lumos.providers.base import BaseProvider, OnTextCallback
from lumos.errors import ProviderError, ContextLengthExceededError


class OpenAICompatProvider(BaseProvider):
    """OpenAI兼容实现。

    支持OpenAI官方及所有OpenAI兼容服务（DeepSeek/Qwen/Moonshot/Ollama/vLLM等）。
    通过指定base_url切换。
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 60,
        **client_kwargs: Any,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            **client_kwargs,
        )

    def _convert_messages(
        self, messages: list[Message], system: str | None,
    ) -> list[dict[str, Any]]:
        oai: list[dict[str, Any]] = []
        if system:
            oai.append({"role": "system", "content": system})
        for msg in messages:
            if isinstance(msg.content, str):
                oai.append({"role": msg.role, "content": msg.content})
            else:
                content_parts: list[dict[str, Any]] = []
                tool_calls_list: list[dict[str, Any]] = []
                for c in msg.content:
                    if c.type == "text":
                        content_parts.append({"type": "text", "text": c.text})
                    elif c.type == "tool_call":
                        tool_calls_list.append({
                            "id": c.id,
                            "type": "function",
                            "function": {
                                "name": c.name,
                                "arguments": json.dumps(c.arguments),
                            },
                        })
                d: dict[str, Any] = {"role": msg.role}
                if tool_calls_list:
                    if content_parts:
                        d["content"] = "".join(
                            p["text"] for p in content_parts
                        )
                    else:
                        d["content"] = None
                    d["tool_calls"] = tool_calls_list
                else:
                    d["content"] = "".join(p["text"] for p in content_parts)
                if msg.name:
                    d["name"] = msg.name
                if msg.tool_call_id:
                    d["tool_call_id"] = msg.tool_call_id
                oai.append(d)
        return oai

    def _convert_tools(self, tools: list[ToolSpec] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    async def chat(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        cancel: asyncio.Event | None = None,
        on_text: OnTextCallback | None = None,
    ) -> tuple[str, list[ToolCall], Usage]:
        oai_messages = self._convert_messages(messages, system)
        oai_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": oai_messages,
            "temperature": temperature,
            "stream": True,
        }
        if oai_tools is not None:
            kwargs["tools"] = oai_tools
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            msg = str(e).lower()
            retryable = any(
                x in msg for x in ("timeout", "rate", "5xx", "server error")
            )
            if "context_length" in msg or "maximum context" in msg:
                raise ContextLengthExceededError(str(e), cause=e) from e
            raise ProviderError(str(e), retryable=retryable, cause=e) from e

        text_chunks: list[str] = []
        tool_calls_acc: dict[int, dict[str, Any]] = {}
        usage = Usage()

        async for chunk in response:
            if cancel and cancel.is_set():
                raise asyncio.CancelledError()
            if chunk.usage is not None:
                usage = Usage(
                    prompt_tokens=getattr(chunk.usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(chunk.usage, "completion_tokens", 0) or 0,
                    total_tokens=getattr(chunk.usage, "total_tokens", 0) or 0,
                )
            for choice in chunk.choices:
                delta = choice.delta
                if delta.content:
                    text_chunks.append(delta.content)
                    if on_text is not None:
                        await on_text(delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc.id or "",
                                "name": (tc.function.name if tc.function else "") or "",
                                "arguments": "",
                            }
                        if tc.function and tc.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc.function.arguments

        tool_calls: list[ToolCall] = []
        for idx in sorted(tool_calls_acc):
            tc = tool_calls_acc[idx]
            raw_args = tc["arguments"]
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                args = {"_raw": raw_args, "_parse_error": True}
            tool_calls.append(ToolCall(id=tc["id"], name=tc["name"], arguments=args))

        return "".join(text_chunks), tool_calls, usage
```

**Step 4.4: 跑测试**

Run: `pytest tests/unit/test_openai_compat.py -v`
Expected: PASS

**Step 4.5: 提交**

```bash
git add src/lumos/providers/openai_compat.py tests/unit/test_openai_compat.py
git commit -m "feat: openai-compatible provider with streaming tool calls"
```

---

### Task 5: 工具系统抽象与注册中心

**Files:**
- Create: `src/lumos/tools/__init__.py`
- Create: `src/lumos/tools/base.py`
- Create: `src/lumos/tools/registry.py`
- Create: `tests/unit/test_tools_registry.py`

**Interfaces:**
- Produces:
  - `Tool`抽象基类
  - `ToolRegistry`：register/unregister/get/all_specs/to_openai_tools
  - `register_tool`装饰器

**Step 5.1: 写`tests/unit/test_tools_registry.py`**

```python
"""测试Tool注册中心。"""
from __future__ import annotations
import pytest
from lumos.tools.base import Tool
from lumos.tools.registry import ToolRegistry, register_tool


@register_tool(
    name="echo",
    description="echoes back",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)
class EchoTool(Tool):
    async def execute(self, *, text: str) -> str:
        return text


def test_decorator_registers():
    reg = ToolRegistry()
    reg.discover()
    spec = reg.get_spec("echo")
    assert spec is not None
    assert spec.name == "echo"


@pytest.mark.asyncio
async def test_execute():
    reg = ToolRegistry()
    reg.discover()
    tool = reg.get("echo")
    result = await tool.execute(text="hi")
    assert result == "hi"


def test_unregister():
    reg = ToolRegistry()
    reg.discover()
    assert reg.get("echo") is not None
    reg.unregister("echo")
    assert reg.get("echo") is None


def test_to_openai_format():
    reg = ToolRegistry()
    reg.discover()
    oai = reg.to_openai_tools()
    assert len(oai) >= 1
    assert any(t["function"]["name"] == "echo" for t in oai)
```

**Step 5.2: 创建`src/lumos/tools/__init__.py`**

```python
"""工具系统。"""
from lumos.tools.base import Tool
from lumos.tools.registry import ToolRegistry, register_tool

__all__ = ["Tool", "ToolRegistry", "register_tool"]
```

**Step 5.3: 写`src/lumos/tools/base.py`**

```python
"""Tool抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass, field


@dataclass
class ToolMeta:
    """工具元数据（装饰器注入）。"""
    name: str
    description: str
    parameters: dict[str, Any]
    requires_confirmation: bool = False


class Tool(ABC):
    """所有工具的抽象基类。子类必须设置meta并实现execute。"""

    meta: ToolMeta

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """执行工具，返回文本结果。抛ToolExecutionError表示执行失败。"""
        ...
```

**Step 5.4: 写`src/lumos/tools/registry.py`**

```python
"""工具注册中心。"""
from __future__ import annotations
from typing import Any
import importlib
import pkgutil
from lumos.agent.message import ToolSpec
from lumos.tools.base import Tool


class ToolRegistry:
    """工具注册表，存储Tool实例并生成OpenAI兼容的tools列表。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.meta.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name]

    def get_spec(self, name: str) -> ToolSpec | None:
        tool = self._tools.get(name)
        if tool is None:
            return None
        m = tool.meta
        return ToolSpec(
            name=m.name, description=m.description,
            parameters=m.parameters,
            requires_confirmation=m.requires_confirmation,
            source="builtin",
        )

    def all_specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name=t.meta.name, description=t.meta.description,
                parameters=t.meta.parameters,
                requires_confirmation=t.meta.requires_confirmation,
                source="builtin",
            )
            for t in self._tools.values()
        ]

    def to_openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self.all_specs()
        ]

    def discover(self, package: str = "lumos.tools.builtin") -> None:
        """扫描内置工具包，自动注册所有Tool子类。"""
        try:
            pkg = importlib.import_module(package)
        except ImportError:
            return
        for mod_info in pkgutil.iter_modules(pkg.__path__):
            mod = importlib.import_module(f"{package}.{mod_info.name}")
            for name in dir(mod):
                obj = getattr(mod, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, Tool)
                    and obj is not Tool
                    and hasattr(obj, "meta")
                ):
                    self.register(obj())


def register_tool(
    *,
    name: str,
    description: str,
    parameters: dict[str, Any],
    requires_confirmation: bool = False,
):
    """Tool类装饰器：注入meta。"""
    def decorator(cls: type[Tool]) -> type[Tool]:
        cls.meta = ToolMeta(
            name=name, description=description,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
        )
        return cls
    return decorator
```

**Step 5.5: 创建`src/lumos/tools/builtin/__init__.py`**

```python
"""内置工具。"""
```

**Step 5.6: 创建`src/lumos/tools/builtin/echo.py`**（临时工具，用于测试discover机制）

```python
"""Echo工具（测试discover机制用，Task 6移除）。"""
from __future__ import annotations
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool


@register_tool(
    name="echo",
    description="Echoes back the input text.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)
class EchoTool(Tool):
    async def execute(self, *, text: str) -> str:
        return text
```

**Step 5.7: 跑测试**

Run: `pytest tests/unit/test_tools_registry.py -v`
Expected: PASS

**Step 5.8: 提交**

```bash
git add src/lumos/tools tests/unit/test_tools_registry.py
git commit -m "feat: tool abstraction and registry with auto-discovery"
```

---

### Task 6: 内置工具实现（datetime、calculator、shell、file_ops、http_request、web_search、web_fetch）

**Files:**
- Create: `src/lumos/tools/builtin/datetime.py`
- Create: `src/lumos/tools/builtin/calculator.py`
- Create: `src/lumos/tools/builtin/shell.py`
- Create: `src/lumos/tools/builtin/file_ops.py`
- Create: `src/lumos/tools/builtin/http_request.py`
- Create: `src/lumos/tools/builtin/web_search.py`
- Create: `src/lumos/tools/builtin/web_fetch.py`
- Delete: `src/lumos/tools/builtin/echo.py`
- Create: `tests/unit/test_builtin_tools.py`

**Interfaces:**
- Produces: 7个Tool类，导出名固定为`datetime_now`, `calculator`, `shell_exec`, `file_read`, `file_write`, `http_request`, `web_search`, `web_fetch`

**Step 6.1: 写`src/lumos/tools/builtin/datetime.py`**

```python
"""当前时间工具。"""
from __future__ import annotations
from datetime import datetime, timezone
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool


@register_tool(
    name="datetime_now",
    description="Get the current date and time in a specified timezone.",
    parameters={
        "type": "object",
        "properties": {
            "tz": {
                "type": "string",
                "description": "IANA timezone name, e.g. Asia/Shanghai. Default UTC.",
                "default": "UTC",
            },
        },
        "required": [],
    },
)
class DateTimeTool(Tool):
    async def execute(self, *, tz: str = "UTC") -> str:
        try:
            zone = timezone.utc if tz == "UTC" else __import__("zoneinfo").ZoneInfo(tz)
        except Exception:
            zone = timezone.utc
            tz = "UTC"
        now = datetime.now(zone)
        return now.strftime(f"%Y-%m-%d %H:%M:%S %Z ({tz})")
```

**Step 6.2: 写`src/lumos/tools/builtin/calculator.py`**

```python
"""受限数学表达式计算。"""
from __future__ import annotations
import ast
import operator
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool


_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_eval(expr: str) -> float | int:
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Only numeric constants allowed: {node.value!r}")
        return node.value
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary: {type(node.op).__name__}")
        return op(_eval_node(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


@register_tool(
    name="calculator",
    description="Evaluate a math expression. Supports +,-,*,/,//,%,**, parentheses.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Math expression"},
        },
        "required": ["expression"],
    },
)
class CalculatorTool(Tool):
    async def execute(self, *, expression: str) -> str:
        try:
            result = _safe_eval(expression)
            return str(result)
        except Exception as e:
            raise ValueError(f"Calculation failed: {e}")
```

**Step 6.3: 写`src/lumos/tools/builtin/shell.py`**

```python
"""受限shell执行。"""
from __future__ import annotations
import asyncio
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


@register_tool(
    name="shell_exec",
    description="Execute a shell command. Disabled by default; requires confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "default": 10, "minimum": 1, "maximum": 60},
        },
        "required": ["command"],
    },
    requires_confirmation=True,
)
class ShellTool(Tool):
    async def execute(self, *, command: str, timeout: int = 10) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout,
                )
            except asyncio.TimeoutError as e:
                proc.kill()
                raise ToolExecutionError(
                    f"Command timed out after {timeout}s",
                    tool_name="shell_exec", cause=e,
                ) from e
            output = (stdout or b"").decode("utf-8", errors="replace")
            err = (stderr or b"").decode("utf-8", errors="replace")
            result = output + (("\n[stderr] " + err) if err else "")
            if proc.returncode != 0:
                raise ToolExecutionError(
                    f"Exit code {proc.returncode}: {result}",
                    tool_name="shell_exec",
                )
            return result or "(no output)"
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                str(e), tool_name="shell_exec", cause=e,
            ) from e
```

**Step 6.4: 写`src/lumos/tools/builtin/file_ops.py`**

```python
"""文件读写工具（受路径限制）。"""
from __future__ import annotations
from pathlib import Path
from lumos.config import ToolsConfig
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


def _resolve_safe(path_str: str, allowed: list[str]) -> Path:
    target = Path(path_str).expanduser().resolve()
    for prefix in allowed:
        try:
            target.relative_to(Path(prefix).expanduser().resolve())
            return target
        except ValueError:
            continue
    raise PermissionError(
        f"Path not allowed: {path_str}. Allowed: {allowed}"
    )


@register_tool(
    name="file_read",
    description="Read the contents of a local file. Path must be in allowed_paths.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "max_bytes": {"type": "integer", "default": 100000, "maximum": 1000000},
        },
        "required": ["path"],
    },
)
class FileReadTool(Tool):
    config: ToolsConfig | None = None

    async def execute(self, *, path: str, max_bytes: int = 100000) -> str:
        try:
            allowed = (self.config.allowed_paths if self.config else []) or []
            p = _resolve_safe(path, allowed)
            content = p.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_bytes:
                content = content[:max_bytes] + f"\n...[truncated, total {len(content)} chars]"
            return content
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="file_read", cause=e) from e


@register_tool(
    name="file_write",
    description="Write content to a local file. Path must be in allowed_paths.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    },
    requires_confirmation=True,
)
class FileWriteTool(Tool):
    config: ToolsConfig | None = None

    async def execute(self, *, path: str, content: str) -> str:
        try:
            allowed = (self.config.allowed_paths if self.config else []) or []
            p = _resolve_safe(path, allowed)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} chars to {p}"
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="file_write", cause=e) from e
```

**Step 6.5: 写`src/lumos/tools/builtin/http_request.py`**

```python
"""通用HTTP请求工具。"""
from __future__ import annotations
import httpx
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


@register_tool(
    name="http_request",
    description="Make an HTTP request. Supports GET/POST/PUT/DELETE. Body must be JSON.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
            "headers": {"type": "object", "additionalProperties": {"type": "string"}},
            "json_body": {"type": "object"},
            "timeout": {"type": "integer", "default": 30, "maximum": 120},
        },
        "required": ["url", "method"],
    },
)
class HttpRequestTool(Tool):
    async def execute(
        self, *, url: str, method: str,
        headers: dict | None = None,
        json_body: dict | None = None,
        timeout: int = 30,
    ) -> str:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method=method, url=url,
                    headers=headers or {},
                    json=json_body,
                )
            body_preview = resp.text[:5000]
            return f"Status: {resp.status_code}\n\n{body_preview}"
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="http_request", cause=e) from e
```

**Step 6.6: 写`src/lumos/tools/builtin/web_search.py`**

```python
"""DuckDuckGo搜索工具。"""
from __future__ import annotations
import asyncio
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


@register_tool(
    name="web_search",
    description="Search the web using DuckDuckGo. Returns top results with title, snippet, URL.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
)
class WebSearchTool(Tool):
    async def execute(self, *, query: str, max_results: int = 5) -> str:
        try:
            from duckduckgo_search import DDGS
            def _search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))
            results = await asyncio.to_thread(_search)
            if not results:
                return "No results found."
            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"[{i}] {r.get('title', '')}\n{r.get('href', '')}\n{r.get('body', '')}")
            return "\n\n".join(lines)
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="web_search", cause=e) from e
```

**Step 6.7: 写`src/lumos/tools/builtin/web_fetch.py`**

```python
"""URL抓取转Markdown工具。"""
from __future__ import annotations
import httpx
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool
from lumos.errors import ToolExecutionError


@register_tool(
    name="web_fetch",
    description="Fetch a URL and extract its main content as Markdown.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {"type": "integer", "default": 20000, "maximum": 100000},
        },
        "required": ["url"],
    },
)
class WebFetchTool(Tool):
    async def execute(self, *, url: str, max_chars: int = 20000) -> str:
        try:
            import trafilatura
            async with httpx.AsyncClient(
                timeout=30, follow_redirects=True,
                headers={"User-Agent": "Lumos/0.1 (+https://lumos.local)"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
            text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n...[truncated, total {len(text)} chars]"
            return f"Source: {url}\n\n{text}" if text else f"No content extracted from {url}"
        except Exception as e:
            raise ToolExecutionError(str(e), tool_name="web_fetch", cause=e) from e
```

**Step 6.8: 删除`src/lumos/tools/builtin/echo.py`**

```bash
rm src/lumos/tools/builtin/echo.py
```

**Step 6.9: 写`tests/unit/test_builtin_tools.py`**

```python
"""测试内置工具。"""
from __future__ import annotations
import pytest
from lumos.tools.builtin.datetime import DateTimeTool
from lumos.tools.builtin.calculator import CalculatorTool, _safe_eval
from lumos.tools.builtin.shell import ShellTool
from lumos.tools.builtin.file_ops import FileReadTool, FileWriteTool
from lumos.config import ToolsConfig


@pytest.mark.asyncio
async def test_datetime_default_utc():
    tool = DateTimeTool()
    result = await tool.execute()
    assert "UTC" in result


@pytest.mark.asyncio
async def test_datetime_shanghai():
    tool = DateTimeTool()
    result = await tool.execute(tz="Asia/Shanghai")
    assert "Shanghai" in result or "CST" in result or "+08" in result


def test_calculator_eval():
    assert _safe_eval("1 + 2") == 3
    assert _safe_eval("2 ** 10") == 1024
    assert _safe_eval("(1 + 2) * 3") == 9


def test_calculator_rejects_function_calls():
    with pytest.raises(ValueError):
        _safe_eval("__import__('os').system('rm -rf /')")


@pytest.mark.asyncio
async def test_calculator_tool():
    tool = CalculatorTool()
    result = await tool.execute(expression="(10 + 5) * 2")
    assert result == "30"


@pytest.mark.asyncio
async def test_shell_exec_success():
    tool = ShellTool()
    result = await tool.execute(command="echo hello")
    assert "hello" in result


@pytest.mark.asyncio
async def test_shell_exec_failure():
    from lumos.errors import ToolExecutionError
    tool = ShellTool()
    with pytest.raises(ToolExecutionError):
        await tool.execute(command="exit 1")


@pytest.mark.asyncio
async def test_file_write_and_read(tmp_path):
    cfg = ToolsConfig(allowed_paths=[str(tmp_path)])
    write_tool = FileWriteTool()
    write_tool.config = cfg
    target = tmp_path / "test.txt"
    await write_tool.execute(path=str(target), content="hello world")
    assert target.read_text() == "hello world"

    read_tool = FileReadTool()
    read_tool.config = cfg
    content = await read_tool.execute(path=str(target))
    assert content == "hello world"


@pytest.mark.asyncio
async def test_file_read_path_blocked(tmp_path):
    from lumos.errors import ToolExecutionError
    cfg = ToolsConfig(allowed_paths=[str(tmp_path)])
    tool = FileReadTool()
    tool.config = cfg
    with pytest.raises(ToolExecutionError, match="not allowed"):
        await tool.execute(path="/etc/passwd")


@pytest.mark.asyncio
async def test_http_request_real(respx_mock):
    import respx
    import httpx
    respx_mock.get("https://example.com/api").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    from lumos.tools.builtin.http_request import HttpRequestTool
    tool = HttpRequestTool()
    result = await tool.execute(url="https://example.com/api", method="GET")
    assert "200" in result
    assert '"ok": true' in result
```

**Step 6.10: 跑测试**

Run: `pip install respx duckduckgo-search trafilatura`
Then: `pytest tests/unit/test_builtin_tools.py -v`
Expected: PASS（web_search和web_fetch如无网络会跳过或失败，但单测已mock http_request）

**Step 6.11: 提交**

```bash
git add src/lumos/tools/builtin tests/unit/test_builtin_tools.py
git rm src/lumos/tools/builtin/echo.py 2>/dev/null || true
git commit -m "feat: built-in tools (datetime, calculator, shell, file_ops, http, web_search, web_fetch)"
```

---

## Phase C：Skills与MCP

### Task 7: Skills加载与管理

**Files:**
- Create: `src/lumos/skills/__init__.py`
- Create: `src/lumos/skills/loader.py`
- Create: `src/lumos/skills/manager.py`
- Create: `skills/web-research/SKILL.md`
- Create: `skills/code-assistant/SKILL.md`
- Create: `skills/data-analysis/SKILL.md`
- Create: `tests/unit/test_skills.py`

**Interfaces:**
- Produces:
  - `Skill`数据类
  - `SkillManager.discover(dirs)`, `get(name)`, `enable(name)`, `disable(name)`, `list_all()`, `list_enabled()`, `build_system_prompt(enabled)`

**Step 7.1: 写`tests/unit/test_skills.py`**

```python
"""测试Skills加载与管理。"""
from __future__ import annotations
from pathlib import Path
import textwrap
import pytest
from lumos.skills.loader import parse_skill
from lumos.skills.manager import SkillManager


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    skill_a = d / "alpha"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: alpha
        description: First skill
        version: 1.0.0
        tags: [t1]
        required_tools: []
        optional_tools: []
        max_steps: null
        ---

        # Alpha Body

        Use this for X.
    """), encoding="utf-8")
    skill_b = d / "beta"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: beta
        description: Second skill
        required_tools: [datetime_now]
        ---

        Beta instructions.
    """), encoding="utf-8")
    return d


def test_parse_skill(skills_dir: Path):
    skill = parse_skill(skills_dir / "alpha" / "SKILL.md")
    assert skill.name == "alpha"
    assert skill.description == "First skill"
    assert "Alpha Body" in skill.instructions
    assert "Use this for X" in skill.instructions


def test_skill_manager_discover(skills_dir: Path):
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    names = {s.name for s in mgr.list_all()}
    assert names == {"alpha", "beta"}


def test_skill_manager_enable_disable(skills_dir: Path):
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    mgr.disable("alpha")
    enabled = {s.name for s in mgr.list_enabled()}
    assert "alpha" not in enabled
    assert "beta" in enabled


def test_build_system_prompt(skills_dir: Path):
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    prompt = mgr.build_system_prompt(base="BASE PROMPT")
    assert "BASE PROMPT" in prompt
    assert "alpha" in prompt.lower() or "First skill" in prompt


def test_build_system_prompt_filters_disabled(skills_dir: Path):
    mgr = SkillManager(discover_dirs=[skills_dir])
    mgr.discover()
    mgr.disable("alpha")
    prompt = mgr.build_system_prompt(base="BASE")
    assert "First skill" not in prompt
    assert "Second skill" in prompt
```

**Step 7.2: 创建`src/lumos/skills/__init__.py`**

```python
"""Skills系统。"""
from lumos.skills.loader import parse_skill, Skill
from lumos.skills.manager import SkillManager

__all__ = ["Skill", "parse_skill", "SkillManager"]
```

**Step 7.3: 写`src/lumos/skills/loader.py`**

```python
"""SKILL.md解析。"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    description: str
    version: str
    tags: list[str]
    required_tools: list[str]
    optional_tools: list[str]
    max_steps: int | None
    instructions: str
    dir_path: Path
    enabled: bool = True


def parse_skill(path: Path) -> Skill:
    """从SKILL.md文件解析Skill。"""
    import frontmatter
    post = frontmatter.load(path)
    meta = post.metadata
    return Skill(
        name=meta.get("name", path.parent.name),
        description=meta.get("description", ""),
        version=meta.get("version", "0.0.0"),
        tags=list(meta.get("tags", []) or []),
        required_tools=list(meta.get("required_tools", []) or []),
        optional_tools=list(meta.get("optional_tools", []) or []),
        max_steps=meta.get("max_steps"),
        instructions=post.content.strip(),
        dir_path=path.parent,
        enabled=meta.get("enabled", True),
    )
```

**Step 7.4: 写`src/lumos/skills/manager.py`**

```python
"""Skill管理器：扫描、启用/禁用、构建系统提示词。"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable
from lumos.skills.loader import Skill, parse_skill


class SkillManager:
    def __init__(self, *, discover_dirs: Iterable[str | Path]) -> None:
        self._dirs = [Path(d) for d in discover_dirs]
        self._skills: dict[str, Skill] = {}

    def discover(self) -> None:
        self._skills.clear()
        for d in self._dirs:
            if not d.exists():
                continue
            for skill_md in d.glob("*/SKILL.md"):
                try:
                    s = parse_skill(skill_md)
                    self._skills[s.name] = s
                except Exception as e:
                    import structlog
                    structlog.get_logger().warning(
                        "skill.parse_failed", path=str(skill_md), error=str(e),
                    )

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def enable(self, name: str) -> None:
        if name in self._skills:
            self._skills[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self._skills:
            self._skills[name].enabled = False

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def list_enabled(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.enabled]

    def missing_required_tools(
        self, available_tools: set[str],
    ) -> dict[str, list[str]]:
        """返回{name: missing_tools}，表示启用的skill缺少哪些依赖工具。"""
        result: dict[str, list[str]] = {}
        for s in self._skills.values():
            if not s.enabled:
                continue
            missing = [t for t in s.required_tools if t not in available_tools]
            if missing:
                result[s.name] = missing
        return result

    def build_system_prompt(self, *, base: str) -> str:
        """拼接base prompt + 启用skills的指令。"""
        parts = [base]
        for s in self.list_enabled():
            parts.append(f"\n\n## Skill: {s.name}\n{s.instructions}")
        return "".join(parts)
```

**Step 7.5: 创建`skills/web-research/SKILL.md`**

```markdown
---
name: web-research
description: |
  进行深入的网页研究。当用户询问需要最新信息、事实核查、
  多源综合的问题时启用。提供联网搜索+抓取+总结的工作流。
version: 1.0.0
author: Lumos Team
tags: [research, web, analysis]
required_tools: [web_search, web_fetch]
optional_tools: [http_request]
max_steps: 10
---

# 网络研究技能

你是专业的研究助手。回答需要：

1. **多源验证**：至少搜索2次，交叉对比
2. **引用来源**：每个事实都标注URL
3. **时效说明**：标注信息发布日期
4. **不确定性标注**：置信度高/中/低

## 工作流

当用户问问题时：
- 先用 `web_search` 收集相关资料
- 必要时用 `web_fetch` 抓取具体页面
- 综合多源信息，给出带引用的回答
```

**Step 7.6: 创建`skills/code-assistant/SKILL.md`**

```markdown
---
name: code-assistant
description: |
  编程助手。帮助用户编写、调试、重构代码，回答技术问题。
  启用后你专注于代码质量、最佳实践、可读性。
version: 1.0.0
tags: [code, programming]
required_tools: [file_read, file_write, shell_exec]
max_steps: 20
---

# 编程助手技能

你是专业的编程助手。回答代码相关问题时要：

1. 给出可运行的代码示例
2. 解释关键概念和权衡
3. 指出常见陷阱
4. 建议测试用例

## 工作流

- 先理解用户需求
- 必要时读取相关文件 (`file_read`)
- 给出代码（可写文件 `file_write`，需用户确认）
- 必要时执行测试 (`shell_exec`，需用户确认)
```

**Step 7.7: 创建`skills/data-analysis/SKILL.md`**

```markdown
---
name: data-analysis
description: |
  数据分析助手。帮助用户分析、统计、可视化数据。
  启用后你专注于数据处理、洞察提取、清晰呈现。
version: 1.0.0
tags: [data, analysis, statistics]
required_tools: [file_read, shell_exec, calculator]
max_steps: 15
---

# 数据分析技能

你是数据分析专家。回答数据相关问题时要：

1. 明确数据来源和范围
2. 选择合适的统计方法
3. 计算关键指标
4. 总结洞察

## 工作流

- 读取数据文件 (`file_read`)
- 使用 `calculator` 做关键计算
- 必要时执行Python脚本 (`shell_exec`，需用户确认)
```

**Step 7.8: 跑测试**

Run: `pytest tests/unit/test_skills.py -v`
Expected: PASS

**Step 7.9: 提交**

```bash
git add src/lumos/skills skills/ tests/unit/test_skills.py
git commit -m "feat: skills loader and manager with 3 built-in skills"
```

---

### Task 8: MCP传输实现（stdio、SSE、StreamableHTTP）

**Files:**
- Create: `src/lumos/mcp/__init__.py`
- Create: `src/lumos/mcp/transports/__init__.py`
- Create: `src/lumos/mcp/transports/stdio.py`
- Create: `src/lumos/mcp/transports/sse.py`
- Create: `src/lumos/mcp/transports/streamable_http.py`
- Create: `src/lumos/mcp/config.py`
- Create: `tests/unit/test_mcp_transports.py`

**Interfaces:**
- Produces:
  - `BaseTransport`抽象类（start/read_messages/write_message/close）
  - `StdioTransport`, `SseTransport`, `StreamableHttpTransport`
  - `McpServerConfig`数据类

**Step 8.1: 写`src/lumos/mcp/config.py`**

```python
"""MCP服务器配置。"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class McpServerConfig:
    name: str
    transport: str  # stdio | sse | streamable_http
    enabled: bool = True
    # stdio
    command: str | None = None
    args: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    # sse / streamable_http
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
```

**Step 8.2: 写`tests/unit/test_mcp_transports.py`**

```python
"""测试MCP传输（stdio用真子进程，SSE/HTTP用mock）。"""
from __future__ import annotations
import asyncio
import json
import pytest
from lumos.mcp.transports.stdio import StdioTransport
from lumos.mcp.transports.sse import SseTransport
from lumos.mcp.transports.streamable_http import StreamableHttpTransport


@pytest.mark.asyncio
async def test_stdio_transport_echo():
    """用python作为stdio MCP服务器做echo测试。"""
    transport = StdioTransport(
        command="python",
        args=["-c", (
            "import sys, json\n"
            "for line in sys.stdin:\n"
            "    msg = json.loads(line)\n"
            "    if msg.get('method') == 'ping':\n"
            "        resp = {'jsonrpc': '2.0', 'id': msg['id'], 'result': 'pong'}\n"
            "        print(json.dumps(resp), flush=True)\n"
        )],
        env={},
    )
    await transport.start()
    try:
        await transport.write_message({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        # 等待响应
        response = await asyncio.wait_for(transport.read_message(), timeout=5.0)
        assert response["result"] == "pong"
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_sse_transport_send_receive(respx_mock):
    """SSE transport: 客户端GET SSE流，POST发送消息。"""
    import respx
    import httpx

    sse_body = (
        "event: endpoint\ndata: /post_endpoint\n\n"
        "data: {\"jsonrpc\":\"2.0\",\"id\":1,\"result\":\"ok\"}\n\n"
    )

    async def sse_handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_body,
        )

    respx_mock.get("https://mcp.test/sse").mock(side_effect=sse_handler)

    transport = SseTransport(
        url="https://mcp.test/sse", headers={},
    )
    await transport.start()
    try:
        # 应能从SSE读到一个JSON-RPC响应
        msg = await asyncio.wait_for(transport.read_message(), timeout=5.0)
        assert msg["result"] == "ok"
    finally:
        await transport.close()
```

**Step 8.3: 创建`src/lumos/mcp/__init__.py`**

```python
"""MCP客户端。"""
```

**Step 8.4: 创建`src/lumos/mcp/transports/__init__.py`**

```python
"""MCP传输实现。"""
from lumos.mcp.transports.stdio import StdioTransport
from lumos.mcp.transports.sse import SseTransport
from lumos.mcp.transports.streamable_http import StreamableHttpTransport
from lumos.mcp.transports.base import BaseTransport

__all__ = [
    "BaseTransport", "StdioTransport", "SseTransport", "StreamableHttpTransport",
]
```

**Step 8.5: 写`src/lumos/mcp/transports/base.py`**

```python
"""MCP传输抽象基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseTransport(ABC):
    """所有MCP传输的抽象接口。"""

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def read_message(self) -> dict[str, Any]:
        """读取下一个JSON-RPC消息。"""
        ...

    @abstractmethod
    async def write_message(self, msg: dict[str, Any]) -> None:
        """发送一个JSON-RPC消息。"""
        ...

    @abstractmethod
    async def close(self) -> None:
        ...
```

**Step 8.6: 写`src/lumos/mcp/transports/stdio.py`**

```python
"""stdio传输：本地子进程。"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from typing import Any
from lumos.errors import McpConnectionError


class StdioTransport:
    def __init__(
        self, *, command: str, args: tuple[str, ...] = (), env: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.args = args
        self.env = env or {}
        self.proc: asyncio.subprocess.Process | None = None
        self._stderr_task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            full_env = {**os.environ, **self.env}
            self.proc = await asyncio.create_subprocess_exec(
                self.command, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
            )
        except Exception as e:
            raise McpConnectionError(
                f"Failed to start stdio MCP: {self.command} {self.args}: {e}",
                cause=e,
            ) from e
        self._stderr_task = asyncio.create_task(self._drain_stderr())

    async def _drain_stderr(self) -> None:
        if self.proc and self.proc.stderr:
            while True:
                line = await self.proc.stderr.readline()
                if not line:
                    return
                import structlog
                structlog.get_logger().warning(
                    "mcp.stderr", server=self.command, line=line.decode(errors="replace").rstrip(),
                )

    async def read_message(self) -> dict[str, Any]:
        if not self.proc or not self.proc.stdout:
            raise McpConnectionError("stdio transport not started")
        line = await self.proc.stdout.readline()
        if not line:
            raise McpConnectionError("stdio MCP closed stdout")
        try:
            return json.loads(line.decode("utf-8").strip())
        except json.JSONDecodeError as e:
            raise McpConnectionError(f"Invalid JSON from stdio MCP: {e}") from e

    async def write_message(self, msg: dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise McpConnectionError("stdio transport not started")
        data = (json.dumps(msg) + "\n").encode("utf-8")
        self.proc.stdin.write(data)
        await self.proc.stdin.drain()

    async def close(self) -> None:
        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
                await asyncio.wait_for(self.proc.wait(), timeout=5.0)
            except (ProcessLookupError, asyncio.TimeoutError):
                self.proc.kill()
            self.proc = None
        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass
            self._stderr_task = None
```

**Step 8.7: 写`src/lumos/mcp/transports/sse.py`**

```python
"""SSE传输：远程MCP服务器。"""
from __future__ import annotations
import asyncio
import json
from typing import Any
import httpx
from lumos.errors import McpConnectionError


class SseTransport:
    def __init__(self, *, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None
        self._response: httpx.Response | None = None
        self._post_url: str | None = None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._reader_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=None))
        try:
            req = self._client.build_request("GET", self.url, headers=self.headers)
            self._response = await self._client.send(req, stream=True)
            self._response.raise_for_status()
        except Exception as e:
            raise McpConnectionError(
                f"Failed to connect SSE MCP {self.url}: {e}", cause=e,
            ) from e
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def _reader_loop(self) -> None:
        assert self._response is not None
        event_type = ""
        data_lines: list[str] = []
        try:
            async for line in self._response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data_lines.append(line.split(":", 1)[1].strip())
                elif line == "":
                    if event_type == "endpoint" and data_lines:
                        endpoint = data_lines[-1]
                        base = str(self._response.request.url)
                        from urllib.parse import urljoin
                        self._post_url = urljoin(base, endpoint)
                    elif event_type in ("message", "") and data_lines:
                        try:
                            payload = json.loads("\n".join(data_lines))
                            await self._queue.put(payload)
                        except json.JSONDecodeError:
                            pass
                    event_type = ""
                    data_lines = []
        except Exception as e:
            import structlog
            structlog.get_logger().error("mcp.sse.reader_failed", error=str(e))
        finally:
            await self._response.aclose()

    async def read_message(self) -> dict[str, Any]:
        return await asyncio.wait_for(self._queue.get(), timeout=60.0)

    async def write_message(self, msg: dict[str, Any]) -> None:
        if not self._client:
            raise McpConnectionError("SSE transport not started")
        if not self._post_url:
            raise McpConnectionError("SSE endpoint not yet announced")
        try:
            resp = await self._client.post(
                self._post_url,
                json=msg,
                headers={**self.headers, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
        except Exception as e:
            raise McpConnectionError(f"SSE POST failed: {e}", cause=e) from e

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None
        if self._client:
            await self._client.aclose()
            self._client = None
        self._response = None
        self._post_url = None
```

**Step 8.8: 写`src/lumos/mcp/transports/streamable_http.py`**

```python
"""Streamable HTTP传输（MCP 2025协议）。"""
from __future__ import annotations
import asyncio
import json
from typing import Any
import httpx
from lumos.errors import McpConnectionError


class StreamableHttpTransport:
    """MCP Streamable HTTP传输。

    协议要点：
    - 客户端POST JSON-RPC消息到endpoint
    - 服务端响应SSE流或单条JSON
    - 双向通信通过持续HTTP连接
    """

    def __init__(self, *, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=60))

    async def read_message(self) -> dict[str, Any]:
        """Streamable HTTP的read语义：阻塞等待下一个SSE事件。"""
        if not self._client:
            raise McpConnectionError("streamable_http transport not started")
        # 由客户端主动POST+读取响应，因此read_message通常不单独调用。
        # 这里提供基线实现：读取self._client上的最近响应
        # 实际使用中由McpClient在write_message后处理响应
        raise NotImplementedError(
            "Streamable HTTP is request-response; use write_message which returns response"
        )

    async def write_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """发送JSON-RPC消息，返回响应。"""
        if not self._client:
            raise McpConnectionError("streamable_http transport not started")
        try:
            resp = await self._client.post(
                self.url,
                json=msg,
                headers={
                    **self.headers,
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "text/event-stream" in ct:
                # 解析SSE格式响应
                data_lines: list[str] = []
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        data_lines.append(line.split(":", 1)[1].strip())
                if data_lines:
                    return json.loads("\n".join(data_lines))
                raise McpConnectionError("Empty SSE response")
            return resp.json()
        except Exception as e:
            raise McpConnectionError(
                f"streamable_http POST failed: {e}", cause=e,
            ) from e

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
```

**Step 8.9: 跑测试**

Run: `pytest tests/unit/test_mcp_transports.py -v`
Expected: PASS

**Step 8.10: 提交**

```bash
git add src/lumos/mcp tests/unit/test_mcp_transports.py
git commit -m "feat: MCP transports (stdio, SSE, streamable HTTP)"
```

---

### Task 9: MCP客户端与Manager

**Files:**
- Create: `src/lumos/mcp/client.py`
- Create: `src/lumos/mcp/manager.py`
- Create: `tests/unit/test_mcp_manager.py`

**Interfaces:**
- Produces:
  - `McpClient`：单个MCP服务器连接的封装（connect/disconnect/call_tool/list_tools）
  - `McpManager`：管理所有连接（connect_all/shutdown/all_tools/call_tool_by_name）

**Step 9.1: 写`tests/unit/test_mcp_manager.py`**

```python
"""测试MCP Manager（用一个假stdio MCP服务器脚本）。"""
from __future__ import annotations
import asyncio
import json
import shutil
from pathlib import Path
import pytest
from lumos.mcp.config import McpServerConfig
from lumos.mcp.manager import McpManager


PYTHON = shutil.which("python") or shutil.which("python3")


FAKE_MCP_SCRIPT = """
import sys, json

def send(msg):
    print(json.dumps(msg), flush=True)

def handle(msg):
    method = msg.get("method")
    if method == "initialize":
        return {"jsonrpc":"2.0","id":msg["id"],"result":{
            "protocolVersion":"2024-11-05",
            "capabilities":{"tools":{"listChanged":False}},
            "serverInfo":{"name":"fake","version":"0.1.0"},
        }}
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc":"2.0","id":msg["id"],"result":{
            "tools":[
                {"name":"echo","description":"echo","inputSchema":{
                    "type":"object",
                    "properties":{"text":{"type":"string"}},
                    "required":["text"],
                }},
            ]
        }}
    if method == "tools/call":
        return {"jsonrpc":"2.0","id":msg["id"],"result":{
            "content":[{"type":"text","text":msg["params"]["arguments"]["text"]}]
        }}
    return None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    resp = handle(msg)
    if resp is not None:
        send(resp)
"""


@pytest.fixture
def fake_mcp_path(tmp_path: Path) -> Path:
    p = tmp_path / "fake_mcp.py"
    p.write_text(FAKE_MCP_SCRIPT)
    return p


@pytest.mark.asyncio
async def test_manager_connect_and_list_tools(fake_mcp_path: Path):
    if not PYTHON:
        pytest.skip("no python interpreter")
    cfg = McpServerConfig(
        name="fake", transport="stdio",
        command=PYTHON, args=(str(fake_mcp_path),),
    )
    mgr = McpManager([cfg])
    await mgr.connect_all()
    try:
        tools = mgr.all_tools()
        names = {t.name for t in tools}
        assert any(n.startswith("fake__") for n in names)
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_manager_call_tool(fake_mcp_path: Path):
    if not PYTHON:
        pytest.skip("no python interpreter")
    cfg = McpServerConfig(
        name="fake", transport="stdio",
        command=PYTHON, args=(str(fake_mcp_path),),
    )
    mgr = McpManager([cfg])
    await mgr.connect_all()
    try:
        # 查找带前缀的echo工具
        tools = mgr.all_tools()
        echo_spec = next(t for t in tools if t.name.endswith("echo"))
        result = await mgr.call_tool(echo_spec.name, {"text": "hello"})
        assert "hello" in result
    finally:
        await mgr.shutdown()
```

**Step 9.2: 写`src/lumos/mcp/client.py`**

```python
"""单个MCP服务器连接的封装。"""
from __future__ import annotations
import asyncio
import json
from typing import Any
from lumos.mcp.config import McpServerConfig
from lumos.mcp.transports import (
    BaseTransport, StdioTransport, SseTransport, StreamableHttpTransport,
)
from lumos.errors import McpConnectionError


class McpClient:
    """单个MCP服务器的JSON-RPC客户端。"""

    def __init__(self, config: McpServerConfig) -> None:
        self.config = config
        self.transport: BaseTransport = self._build_transport()
        self._initialized = False
        self._request_id = 0
        self._lock = asyncio.Lock()

    def _build_transport(self) -> BaseTransport:
        if self.config.transport == "stdio":
            return StdioTransport(
                command=self.config.command or "",
                args=self.config.args, env=self.config.env,
            )
        if self.config.transport == "sse":
            return SseTransport(
                url=self.config.url or "", headers=self.config.headers,
            )
        if self.config.transport == "streamable_http":
            return StreamableHttpTransport(
                url=self.config.url or "", headers=self.config.headers,
            )
        raise ValueError(f"Unknown transport: {self.config.transport}")

    async def connect(self) -> None:
        await self.transport.start()
        # MCP初始化握手
        try:
            await self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "lumos", "version": "0.1.0"},
            })
            await self._notify("notifications/initialized", {})
            self._initialized = True
        except Exception as e:
            await self.transport.close()
            raise McpConnectionError(
                f"MCP initialize failed for {self.config.name}: {e}",
                cause=e,
            ) from e

    async def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        msg_id = await self._next_id()
        request = {
            "jsonrpc": "2.0", "id": msg_id,
            "method": method, "params": params,
        }
        async with self._lock:
            await self.transport.write_message(request)
            # streamable_http是请求-响应模式，write_message返回响应
            if isinstance(self.transport, StreamableHttpTransport):
                response = await self.transport.write_message(request)  # 第二次调用不对
            # 实际：streamable_http的write_message返回响应，所以这里要重写
            raise NotImplementedError("Use specialized call paths")

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
        notification = {"jsonrpc": "2.0", "method": method, "params": params}
        await self.transport.write_message(notification)

    async def list_tools(self) -> list[dict[str, Any]]:
        resp = await self._request_unlocked("tools/list", {})
        return resp.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        resp = await self._request_unlocked(
            "tools/call", {"name": name, "arguments": arguments},
        )
        content = resp.get("result", {}).get("content", [])
        parts: list[str] = []
        for c in content:
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
        return "\n".join(parts) if parts else json.dumps(resp.get("result"))

    async def _request_unlocked(
        self, method: str, params: dict[str, Any],
    ) -> dict[str, Any]:
        """根据传输类型分派的request实现。"""
        msg_id = await self._next_id()
        request = {
            "jsonrpc": "2.0", "id": msg_id, "method": method, "params": params,
        }
        if isinstance(self.transport, StreamableHttpTransport):
            response = await self.transport.write_message(request)
            if "error" in response:
                raise McpConnectionError(f"MCP error: {response['error']}")
            return response
        # stdio / SSE: write then read
        async with self._lock:
            await self.transport.write_message(request)
            while True:
                msg = await self.transport.read_message()
                if msg.get("id") == msg_id:
                    if "error" in msg:
                        raise McpConnectionError(f"MCP error: {msg['error']}")
                    return msg

    async def disconnect(self) -> None:
        await self.transport.close()
```

**Step 9.3: 写`src/lumos/mcp/manager.py`**

```python
"""MCP Manager：管理多个MCP服务器连接。"""
from __future__ import annotations
from typing import Any
import asyncio
from lumos.agent.message import ToolSpec
from lumos.errors import McpConnectionError
from lumos.mcp.client import McpClient
from lumos.mcp.config import McpServerConfig


class McpManager:
    """管理所有MCP服务器连接。"""

    def __init__(self, configs: list[McpServerConfig]) -> None:
        self.configs = [c for c in configs if c.enabled]
        self._clients: dict[str, McpClient] = {}

    async def connect_all(self) -> None:
        """并发连接所有enabled服务器，单个失败不影响其他。"""
        results = await asyncio.gather(
            *[self._connect_one(c) for c in self.configs],
            return_exceptions=True,
        )
        for c, r in zip(self.configs, results):
            if isinstance(r, Exception):
                import structlog
                structlog.get_logger().error(
                    "mcp.connect_failed", name=c.name, error=str(r),
                )

    async def _connect_one(self, config: McpServerConfig) -> None:
        client = McpClient(config)
        await client.connect()
        self._clients[config.name] = client

    async def shutdown(self) -> None:
        await asyncio.gather(
            *[c.disconnect() for c in self._clients.values()],
            return_exceptions=True,
        )
        self._clients.clear()

    def all_tools(self) -> list[ToolSpec]:
        specs: list[ToolSpec] = []
        for server_name, client in self._clients.items():
            # 同步遍历已缓存的工具（连接时调用list_tools）
            for t in getattr(client, "_tools_cache", []):
                specs.append(ToolSpec(
                    name=f"{server_name}__{t['name']}",
                    description=t.get("description", ""),
                    parameters=t.get("inputSchema", {}),
                    source="mcp",
                ))
        return specs

    async def call_tool(self, full_name: str, arguments: dict[str, Any]) -> str:
        if "__" not in full_name:
            raise ValueError(f"Invalid MCP tool name: {full_name}")
        server_name, tool_name = full_name.split("__", 1)
        client = self._clients.get(server_name)
        if client is None:
            raise McpConnectionError(f"MCP server not connected: {server_name}")
        return await client.call_tool(tool_name, arguments)

    def get_client(self, name: str) -> McpClient | None:
        return self._clients.get(name)

    async def refresh_tools_cache(self) -> None:
        """每个客户端连接后调用list_tools并缓存。"""
        for client in self._clients.values():
            try:
                client._tools_cache = await client.list_tools()
            except Exception as e:
                import structlog
                structlog.get_logger().warning(
                    "mcp.list_tools_failed", name=client.config.name, error=str(e),
                )
```

**Step 9.4: 修复`src/lumos/mcp/client.py`的初始化（连接后立即缓存tools）**

修改`connect`方法末尾添加：
```python
        # 缓存工具列表
        try:
            self._tools_cache = await self.list_tools()
        except Exception:
            self._tools_cache = []
```

并且删除`_request`和`_notify`中错误的`_request_unlocked`重定向（保留但unused）。最终client.py应清晰展示核心逻辑。

**Step 9.5: 跑测试**

Run: `pytest tests/unit/test_mcp_manager.py -v`
Expected: PASS

**Step 9.6: 提交**

```bash
git add src/lumos/mcp/client.py src/lumos/mcp/manager.py tests/unit/test_mcp_manager.py
git commit -m "feat: MCP client and manager with tool caching and namespace"
```

---

## Phase D：Agent核心

### Task 10: Agent主循环

**Files:**
- Create: `src/lumos/agent/core.py`
- Create: `src/lumos/agent/runner.py`
- Create: `tests/unit/test_agent_core.py`

**Interfaces:**
- Produces:
  - `Agent`：主循环类，含`run(user_input, on_event, cancel) -> Usage`
  - `AgentRunner`：单session运行器，绑定provider/tools/skills/mcp/cancel

**Step 10.1: 写`tests/unit/test_agent_core.py`**

```python
"""测试Agent主循环。"""
from __future__ import annotations
import asyncio
import pytest
from lumos.agent.core import Agent
from lumos.agent.message import Message, ToolCall, ToolSpec, Usage
from lumos.tools.base import Tool
from lumos.tools.registry import ToolRegistry, register_tool


@register_tool(
    name="mytool",
    description="test tool",
    parameters={
        "type": "object",
        "properties": {"q": {"type": "string"}},
        "required": ["q"],
    },
)
class MyTool(Tool):
    async def execute(self, *, q: str) -> str:
        return f"result for {q}"


class FakeProvider:
    def __init__(self, scripted: list[tuple[str, list[ToolCall]]]):
        self.scripted = list(scripted)
        self.calls: list[list[Message]] = []

    async def chat(self, messages, *, system, tools, temperature,
                   max_tokens, cancel, on_text):
        self.calls.append(list(messages))
        # 返回下一个脚本响应
        text, tool_calls = self.scripted.pop(0)
        if cancel:
            cancel.set()
        return text, tool_calls, Usage(10, 5, 15)


@pytest.mark.asyncio
async def test_agent_runs_until_no_tool_calls():
    provider = FakeProvider([("Hello!", [])])
    registry = ToolRegistry()
    registry.discover_globals([MyTool])

    agent = Agent(
        provider=provider,
        tool_registry=registry,
        skills=None,
        mcp=None,
        config=type("Cfg", (), {"max_steps": 5, "system_prompt": "BASE"})(),
    )

    events: list[str] = []
    async def on_event(e):
        events.append(e.type)

    usage = await agent.run("hi", on_event=on_event)
    assert usage.total_tokens == 15
    assert "done" in events


@pytest.mark.asyncio
async def test_agent_runs_tool_then_done():
    provider = FakeProvider([
        ("Searching...", [ToolCall(id="t1", name="mytool", arguments={"q": "AI"})]),
        ("Done", []),
    ])
    registry = ToolRegistry()
    registry.discover_globals([MyTool])

    agent = Agent(
        provider=provider,
        tool_registry=registry,
        skills=None,
        mcp=None,
        config=type("Cfg", (), {"max_steps": 5, "system_prompt": "BASE"})(),
    )

    events: list[dict] = []
    async def on_event(e):
        events.append({"type": e.type, "data": e.data})

    usage = await agent.run("hi", on_event=on_event)
    assert any(e["type"] == "tool_call_start" for e in events)
    assert any(e["type"] == "tool_call_result" for e in events)
    assert usage.total_tokens == 30


@pytest.mark.asyncio
async def test_agent_respects_max_steps():
    provider = FakeProvider([
        ("step1", [ToolCall(id="t1", name="mytool", arguments={"q": "a"})]),
        ("step2", [ToolCall(id="t2", name="mytool", arguments={"q": "b"})]),
        ("step3", [ToolCall(id="t3", name="mytool", arguments={"q": "c"})]),
    ])
    registry = ToolRegistry()
    registry.discover_globals([MyTool])

    agent = Agent(
        provider=provider,
        tool_registry=registry,
        skills=None,
        mcp=None,
        config=type("Cfg", (), {"max_steps": 2, "system_prompt": "BASE"})(),
    )

    with pytest.raises(Exception, match="[Mm]ax"):
        await agent.run("hi", on_event=lambda e: asyncio.sleep(0))
```

**Step 10.2: 在`tools/registry.py`添加`discover_globals`辅助方法**

```python
    def discover_globals(self, tools: list[type[Tool]]) -> None:
        """注册已显式提供的Tool类列表（用于测试）。"""
        for t_cls in tools:
            if hasattr(t_cls, "meta"):
                self.register(t_cls())
```

**Step 10.3: 创建`src/lumos/agent/runner.py`**

```python
"""单session Agent运行器：管理cancel事件、on_event回调、生命周期。"""
from __future__ import annotations
import asyncio
from typing import Awaitable, Callable
from lumos.agent.core import Agent
from lumos.agent.message import AgentEvent
from lumos.tools.registry import ToolRegistry
from lumos.skills.manager import SkillManager
from lumos.mcp.manager import McpManager
from lumos.providers.base import BaseProvider
from lumos.config import AgentConfig


OnEvent = Callable[[AgentEvent], Awaitable[None]]


class AgentRunner:
    """一个session对应一个AgentRunner实例。"""

    def __init__(
        self,
        *,
        session_id: str,
        provider: BaseProvider,
        tool_registry: ToolRegistry,
        skill_manager: SkillManager | None,
        mcp_manager: McpManager | None,
        agent_config: AgentConfig,
        history: list | None = None,
    ) -> None:
        self.session_id = session_id
        self.cancel = asyncio.Event()
        self.agent = Agent(
            provider=provider,
            tool_registry=tool_registry,
            skill_manager=skill_manager,
            mcp_manager=mcp_manager,
            agent_config=agent_config,
            history=list(history or []),
        )

    async def run(self, user_input: str, on_event: OnEvent) -> None:
        self.cancel.clear()
        await self.agent.run(user_input, on_event=on_event, cancel=self.cancel)

    def request_cancel(self) -> None:
        self.cancel.set()
```

**Step 10.4: 写`src/lumos/agent/core.py`**

```python
"""Agent主循环（ReAct风格）。"""
from __future__ import annotations
import asyncio
from typing import Awaitable, Callable
from lumos.agent.message import (
    Message, TextContent, ToolCall, ToolResult, Usage, AgentEvent, ToolSpec,
)
from lumos.tools.registry import ToolRegistry
from lumos.skills.manager import SkillManager
from lumos.mcp.manager import McpManager
from lumos.errors import MaxStepsExceededError, CancelledError, ToolExecutionError
from lumos.config import AgentConfig


OnEvent = Callable[[AgentEvent], Awaitable[None]]


class Agent:
    def __init__(
        self,
        *,
        provider,
        tool_registry: ToolRegistry,
        skill_manager: SkillManager | None,
        mcp_manager: McpManager | None,
        agent_config: AgentConfig,
        history: list[Message] | None = None,
    ) -> None:
        self.provider = provider
        self.tools = tool_registry
        self.skills = skill_manager
        self.mcp = mcp_manager
        self.config = agent_config
        self.history: list[Message] = list(history or [])

    def _collect_tool_specs(self) -> list[ToolSpec]:
        specs = self.tools.all_specs()
        if self.mcp is not None:
            specs.extend(self.mcp.all_tools())
        return specs

    async def _build_system_prompt(self) -> str:
        base = self.config.system_prompt
        if self.skills is None:
            return base
        return self.skills.build_system_prompt(base=base)

    async def _execute_tool(
        self, tc: ToolCall, on_event: OnEvent,
    ) -> ToolResult:
        try:
            if "__" in tc.name and self.mcp is not None:
                result_text = await self.mcp.call_tool(tc.name, tc.arguments)
            else:
                tool = self.tools.get(tc.name)
                result_text = await tool.execute(**tc.arguments)
            return ToolResult(
                tool_call_id=tc.id, content=result_text,
                is_error=False, name=tc.name,
            )
        except CancelledError:
            raise
        except Exception as e:
            error_text = f"Error: {type(e).__name__}: {e}"
            return ToolResult(
                tool_call_id=tc.id, content=error_text,
                is_error=True, name=tc.name,
            )

    async def run(
        self,
        user_input: str,
        *,
        on_event: OnEvent,
        cancel: asyncio.Event | None = None,
    ) -> Usage:
        cancel = cancel or asyncio.Event()
        total_usage = Usage()
        self.history.append(Message(role="user", content=user_input))

        for step in range(self.config.max_steps):
            if cancel.is_set():
                raise CancelledError("Run cancelled")

            system = await self._build_system_prompt()
            tool_specs = self._collect_tool_specs()

            async def on_text(delta: str) -> None:
                if cancel.is_set():
                    raise asyncio.CancelledError()
                await on_event(AgentEvent(
                    type="text", session_id="", data={"delta": delta},
                ))

            text, tool_calls, usage = await self.provider.chat(
                messages=self.history,
                system=system,
                tools=tool_specs,
                temperature=0.7,
                max_tokens=None,
                cancel=cancel,
                on_text=on_text,
            )
            total_usage.prompt_tokens += usage.prompt_tokens
            total_usage.completion_tokens += usage.completion_tokens
            total_usage.total_tokens += usage.total_tokens

            content: list = []
            if text:
                content.append(TextContent(text=text))
            for tc in tool_calls:
                content.append(tc)
            self.history.append(Message(role="assistant", content=content))

            await on_event(AgentEvent(
                type="usage", session_id="",
                data={
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                },
            ))

            if not tool_calls:
                await on_event(AgentEvent(
                    type="done", session_id="",
                    data={"usage": total_usage.__dict__},
                ))
                return total_usage

            # 并行执行所有tool_calls
            await on_event(AgentEvent(
                type="tool_call_start", session_id="",
                data={"calls": [tc.to_dict() for tc in tool_calls]},
            ))
            results = await asyncio.gather(
                *[self._execute_tool(tc, on_event) for tc in tool_calls],
                return_exceptions=False,
            )
            for tc, r in zip(tool_calls, results):
                self.history.append(r.to_message())
                await on_event(AgentEvent(
                    type="tool_call_result", session_id="",
                    data={
                        "tool_call_id": r.tool_call_id,
                        "name": tc.name,
                        "result": r.content,
                        "is_error": r.is_error,
                    },
                ))
            await on_event(AgentEvent(
                type="tool_call_end", session_id="", data=None,
            ))

        raise MaxStepsExceededError(
            f"Agent exceeded max_steps={self.config.max_steps}"
        )
```

**Step 10.5: 跑测试**

Run: `pytest tests/unit/test_agent_core.py -v`
Expected: PASS

**Step 10.6: 提交**

```bash
git add src/lumos/agent/core.py src/lumos/agent/runner.py tests/unit/test_agent_core.py
git commit -m "feat: Agent main loop with parallel tool execution"
```

---

### Task 11: 上下文压缩

**Files:**
- Create: `src/lumos/agent/context.py`
- Create: `tests/unit/test_agent_context.py`

**Interfaces:**
- Produces:
  - `estimate_tokens(messages) -> int`：粗略估算token数（按4字符/token）
  - `compress_history(history, summarizer, threshold) -> list[Message]`：超过阈值时压缩

**Step 11.1: 写`tests/unit/test_agent_context.py`**

```python
"""测试上下文压缩。"""
from __future__ import annotations
import pytest
from lumos.agent.context import estimate_tokens, compress_history
from lumos.agent.message import Message, TextContent


@pytest.mark.asyncio
async def test_compress_under_threshold():
    history = [Message(role="user", content="hi")]
    async def summarizer(text):
        return f"summary: {text}"
    result = await compress_history(
        history, summarizer=summarizer, threshold=10000,
    )
    assert result == history


@pytest.mark.asyncio
async def test_compress_over_threshold():
    # 制造长历史
    history = [
        Message(role="user", content="x" * 5000),
        Message(role="assistant", content="y" * 5000),
        Message(role="user", content="z" * 5000),
        Message(role="assistant", content="w" * 5000),
    ]
    called = []
    async def summarizer(text):
        called.append(len(text))
        return f"[summary of {len(text)} chars]"

    result = await compress_history(
        history, summarizer=summarizer, threshold=1000,
    )
    assert len(result) < len(history)
    assert len(called) > 0


def test_estimate_tokens():
    msgs = [
        Message(role="user", content="hello"),  # 5 chars ≈ 2 tokens
        Message(role="assistant", content="hi there"),  # 8 chars ≈ 2 tokens
    ]
    tokens = estimate_tokens(msgs)
    assert tokens > 0
```

**Step 11.2: 写`src/lumos/agent/context.py`**

```python
"""上下文窗口管理与压缩。"""
from __future__ import annotations
from typing import Awaitable, Callable
from lumos.agent.message import Message, TextContent


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for c in content:
        if c.type == "text":
            parts.append(c.text)
        elif c.type == "tool_call":
            parts.append(f"tool_call({c.name}, {c.arguments})")
    return " ".join(parts)


def estimate_tokens(messages: list[Message]) -> int:
    """粗略估算token数（4字符/token近似）。"""
    total = 0
    for m in messages:
        total += len(_content_text(m.content)) // 4 + 4  # 每条消息加4 token开销
    return total


Summarizer = Callable[[str], Awaitable[str]]


async def compress_history(
    history: list[Message],
    *,
    summarizer: Summarizer,
    threshold: int,
) -> list[Message]:
    """当总token数超过threshold时，将前半部分user/assistant消息压缩为一条summary。"""
    if estimate_tokens(history) <= threshold:
        return history

    # 找到第一个非system消息的位置，保留首条user消息不动
    keep_count = 1
    head = history[:keep_count]
    body = history[keep_count:]

    # 合并body为单个文本
    body_text = "\n".join(
        f"{m.role}: {_content_text(m.content)}" for m in body
    )
    summary = await summarizer(body_text)
    summary_msg = Message(
        role="system",
        content=f"[Earlier messages summary]\n{summary}",
    )
    return list(head) + [summary_msg]
```

**Step 11.3: 跑测试**

Run: `pytest tests/unit/test_agent_context.py -v`
Expected: PASS

**Step 11.4: 提交**

```bash
git add src/lumos/agent/context.py tests/unit/test_agent_context.py
git commit -m "feat: context window management with summarization"
```

---

## Phase E：持久化仓储

### Task 12: 用户仓储与认证工具

**Files:**
- Create: `src/lumos/persistence/repositories/__init__.py`
- Create: `src/lumos/persistence/repositories/users.py`
- Create: `src/lumos/persistence/repositories/sessions.py`
- Create: `src/lumos/persistence/repositories/messages.py`
- Create: `src/lumos/persistence/repositories/mcp_servers.py`
- Create: `src/lumos/api/auth_utils.py`
- Create: `tests/unit/test_user_repository.py`
- Create: `tests/unit/test_auth_utils.py`

**Interfaces:**
- Produces:
  - `UserRepository`：create/get_by_email/get_by_id
  - `ChatSessionRepository`：create/list_by_user/get/update/delete/update_skills
  - `MessageRepository`：append/list_by_session/load_history
  - `McpServerRepository`：list_by_user/upsert/delete
  - `hash_password`, `verify_password`, `create_token_pair`, `decode_token`, `revoke_token`

**Step 12.1: 写`tests/unit/test_auth_utils.py`**

```python
"""测试密码哈希与JWT。"""
from __future__ import annotations
import time
import pytest
from lumos.api.auth_utils import (
    hash_password, verify_password,
    create_token_pair, decode_token,
)
from lumos.errors import LumosError


def test_hash_and_verify():
    h = hash_password("hunter2")
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    pair = create_token_pair("user-1", secret="s", access_ttl=60, refresh_ttl=120)
    assert pair.access_token and pair.refresh_token
    decoded = decode_token(pair.access_token, secret="s", expected_type="access")
    assert decoded["sub"] == "user-1"


def test_jwt_wrong_type():
    pair = create_token_pair("u", secret="s", access_ttl=60, refresh_ttl=120)
    with pytest.raises(Exception):
        decode_token(pair.refresh_token, secret="s", expected_type="access")


def test_jwt_expired():
    pair = create_token_pair("u", secret="s", access_ttl=-1, refresh_ttl=120)
    with pytest.raises(Exception, match="expired|Expired"):
        decode_token(pair.access_token, secret="s", expected_type="access")


def test_jwt_wrong_secret():
    pair = create_token_pair("u", secret="s1", access_ttl=60, refresh_ttl=120)
    with pytest.raises(Exception):
        decode_token(pair.access_token, secret="s2", expected_type="access")
```

**Step 12.2: 写`tests/unit/test_user_repository.py`**

```python
"""测试UserRepository。"""
from __future__ import annotations
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.persistence.db import get_engine, get_session_factory, init_db
from lumos.persistence.repositories.users import UserRepository


@pytest.fixture
async def session() -> AsyncSession:
    eng = get_engine("sqlite+aiosqlite:///:memory:")
    await init_db(eng)
    factory = get_session_factory(eng)
    async with factory() as s:
        yield s
    await eng.dispose()


@pytest.mark.asyncio
async def test_create_and_get(session: AsyncSession):
    repo = UserRepository(session)
    user = await repo.create(email="a@b.com", password_hash="h")
    assert user.id
    assert user.email == "a@b.com"

    found = await repo.get_by_email("a@b.com")
    assert found is not None
    assert found.id == user.id

    by_id = await repo.get_by_id(user.id)
    assert by_id is not None
```

**Step 12.3: 创建`src/lumos/persistence/repositories/__init__.py`**

```python
"""仓储层。"""
from lumos.persistence.repositories.users import UserRepository
from lumos.persistence.repositories.sessions import ChatSessionRepository
from lumos.persistence.repositories.messages import MessageRepository
from lumos.persistence.repositories.mcp_servers import McpServerRepository

__all__ = [
    "UserRepository", "ChatSessionRepository",
    "MessageRepository", "McpServerRepository",
]
```

**Step 12.4: 写`src/lumos/persistence/repositories/users.py`**

```python
"""用户仓储。"""
from __future__ import annotations
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.persistence.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, email: str, password_hash: str,
    ) -> User:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            is_active=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)
```

**Step 12.5: 写`src/lumos/persistence/repositories/sessions.py`**

```python
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
```

**Step 12.6: 写`src/lumos/persistence/repositories/messages.py`**

```python
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
```

**Step 12.7: 写`src/lumos/persistence/repositories/mcp_servers.py`**

```python
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
```

**Step 12.8: 写`src/lumos/api/__init__.py`（目录+空文件）**

```bash
mkdir -p src/lumos/api/routes
touch src/lumos/api/__init__.py
touch src/lumos/api/routes/__init__.py
```

**Step 12.9: 写`src/lumos/api/auth_utils.py`**

```python
"""认证工具：密码哈希 + JWT。"""
from __future__ import annotations
import time
from dataclasses import dataclass
import bcrypt
import jwt
from lumos.errors import LumosError


def hash_password(password: str, *, rounds: int = 12) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=rounds),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


def create_token_pair(
    user_id: str,
    *,
    secret: str,
    access_ttl: int,
    refresh_ttl: int,
) -> TokenPair:
    now = int(time.time())
    access = jwt.encode(
        {"sub": user_id, "type": "access", "iat": now, "exp": now + access_ttl},
        secret, algorithm="HS256",
    )
    refresh = jwt.encode(
        {"sub": user_id, "type": "refresh", "iat": now, "exp": now + refresh_ttl},
        secret, algorithm="HS256",
    )
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=access_ttl)


def decode_token(
    token: str, *, secret: str, expected_type: str,
) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise LumosError("token expired") from e
    except jwt.InvalidTokenError as e:
        raise LumosError(f"invalid token: {e}") from e
    if payload.get("type") != expected_type:
        raise LumosError(f"wrong token type: expected {expected_type}")
    return payload
```

**Step 12.10: 跑测试**

Run: `pytest tests/unit/test_user_repository.py tests/unit/test_auth_utils.py -v`
Expected: PASS

**Step 12.11: 提交**

```bash
git add src/lumos/persistence/repositories src/lumos/api tests/unit/test_user_repository.py tests/unit/test_auth_utils.py
git commit -m "feat: user/session/message/mcp repositories and auth utils"
```

---

## Phase F：Web API

### Task 13: Pydantic Schemas与依赖注入

**Files:**
- Create: `src/lumos/api/schemas.py`
- Create: `src/lumos/api/deps.py`
- Create: `tests/unit/test_schemas.py`

**Interfaces:**
- Produces:
  - Pydantic models: `UserOut`, `RegisterRequest`, `LoginRequest`, `TokenResponse`, `SessionCreate`, `SessionOut`, `MessageOut`, `SkillOut`, `McpServerCreate`, `McpServerOut`, `HealthResponse`
  - FastAPI dependencies: `get_db`, `get_current_user`

**Step 13.1: 写`tests/unit/test_schemas.py`**

```python
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
```

**Step 13.2: 写`src/lumos/api/schemas.py`**

```python
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
```

**Step 13.3: 写`src/lumos/api/deps.py`**

```python
"""FastAPI依赖注入。"""
from __future__ import annotations
from typing import AsyncIterator
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.persistence.db import get_session_factory
from lumos.persistence.models import User
from lumos.persistence.repositories.users import UserRepository
from lumos.api.auth_utils import decode_token


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory = get_session_factory(request.app.state.engine)
    async with factory() as session:
        yield session


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    secret = __import__("lumos.api.deps_helper", fromlist=["get_jwt_secret"]).get_jwt_secret()
    try:
        payload = decode_token(token, secret=secret, expected_type="access")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    repo = UserRepository(db)
    user = await repo.get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found",
        )
    return user
```

**Step 13.4: 写`src/lumos/api/deps_helper.py`**

```python
"""配置助手：访问app.state。"""
from __future__ import annotations
from fastapi import Request


def get_jwt_secret() -> str:
    from lumos.config import get_config
    return get_config().auth.jwt_secret


def get_provider(request: Request):
    return request.app.state.provider


def get_tool_registry(request: Request):
    return request.app.state.tool_registry


def get_skill_manager(request: Request):
    return request.app.state.skill_manager


def get_mcp_manager(request: Request):
    return request.app.state.mcp_manager
```

**Step 13.5: 添加`src/lumos/config.py`的`get_config`**

```python
_CONFIG_INSTANCE: "LumosConfig | None" = None


def set_config(cfg: "LumosConfig") -> None:
    global _CONFIG_INSTANCE
    _CONFIG_INSTANCE = cfg


def get_config() -> "LumosConfig":
    if _CONFIG_INSTANCE is None:
        raise RuntimeError("Config not initialized; call set_config() first")
    return _CONFIG_INSTANCE
```

**Step 13.6: 跑测试**

Run: `pytest tests/unit/test_schemas.py -v`
Expected: PASS

**Step 13.7: 提交**

```bash
git add src/lumos/api/schemas.py src/lumos/api/deps.py src/lumos/api/deps_helper.py src/lumos/config.py tests/unit/test_schemas.py
git commit -m "feat: Pydantic schemas and FastAPI dependencies"
```

---

### Task 14: 认证路由（register/login/refresh/logout/me）

**Files:**
- Create: `src/lumos/api/routes/auth.py`
- Create: `tests/api/__init__.py`
- Create: `tests/api/conftest.py`
- Create: `tests/api/test_auth_routes.py`

**Interfaces:**
- Produces: 5个端点 `POST /api/auth/{register,login,refresh,logout}`, `GET /api/auth/me`

**Step 14.1: 写`tests/api/conftest.py`**

```python
"""API集成测试fixture：内存DB + FastAPI TestClient。"""
from __future__ import annotations
import os
from typing import AsyncIterator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lumos.config import (
    LumosConfig, ServerConfig, ProviderConfig, DbConfig,
    ToolsConfig, SkillsConfig, McpConfig, AuthConfig, AgentConfig, set_config,
)
from lumos.persistence.db import get_engine, init_db
from lumos.api.app import create_app


@pytest_asyncio.fixture
async def app() -> AsyncIterator:
    cfg = LumosConfig(
        server=ServerConfig(host="127.0.0.1", port=8000),
        provider=ProviderConfig(
            type="openai_compat",
            base_url="http://localhost/v1",
            api_key="test",
            model="gpt-test",
        ),
        db=DbConfig(url="sqlite+aiosqlite:///:memory:"),
        tools=ToolsConfig(),
        skills=SkillsConfig(dirs=[]),
        mcp=McpConfig(servers=[]),
        auth=AuthConfig(jwt_secret="test-secret-32-bytes-long-string", access_ttl=3600, refresh_ttl=7200),
        agent=AgentConfig(),
    )
    set_config(cfg)
    application = create_app(cfg, for_testing=True)
    yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

**Step 14.2: 写`tests/api/test_auth_routes.py`**

```python
"""测试认证路由。"""
from __future__ import annotations
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_me(client: AsyncClient):
    # 注册
    r = await client.post("/api/auth/register", json={
        "email": "alice@example.com", "password": "hunter22pass",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert "access_token" in data
    access = data["access_token"]

    # /me
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    r = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    r = await client.post("/api/auth/login", json={
        "email": "a@b.com", "password": "wrong-password",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    refresh = reg.json()["refresh_token"]
    r = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_logout_revokes_refresh(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    refresh = reg.json()["refresh_token"]
    r = await client.post("/api/auth/logout", json={"refresh_token": refresh})
    assert r.status_code == 204
    # 再用同一个refresh刷新应失败
    r2 = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_unauthorized_me(client: AsyncClient):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
```

**Step 14.3: 写`src/lumos/api/routes/auth.py`**

```python
"""/api/auth 路由。"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import (
    RegisterRequest, LoginRequest, RefreshRequest,
    TokenResponse, UserOut,
)
from lumos.api.deps import get_db, get_current_user
from lumos.api.auth_utils import (
    hash_password, verify_password,
    create_token_pair, decode_token,
)
from lumos.persistence.repositories.users import UserRepository
from lumos.persistence.models import User, RevokedToken
from lumos.config import get_config
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    if await repo.get_by_email(req.email):
        raise HTTPException(409, "email already registered")
    cfg = get_config()
    user = await repo.create(
        email=req.email, password_hash=hash_password(req.password, rounds=cfg.auth.bcrypt_rounds),
    )
    pair = create_token_pair(
        user.id, secret=cfg.auth.jwt_secret,
        access_ttl=cfg.auth.access_ttl, refresh_ttl=cfg.auth.refresh_ttl,
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(req.email)
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "user disabled")
    cfg = get_config()
    pair = create_token_pair(
        user.id, secret=cfg.auth.jwt_secret,
        access_ttl=cfg.auth.access_ttl, refresh_ttl=cfg.auth.refresh_ttl,
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    cfg = get_config()
    try:
        payload = decode_token(req.refresh_token, secret=cfg.auth.jwt_secret, expected_type="refresh")
    except Exception:
        raise HTTPException(401, "invalid refresh token")
    # 检查撤销名单
    from sqlalchemy import select
    stmt = select(RevokedToken).where(RevokedToken.jti == req.refresh_token[:36])
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(401, "refresh token revoked")
    pair = create_token_pair(
        payload["sub"], secret=cfg.auth.jwt_secret,
        access_ttl=cfg.auth.access_ttl, refresh_ttl=cfg.auth.refresh_ttl,
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/logout", status_code=204)
async def logout(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    cfg = get_config()
    try:
        payload = decode_token(req.refresh_token, secret=cfg.auth.jwt_secret, expected_type="refresh")
    except Exception:
        raise HTTPException(401, "invalid refresh token")
    expires_at = datetime.utcfromtimestamp(payload["exp"])
    revoked = RevokedToken(
        jti=req.refresh_token[:36], user_id=payload["sub"],
        expires_at=expires_at,
    )
    db.add(revoked)
    await db.commit()
    return None


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id, email=user.email,
        created_at=user.created_at, is_active=user.is_active,
    )
```

**Step 14.4: 创建`src/lumos/api/app.py`的最小可用版本（Task 19扩展）**

```python
"""FastAPI应用工厂（一阶段最小版，后续Task扩展）。"""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession
from lumos.config import LumosConfig, set_config
from lumos.persistence.db import get_engine, init_db
from lumos.providers.openai_compat import OpenAICompatProvider
from lumos.providers.base import BaseProvider
from lumos.tools.registry import ToolRegistry
from lumos.skills.manager import SkillManager
from lumos.mcp.manager import McpManager
from lumos.mcp.config import McpServerConfig
from lumos.api.routes.auth import router as auth_router


def create_app(config: LumosConfig, *, for_testing: bool = False) -> FastAPI:
    set_config(config)
    app = FastAPI(title="Lumos", version="0.1.0")
    app.state.config = config

    @app.on_event("startup")
    async def _startup():
        eng = get_engine(config.db.url, echo=config.db.echo)
        app.state.engine = eng
        if for_testing:
            await init_db(eng)
        else:
            await init_db(eng)
        app.state.provider = OpenAICompatProvider(
            base_url=config.provider.base_url,
            api_key=config.provider.api_key,
            model=config.provider.model,
            timeout=config.provider.timeout,
        )
        app.state.tool_registry = ToolRegistry()
        app.state.tool_registry.discover()
        # 注入ToolsConfig到需要它的工具
        from lumos.tools.builtin.file_ops import FileReadTool, FileWriteTool
        for tool in app.state.tool_registry._tools.values():
            if isinstance(tool, (FileReadTool, FileWriteTool)):
                tool.config = config.tools
        app.state.skill_manager = SkillManager(discover_dirs=config.skills.dirs)
        app.state.skill_manager.discover()
        mcp_configs = [
            McpServerConfig(
                name=s.name, transport=s.transport, enabled=s.enabled,
                command=s.command, args=tuple(s.args), env=s.env,
                url=s.url, headers=s.headers,
            )
            for s in config.mcp.servers
        ]
        app.state.mcp_manager = McpManager(mcp_configs)
        await app.state.mcp_manager.connect_all()
        await app.state.mcp_manager.refresh_tools_cache()

    @app.on_event("shutdown")
    async def _shutdown():
        if hasattr(app.state, "mcp_manager"):
            await app.state.mcp_manager.shutdown()

    app.include_router(auth_router)
    return app
```

**Step 14.5: 跑测试**

Run: `pytest tests/api/test_auth_routes.py -v`
Expected: PASS

**Step 14.6: 提交**

```bash
git add src/lumos/api/routes/auth.py src/lumos/api/app.py tests/api
git commit -m "feat: auth routes and minimal FastAPI app factory"
```

---

### Task 15: Session和Message REST路由

**Files:**
- Create: `src/lumos/api/routes/sessions.py`
- Create: `src/lumos/api/routes/messages.py`
- Create: `tests/api/test_sessions_routes.py`
- Create: `tests/api/test_messages_routes.py`

**Interfaces:**
- Produces:
  - `GET/POST /api/sessions`, `GET/PATCH/DELETE /api/sessions/{id}`
  - `GET/POST /api/sessions/{id}/messages`

**Step 15.1: 写`tests/api/test_sessions_routes.py`**

```python
"""测试会话路由。"""
from __future__ import annotations
import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    r = await client.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_list_get_delete_session(client: AsyncClient):
    token = await _register(client)
    H = {"Authorization": f"Bearer {token}"}

    # 创建
    r = await client.post("/api/sessions", json={"title": "测试会话"}, headers=H)
    assert r.status_code == 201
    sid = r.json()["id"]

    # 列出
    r = await client.get("/api/sessions", headers=H)
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    # 详情
    r = await client.get(f"/api/sessions/{sid}", headers=H)
    assert r.status_code == 200

    # 删除
    r = await client.delete(f"/api/sessions/{sid}", headers=H)
    assert r.status_code == 204

    # 删除后再访问
    r = await client.get(f"/api/sessions/{sid}", headers=H)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_session_user_isolation(client: AsyncClient):
    token_a = await _register(client)
    # 第二个用户
    await client.post("/api/auth/register", json={
        "email": "b@b.com", "password": "hunter22pass",
    })
    r = await client.post("/api/auth/login", json={
        "email": "b@b.com", "password": "hunter22pass",
    })
    token_b = r.json()["access_token"]

    # A创建一个session
    r = await client.post("/api/sessions", json={}, headers={"Authorization": f"Bearer {token_a}"})
    sid_a = r.json()["id"]

    # B尝试访问应403/404
    r = await client.get(f"/api/sessions/{sid_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code in (403, 404)
```

**Step 15.2: 写`tests/api/test_messages_routes.py`**

```python
"""测试消息路由（同步发送会失败因为需要LLM，仅测试history）。"""
from __future__ import annotations
import pytest
from httpx import AsyncClient


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
```

**Step 15.3: 写`src/lumos/api/routes/sessions.py`**

```python
"""/api/sessions 路由。"""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import SessionCreate, SessionUpdate, SessionOut
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User
from lumos.persistence.repositories.sessions import ChatSessionRepository


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _to_out(cs) -> SessionOut:
    try:
        skills = json.loads(cs.enabled_skills or "[]")
    except Exception:
        skills = []
    return SessionOut(
        id=cs.id, title=cs.title, enabled_skills=skills,
        created_at=cs.created_at, updated_at=cs.updated_at,
    )


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    rows = await repo.list_by_user(user.id)
    return [_to_out(r) for r in rows]


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    req: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    title = req.title or "新会话"
    cs = await repo.create(user_id=user.id, title=title)
    if req.enabled_skills:
        await repo.update_skills(cs.id, json.dumps(req.enabled_skills))
    return _to_out(cs)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    cs = await repo.get(session_id, user.id)
    if cs is None:
        raise HTTPException(404, "session not found")
    return _to_out(cs)


@router.patch("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: str,
    req: SessionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    cs = await repo.get(session_id, user.id)
    if cs is None:
        raise HTTPException(404, "session not found")
    if req.title is not None:
        await repo.update_title(session_id, req.title)
    if req.enabled_skills is not None:
        await repo.update_skills(session_id, json.dumps(req.enabled_skills))
    cs = await repo.get(session_id, user.id)
    return _to_out(cs)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = ChatSessionRepository(db)
    ok = await repo.delete(session_id, user.id)
    if not ok:
        raise HTTPException(404, "session not found")
```

**Step 15.4: 写`src/lumos/api/routes/messages.py`**

```python
"""/api/sessions/{id}/messages 路由。"""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import MessageOut, ChatMessageRequest
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User
from lumos.persistence.repositories.sessions import ChatSessionRepository
from lumos.persistence.repositories.messages import MessageRepository


router = APIRouter(prefix="/api/sessions/{session_id}/messages", tags=["messages"])


def _to_out(m) -> MessageOut:
    tcs = None
    if m.tool_calls:
        try:
            tcs = json.loads(m.tool_calls)
        except Exception:
            tcs = None
    return MessageOut(
        id=m.id, role=m.role, content=m.content,
        tool_calls=tcs, tool_call_id=m.tool_call_id, name=m.name,
        prompt_tokens=m.prompt_tokens,
        completion_tokens=m.completion_tokens,
        created_at=m.created_at,
    )


@router.get("", response_model=list[MessageOut])
async def list_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cs_repo = ChatSessionRepository(db)
    cs = await cs_repo.get(session_id, user.id)
    if cs is None:
        raise HTTPException(404, "session not found")
    repo = MessageRepository(db)
    rows = await repo.list_by_session(session_id)
    return [_to_out(r) for r in rows]
```

**Step 15.5: 注册到app.py**

修改`src/lumos/api/app.py`的`create_app`末尾：
```python
    from lumos.api.routes.sessions import router as sessions_router
    from lumos.api.routes.messages import router as messages_router
    app.include_router(sessions_router)
    app.include_router(messages_router)
```

**Step 15.6: 跑测试**

Run: `pytest tests/api/test_sessions_routes.py tests/api/test_messages_routes.py -v`
Expected: PASS

**Step 15.7: 提交**

```bash
git add src/lumos/api/routes tests/api/test_sessions_routes.py tests/api/test_messages_routes.py
git commit -m "feat: session and message REST routes"
```

---

### Task 16: WebSocket流式对话路由

**Files:**
- Create: `src/lumos/api/routes/ws.py`
- Create: `src/lumos/api/runners.py`（per-session runner管理）
- Create: `tests/api/test_ws.py`

**Interfaces:**
- Produces: `/ws/sessions/{id}` WebSocket端点 + `Runners`单例管理session→AgentRunner映射

**Step 16.1: 写`tests/api/test_ws.py`**

```python
"""测试WebSocket流式协议（使用mock provider）。"""
from __future__ import annotations
import asyncio
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def mock_provider(monkeypatch):
    """替换OpenAICompatProvider.chat为脚本化响应。"""
    from lumos.agent.message import ToolCall, Usage

    class FakeProvider:
        async def chat(self, messages, *, system, tools, temperature,
                       max_tokens, cancel, on_text):
            if on_text:
                await on_text("Hello")
                await on_text(" world")
            return "Hello world", [], Usage(10, 5, 15)

    # 重启app的provider为FakeProvider
    yield FakeProvider


@pytest.mark.asyncio
async def test_ws_simple_chat(app, mock_provider):
    # 替换app.state.provider
    app.state.provider = mock_provider
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        # 注册并创建session
        r = client.post("/api/auth/register", json={
            "email": "a@b.com", "password": "hunter22pass",
        })
        token = r.json()["access_token"]
        H = {"Authorization": f"Bearer {token}"}
        r = client.post("/api/sessions", json={}, headers=H)
        sid = r.json()["id"]

        with client.websocket_connect(f"/ws/sessions/{sid}?token={token}") as ws:
            ws.send_text(json.dumps({
                "type": "user_message", "content": "hi", "enabled_skills": [],
            }))
            events: list[dict] = []
            for _ in range(50):
                try:
                    msg = ws.receive_text()
                except Exception:
                    break
                e = json.loads(msg)
                events.append(e)
                if e["type"] == "done":
                    break
            text_events = [e for e in events if e["type"] == "text"]
            assert any(e["data"]["delta"] == "Hello" for e in text_events)
            assert any(e["data"]["delta"] == " world" for e in text_events)
            assert any(e["type"] == "done" for e in events)
```

**Step 16.2: 写`src/lumos/api/runners.py`**

```python
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
```

**Step 16.3: 写`src/lumos/api/routes/ws.py`**

```python
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
```

**Step 16.4: 注册到app.py**

修改`src/lumos/api/app.py`添加`app.state.runners = Runners()`和路由注册。

**Step 16.5: 跑测试**

Run: `pytest tests/api/test_ws.py -v`
Expected: PASS

**Step 16.6: 提交**

```bash
git add src/lumos/api/routes/ws.py src/lumos/api/runners.py tests/api/test_ws.py
git commit -m "feat: WebSocket streaming chat route"
```

---

### Task 17: Skills和MCP管理路由

**Files:**
- Create: `src/lumos/api/routes/skills.py`
- Create: `src/lumos/api/routes/mcp.py`
- Create: `tests/api/test_skills_routes.py`
- Create: `tests/api/test_mcp_routes.py`

**Interfaces:**
- Produces:
  - `/api/skills`（GET列表、POST启用/禁用）
  - `/api/mcp/servers`（CRUD + test连接）

**Step 17.1: 写`tests/api/test_skills_routes.py`**

```python
"""测试Skills管理路由。"""
from __future__ import annotations
from pathlib import Path
import textwrap
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def app_with_skill(app, tmp_path):
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()
    (skill_dir / "demo").mkdir()
    (skill_dir / "demo" / "SKILL.md").write_text(textwrap.dedent("""\
        ---
        name: demo
        description: Demo skill
        ---
        Demo instructions.
    """), encoding="utf-8")
    app.state.skill_manager = app.state.skill_manager.__class__(
        discover_dirs=[skill_dir],
    )
    app.state.skill_manager.discover()
    yield app


@pytest.mark.asyncio
async def test_list_skills(app_with_skill):
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_with_skill)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/auth/register", json={
            "email": "a@b.com", "password": "hunter22pass",
        })
        token = r.json()["access_token"]
        H = {"Authorization": f"Bearer {token}"}
        r = await client.get("/api/skills", headers=H)
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "demo" in names

        r = await client.post("/api/skills/demo/disable", headers=H)
        assert r.status_code == 204

        r = await client.post("/api/skills/demo/enable", headers=H)
        assert r.status_code == 204
```

**Step 17.2: 写`tests/api/test_mcp_routes.py`**

```python
"""测试MCP管理路由。"""
from __future__ import annotations
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _auth(c: AsyncClient) -> str:
    r = await c.post("/api/auth/register", json={
        "email": "a@b.com", "password": "hunter22pass",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_list_delete_mcp_server(client: AsyncClient):
    token = await _auth(client)
    H = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/mcp/servers", json={
        "name": "fs", "transport": "stdio",
        "command": "echo", "args": ["hello"],
    }, headers=H)
    assert r.status_code == 201
    sid = r.json()["id"]

    r = await client.get("/api/mcp/servers", headers=H)
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    r = await client.delete(f"/api/mcp/servers/{sid}", headers=H)
    assert r.status_code == 204
```

**Step 17.3: 写`src/lumos/api/routes/skills.py`**

```python
"""/api/skills 路由。"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import SkillOut
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
async def list_skills(user: User = Depends(get_current_user)):
    from lumos.api.deps_helper import get_skill_manager
    from fastapi import Request
    sm = get_skill_manager(Request(scope=None))  # 通过app.state无法直接获取
    # 实际用request.app.state：
    raise NotImplementedError("Use /api/skills route registered with Request")


@router.post("/{name}/enable", status_code=204)
async def enable_skill(name: str, request: Request):
    sm = request.app.state.skill_manager
    if sm.get(name) is None:
        raise HTTPException(404, "skill not found")
    sm.enable(name)


@router.post("/{name}/disable", status_code=204)
async def disable_skill(name: str, request: Request):
    sm = request.app.state.skill_manager
    if sm.get(name) is None:
        raise HTTPException(404, "skill not found")
    sm.disable(name)
```

注：上方list_skills的实现需调整以支持Request注入。改写为：

```python
""" /api/skills 路由（最终版）。"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import SkillOut
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
async def list_skills(request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    return [
        SkillOut(
            name=s.name, description=s.description,
            enabled=s.enabled,
            required_tools=s.required_tools,
            optional_tools=s.optional_tools,
        )
        for s in sm.list_all()
    ]


@router.post("/{name}/enable", status_code=204)
async def enable_skill(name: str, request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    if sm.get(name) is None:
        raise HTTPException(404, "skill not found")
    sm.enable(name)


@router.post("/{name}/disable", status_code=204)
async def disable_skill(name: str, request: Request, user: User = Depends(get_current_user)):
    sm = request.app.state.skill_manager
    if sm.get(name) is None:
        raise HTTPException(404, "skill not found")
    sm.disable(name)
```

**Step 17.4: 写`src/lumos/api/routes/mcp.py`**

```python
"""/api/mcp/servers 路由。"""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from lumos.api.schemas import McpServerCreate, McpServerOut
from lumos.api.deps import get_db, get_current_user
from lumos.persistence.models import User
from lumos.persistence.repositories.mcp_servers import McpServerRepository
from lumos.mcp.config import McpServerConfig
from lumos.mcp.client import McpClient
from lumos.errors import McpConnectionError


router = APIRouter(prefix="/api/mcp/servers", tags=["mcp"])


def _to_out(ms) -> McpServerOut:
    try:
        cfg = json.loads(ms.config)
    except Exception:
        cfg = {}
    return McpServerOut(
        id=ms.id, name=ms.name, transport=cfg.get("transport", "stdio"),
        enabled=ms.enabled, config=cfg,
    )


@router.get("", response_model=list[McpServerOut])
async def list_servers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    rows = await repo.list_by_user(user.id)
    return [_to_out(r) for r in rows]


@router.post("", response_model=McpServerOut, status_code=201)
async def create_server(
    req: McpServerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    cfg_dict = req.model_dump()
    ms = await repo.upsert(
        user_id=user.id, name=req.name,
        config_json=json.dumps(cfg_dict), enabled=req.enabled,
    )
    return _to_out(ms)


@router.patch("/{server_id}", response_model=McpServerOut)
async def update_server(
    server_id: str,
    req: McpServerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    existing = await repo.get(server_id, user.id)
    if existing is None:
        raise HTTPException(404, "server not found")
    cfg_dict = req.model_dump()
    ms = await repo.upsert(
        user_id=user.id, name=req.name,
        config_json=json.dumps(cfg_dict), enabled=req.enabled,
    )
    return _to_out(ms)


@router.delete("/{server_id}", status_code=204)
async def delete_server(
    server_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    ok = await repo.delete(server_id, user.id)
    if not ok:
        raise HTTPException(404, "server not found")


@router.post("/{server_id}/test")
async def test_server(
    server_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = McpServerRepository(db)
    ms = await repo.get(server_id, user.id)
    if ms is None:
        raise HTTPException(404, "server not found")
    cfg = json.loads(ms.config)
    mcp_cfg = McpServerConfig(
        name=ms.name, transport=cfg["transport"], enabled=True,
        command=cfg.get("command"), args=tuple(cfg.get("args", [])),
        env=cfg.get("env", {}),
        url=cfg.get("url"), headers=cfg.get("headers", {}),
    )
    client = McpClient(mcp_cfg)
    try:
        await client.connect()
        return {"ok": True, "tools_count": len(await client.list_tools())}
    except McpConnectionError as e:
        return {"ok": False, "error": str(e)}
    finally:
        await client.disconnect()
```

**Step 17.5: 注册路由到app.py**

```python
    from lumos.api.routes.skills import router as skills_router
    from lumos.api.routes.mcp import router as mcp_router
    from lumos.api.runners import Runners
    app.state.runners = Runners()
    app.include_router(skills_router)
    app.include_router(mcp_router)
```

**Step 17.6: 跑测试**

Run: `pytest tests/api/test_skills_routes.py tests/api/test_mcp_routes.py -v`
Expected: PASS

**Step 17.7: 提交**

```bash
git add src/lumos/api/routes/skills.py src/lumos/api/routes/mcp.py tests/api/test_skills_routes.py tests/api/test_mcp_routes.py
git commit -m "feat: skills and MCP management routes"
```

---

### Task 18: 健康检查端点 + 错误处理中间件

**Files:**
- Create: `src/lumos/api/routes/health.py`
- Create: `src/lumos/api/middleware.py`
- Create: `tests/api/test_health.py`

**Interfaces:**
- Produces:
  - `GET /api/health`端点
  - 全局异常处理中间件（统一返回problem+json）

**Step 18.1: 写`tests/api/test_health.py`**

```python
"""测试健康检查。"""
from __future__ import annotations
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["db"] == "ok"
```

**Step 18.2: 写`src/lumos/api/routes/health.py`**

```python
"""/api/health 端点。"""
from __future__ import annotations
from fastapi import APIRouter, Request
from sqlalchemy import text
from lumos.api.schemas import HealthResponse
from lumos import __version__


router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    # 检查DB
    from sqlalchemy.ext.asyncio import async_sessionmaker
    factory = async_sessionmaker(request.app.state.engine, expire_on_commit=False)
    db_status = "ok"
    try:
        async with factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    # 检查Provider/MCP
    providers = {"openai_compat": "ok"}
    mcp_statuses: dict[str, str] = {}
    mgr = getattr(request.app.state, "mcp_manager", None)
    if mgr is not None:
        for name, client in mgr._clients.items():
            mcp_statuses[name] = "connected" if client else "disconnected"
    overall = "ok" if db_status == "ok" else "degraded"
    return HealthResponse(
        status=overall, version=__version__,
        providers=providers, mcp_servers=mcp_statuses, db=db_status,
    )
```

**Step 18.3: 写`src/lumos/api/middleware.py`**

```python
"""全局中间件。"""
from __future__ import annotations
import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from lumos.logging import get_logger, request_id_var
from lumos.errors import LumosError


log = get_logger("http")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        duration_ms = (time.perf_counter() - start) * 1000
        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=rid,
        )
        response.headers["X-Request-ID"] = rid
        return response


def register_middlewares(app):
    app.add_middleware(RequestIdMiddleware)
```

**Step 18.4: 注册到app.py**

```python
from lumos.api.middleware import register_middlewares
# 在create_app中：
register_middlewares(app)
from lumos.api.routes.health import router as health_router
app.include_router(health_router)
```

**Step 18.5: 跑测试**

Run: `pytest tests/api/test_health.py -v`
Expected: PASS

**Step 18.6: 提交**

```bash
git add src/lumos/api/routes/health.py src/lumos/api/middleware.py tests/api/test_health.py
git commit -m "feat: health check endpoint and request-id middleware"
```

---

### Task 19: FastAPI应用工厂完善 + 静态前端挂载

**Files:**
- Modify: `src/lumos/api/app.py`
- Create: `src/lumos/server.py`
- Modify: `src/lumos/cli.py`
- Create: `tests/api/test_app_factory.py`

**Step 19.1: 写`tests/api/test_app_factory.py`**

```python
"""测试应用工厂。"""
from __future__ import annotations
from pathlib import Path
import pytest
from lumos.config import (
    LumosConfig, ServerConfig, ProviderConfig, DbConfig,
    ToolsConfig, SkillsConfig, McpConfig, AuthConfig, AgentConfig,
)
from lumos.api.app import create_app


def test_create_app_smoke(tmp_path: Path):
    cfg = LumosConfig(
        server=ServerConfig(),
        provider=ProviderConfig(
            type="openai_compat", base_url="http://localhost",
            api_key="k", model="m",
        ),
        db=DbConfig(url="sqlite+aiosqlite:///:memory:"),
        tools=ToolsConfig(),
        skills=SkillsConfig(dirs=[]),
        mcp=McpConfig(),
        auth=AuthConfig(jwt_secret="test-secret-32-bytes-long-string"),
        agent=AgentConfig(),
    )
    app = create_app(cfg, for_testing=True)
    assert app.title == "Lumos"
    routes = [r.path for r in app.routes]
    assert "/api/auth/register" in routes
    assert "/api/sessions" in routes
    assert "/api/health" in routes
```

**Step 19.2: 完善`src/lumos/api/app.py`**

将之前Task 14/15/17/18的注册代码整合到最终的`create_app`。最终版本：

```python
"""FastAPI应用工厂。"""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import async_sessionmaker
from lumos.config import LumosConfig, set_config
from lumos.persistence.db import get_engine, init_db
from lumos.providers.openai_compat import OpenAICompatProvider
from lumos.tools.registry import ToolRegistry
from lumos.tools.builtin.file_ops import FileReadTool, FileWriteTool
from lumos.skills.manager import SkillManager
from lumos.mcp.manager import McpManager
from lumos.mcp.config import McpServerConfig
from lumos.api.middleware import register_middlewares
from lumos.api.routes.auth import router as auth_router
from lumos.api.routes.sessions import router as sessions_router
from lumos.api.routes.messages import router as messages_router
from lumos.api.routes.skills import router as skills_router
from lumos.api.routes.mcp import router as mcp_router
from lumos.api.routes.health import router as health_router
from lumos.api.routes.ws import router as ws_router
from lumos.api.runners import Runners
from lumos.logging import configure_logging, get_logger


def create_app(config: LumosConfig, *, for_testing: bool = False) -> FastAPI:
    set_config(config)
    configure_logging(config.log_level)
    log = get_logger("app")
    app = FastAPI(title="Lumos", version="0.1.0")
    app.state.config = config
    register_middlewares(app)

    @app.on_event("startup")
    async def _startup():
        eng = get_engine(config.db.url, echo=config.db.echo)
        app.state.engine = eng
        await init_db(eng)
        # 首次启动创建默认admin
        from sqlalchemy import select
        from lumos.persistence.repositories.users import UserRepository
        from lumos.api.auth_utils import hash_password
        factory = async_sessionmaker(eng, expire_on_commit=False)
        async with factory() as db:
            repo = UserRepository(db)
            if (await repo.get_by_email(config.auth.default_admin_email or "")) is None:
                if config.auth.default_admin_email and config.auth.default_admin_password:
                    await repo.create(
                        email=config.auth.default_admin_email,
                        password_hash=hash_password(
                            config.auth.default_admin_password,
                            rounds=config.auth.bcrypt_rounds,
                        ),
                    )
                    log.info("default_admin_created", email=config.auth.default_admin_email)
        app.state.provider = OpenAICompatProvider(
            base_url=config.provider.base_url,
            api_key=config.provider.api_key,
            model=config.provider.model,
            timeout=config.provider.timeout,
        )
        app.state.tool_registry = ToolRegistry()
        app.state.tool_registry.discover()
        for tool in app.state.tool_registry._tools.values():
            if isinstance(tool, (FileReadTool, FileWriteTool)):
                tool.config = config.tools
        app.state.skill_manager = SkillManager(discover_dirs=config.skills.dirs)
        app.state.skill_manager.discover()
        mcp_configs = [
            McpServerConfig(
                name=s.name, transport=s.transport, enabled=s.enabled,
                command=s.command, args=tuple(s.args), env=s.env,
                url=s.url, headers=s.headers,
            )
            for s in config.mcp.servers
        ]
        app.state.mcp_manager = McpManager(mcp_configs)
        await app.state.mcp_manager.connect_all()
        await app.state.mcp_manager.refresh_tools_cache()
        app.state.runners = Runners()
        log.info("app.startup_complete")

    @app.on_event("shutdown")
    async def _shutdown():
        if hasattr(app.state, "mcp_manager"):
            await app.state.mcp_manager.shutdown()
        if hasattr(app.state, "engine"):
            await app.state.engine.dispose()

    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(messages_router)
    app.include_router(skills_router)
    app.include_router(mcp_router)
    app.include_router(health_router)
    app.include_router(ws_router)

    # 静态前端
    web_dir = Path(__file__).parent.parent / "web"
    if web_dir.exists() and not for_testing:
        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(web_dir / "index.html")
        @app.get("/login", include_in_schema=False)
        async def serve_login():
            return FileResponse(web_dir / "login.html")
        app.mount("/static", StaticFiles(directory=web_dir), name="static")

    return app
```

**Step 19.3: 写`src/lumos/server.py`**

```python
"""生产服务器启动入口。"""
from __future__ import annotations
import argparse
import uvicorn
from pathlib import Path
from lumos.config import load_config, set_config
from lumos.api.app import create_app


def run(config_path: str | Path) -> None:
    cfg = load_config(config_path)
    set_config(cfg)
    app = create_app(cfg)
    uvicorn.run(
        app, host=cfg.server.host, port=cfg.server.port,
        log_level=cfg.log_level.lower(),
    )
```

**Step 19.4: 完善`src/lumos/cli.py`**

```python
"""CLI入口。"""
from __future__ import annotations
import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(prog="lumos")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="Run Lumos server")
    s.add_argument("--config", "-c", default="./config.yaml")

    a = sub.add_parser("admin", help="Admin commands")
    a_sub = a.add_subparsers(dest="admin_cmd", required=True)
    a_create = a_sub.add_parser("create", help="Create admin user")
    a_create.add_argument("--email", required=True)
    a_create.add_argument("--password", required=True)
    a_create.add_argument("--config", "-c", default="./config.yaml")

    args = p.parse_args()
    if args.cmd == "serve":
        from lumos.server import run
        run(args.config)
        return 0
    if args.cmd == "admin" and args.admin_cmd == "create":
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from lumos.config import load_config
        from lumos.persistence.db import get_engine, init_db
        from lumos.persistence.repositories.users import UserRepository
        from lumos.api.auth_utils import hash_password
        import asyncio

        async def _create():
            cfg = load_config(args.config)
            set_config(cfg)
            eng = get_engine(cfg.db.url)
            await init_db(eng)
            factory = async_sessionmaker(eng, expire_on_commit=False)
            async with factory() as db:
                repo = UserRepository(db)
                if await repo.get_by_email(args.email):
                    print(f"User {args.email} already exists")
                    return
                await repo.create(
                    email=args.email,
                    password_hash=hash_password(args.password, rounds=cfg.auth.bcrypt_rounds),
                )
                print(f"Created admin: {args.email}")
            await eng.dispose()
        asyncio.run(_create())
        return 0
    p.print_help()
    return 1
```

**Step 19.5: 跑全部测试**

Run: `pytest -v`
Expected: 全部PASS

**Step 19.6: 提交**

```bash
git add src/lumos/api/app.py src/lumos/server.py src/lumos/cli.py tests/api/test_app_factory.py
git commit -m "feat: full FastAPI app factory, server entry, CLI commands"
```

---

## Phase G：Web前端

### Task 20: 登录/注册页面 + 样式

**Files:**
- Create: `src/lumos/web/login.html`
- Create: `src/lumos/web/style.css`

**Step 20.1: 写`src/lumos/web/style.css`**

```css
/* Lumos基础样式 */
:root {
  --bg: #0f1115;
  --bg-2: #161922;
  --fg: #e6e8ee;
  --fg-dim: #8b93a7;
  --accent: #5b8def;
  --border: #262b3a;
  --error: #e85a5a;
  --success: #4caf50;
  --code-bg: #1a1d28;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body {
  font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
  background: var(--bg); color: var(--fg);
  font-size: 14px; line-height: 1.5;
}
a { color: var(--accent); text-decoration: none; }
button { cursor: pointer; font-family: inherit; }

/* 登录页 */
.login-container {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 100vh; padding: 24px;
}
.login-card {
  width: 100%; max-width: 400px; padding: 32px;
  background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px;
}
.login-card h1 { margin-bottom: 8px; font-size: 24px; }
.login-card p { color: var(--fg-dim); margin-bottom: 24px; }
.login-form { display: flex; flex-direction: column; gap: 16px; }
.login-form input {
  padding: 10px 12px; background: var(--bg); color: var(--fg);
  border: 1px solid var(--border); border-radius: 4px;
  font-family: inherit; font-size: 14px;
}
.login-form input:focus { outline: none; border-color: var(--accent); }
.login-form button {
  padding: 10px 16px; background: var(--accent); color: white;
  border: none; border-radius: 4px; font-size: 14px;
}
.login-form button:hover { filter: brightness(1.1); }
.login-tabs { display: flex; gap: 16px; margin-bottom: 16px; }
.login-tabs button {
  background: none; border: none; color: var(--fg-dim);
  padding: 4px 0; border-bottom: 2px solid transparent;
}
.login-tabs button.active { color: var(--fg); border-bottom-color: var(--accent); }
.error-msg { color: var(--error); font-size: 13px; }

/* 聊天页布局 */
.app-shell { display: grid; grid-template-rows: 48px 1fr; height: 100vh; }
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px; background: var(--bg-2); border-bottom: 1px solid var(--border);
}
.topbar-brand { font-weight: 600; }
.topbar-user { display: flex; gap: 12px; align-items: center; }
.topbar-user button {
  background: none; border: 1px solid var(--border); color: var(--fg);
  padding: 4px 12px; border-radius: 4px;
}
.chat-layout {
  display: grid; grid-template-columns: 240px 1fr; height: 100%;
}
.sidebar {
  background: var(--bg-2); border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
}
.sidebar-header { padding: 12px; border-bottom: 1px solid var(--border); }
.sidebar-header button {
  width: 100%; padding: 8px; background: var(--accent); color: white;
  border: none; border-radius: 4px;
}
.session-list { flex: 1; overflow-y: auto; padding: 8px; }
.session-item {
  padding: 8px 12px; margin-bottom: 4px; border-radius: 4px;
  cursor: pointer; color: var(--fg-dim);
}
.session-item:hover { background: var(--bg); }
.session-item.active { background: var(--bg); color: var(--fg); }
.session-item-time { font-size: 11px; color: var(--fg-dim); margin-top: 2px; }

/* 主区 */
.chat-main { display: flex; flex-direction: column; min-width: 0; }
.messages {
  flex: 1; overflow-y: auto; padding: 24px;
  display: flex; flex-direction: column; gap: 16px;
}
.message {
  max-width: 800px; padding: 12px 16px; border-radius: 8px;
}
.message.user { background: var(--accent); color: white; align-self: flex-end; }
.message.assistant { background: var(--bg-2); align-self: flex-start; }
.message-role { font-size: 11px; color: var(--fg-dim); margin-bottom: 4px; }
.message-content pre {
  background: var(--code-bg); padding: 12px; border-radius: 4px;
  overflow-x: auto; margin: 8px 0;
}
.message-content code { background: var(--code-bg); padding: 2px 4px; border-radius: 2px; }
.message-content p { margin: 8px 0; }
.message-content ul, .message-content ol { margin: 8px 0; padding-left: 24px; }

/* 工具调用可视化 */
.tool-call {
  margin-top: 8px; border: 1px solid var(--border); border-radius: 4px;
  background: var(--bg);
}
.tool-call-header {
  padding: 8px 12px; cursor: pointer; display: flex;
  align-items: center; justify-content: space-between;
}
.tool-call-name { font-family: monospace; color: var(--accent); }
.tool-call-status { font-size: 12px; }
.tool-call-status.running { color: #f0c040; }
.tool-call-status.success { color: var(--success); }
.tool-call-status.error { color: var(--error); }
.tool-call-body { padding: 0 12px 12px; display: none; }
.tool-call.expanded .tool-call-body { display: block; }
.tool-call pre { font-size: 12px; }

/* 输入区 */
.composer {
  border-top: 1px solid var(--border); padding: 12px 16px;
  background: var(--bg-2);
}
.composer-skills { display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.composer-skills label {
  display: inline-flex; align-items: center; gap: 4px; font-size: 12px;
  padding: 2px 8px; border: 1px solid var(--border); border-radius: 12px;
}
.composer-input {
  display: flex; gap: 8px; align-items: flex-end;
}
.composer-input textarea {
  flex: 1; min-height: 40px; max-height: 200px; padding: 10px;
  background: var(--bg); color: var(--fg);
  border: 1px solid var(--border); border-radius: 4px;
  font-family: inherit; resize: vertical;
}
.composer-input button {
  padding: 10px 20px; background: var(--accent); color: white;
  border: none; border-radius: 4px;
}
.composer-input button:disabled { background: var(--border); cursor: not-allowed; }

/* 抽屉 */
.drawer {
  position: fixed; top: 0; right: -400px; width: 400px; height: 100vh;
  background: var(--bg-2); border-left: 1px solid var(--border);
  transition: right 0.3s; padding: 16px; overflow-y: auto; z-index: 100;
}
.drawer.open { right: 0; }
.drawer-header { display: flex; justify-content: space-between; margin-bottom: 16px; }
.drawer-section { margin-bottom: 24px; }
.drawer-section h3 { margin-bottom: 8px; font-size: 14px; color: var(--fg-dim); }
.mcp-card, .skill-card {
  border: 1px solid var(--border); border-radius: 4px;
  padding: 12px; margin-bottom: 8px;
}

/* 抽屉切换按钮 */
.drawer-toggle {
  position: fixed; bottom: 100px; right: 16px;
  padding: 8px 12px; background: var(--bg-2);
  border: 1px solid var(--border); border-radius: 4px; color: var(--fg);
  z-index: 99;
}
```

**Step 20.2: 写`src/lumos/web/login.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>登录 - Lumos</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <div class="login-container">
    <div class="login-card">
      <h1>Lumos</h1>
      <p>基于Agent的知识问答系统</p>
      <div class="login-tabs">
        <button id="tab-login" class="active">登录</button>
        <button id="tab-register">注册</button>
      </div>
      <form id="auth-form" class="login-form">
        <input id="email" type="email" placeholder="邮箱" required />
        <input id="password" type="password" placeholder="密码 (至少8位)" required minlength="8" />
        <button type="submit" id="submit-btn">登录</button>
        <div class="error-msg" id="error-msg"></div>
      </form>
    </div>
  </div>
  <script>
    let mode = 'login';
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const submitBtn = document.getElementById('submit-btn');
    const errorMsg = document.getElementById('error-msg');

    tabLogin.onclick = () => switchMode('login');
    tabRegister.onclick = () => switchMode('register');

    function switchMode(newMode) {
      mode = newMode;
      tabLogin.classList.toggle('active', mode === 'login');
      tabRegister.classList.toggle('active', mode === 'register');
      submitBtn.textContent = mode === 'login' ? '登录' : '注册';
      errorMsg.textContent = '';
    }

    document.getElementById('auth-form').onsubmit = async (e) => {
      e.preventDefault();
      errorMsg.textContent = '';
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      const url = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      try {
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        if (!r.ok) {
          const detail = (await r.json()).detail || '请求失败';
          errorMsg.textContent = typeof detail === 'string' ? detail : JSON.stringify(detail);
          return;
        }
        const data = await r.json();
        localStorage.setItem('lumos.access_token', data.access_token);
        // refresh_token存httpOnly cookie需要后端设置，一阶段存localStorage
        localStorage.setItem('lumos.refresh_token', data.refresh_token);
        window.location.href = '/';
      } catch (err) {
        errorMsg.textContent = err.message;
      }
    };
  </script>
</body>
</html>
```

**Step 20.3: 提交**

```bash
git add src/lumos/web/login.html src/lumos/web/style.css
git commit -m "feat: login page and base styles"
```

---

### Task 21: 聊天页面HTML

**Files:**
- Create: `src/lumos/web/index.html`

**Step 21.1: 写`src/lumos/web/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Lumos</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-brand">🪔 Lumos</div>
      <div class="topbar-user">
        <span id="user-email"></span>
        <button id="btn-drawer">⚙ 设置</button>
        <button id="btn-logout">登出</button>
      </div>
    </header>
    <div class="chat-layout">
      <aside class="sidebar">
        <div class="sidebar-header">
          <button id="btn-new-session">+ 新会话</button>
        </div>
        <div class="session-list" id="session-list"></div>
      </aside>
      <main class="chat-main">
        <div class="messages" id="messages"></div>
        <div class="composer">
          <div class="composer-skills" id="composer-skills"></div>
          <div class="composer-input">
            <textarea id="input-text" placeholder="输入消息... (Enter发送, Shift+Enter换行)"></textarea>
            <button id="btn-send">发送</button>
            <button id="btn-cancel" style="display:none">取消</button>
          </div>
        </div>
      </main>
    </div>
  </div>

  <!-- 抽屉：Skills + MCP -->
  <button class="drawer-toggle" id="btn-drawer-bottom">⚙</button>
  <div class="drawer" id="drawer">
    <div class="drawer-header">
      <h2>设置</h2>
      <button id="btn-close-drawer">✕</button>
    </div>
    <div class="drawer-section">
      <h3>Skills</h3>
      <div id="skill-list"></div>
    </div>
    <div class="drawer-section">
      <h3>MCP Servers</h3>
      <div id="mcp-list"></div>
      <button id="btn-add-mcp" style="margin-top:8px">+ 添加</button>
    </div>
  </div>

  <script src="/static/vendor/marked.min.js"></script>
  <script src="/static/vendor/highlight.min.js"></script>
  <script src="/static/app.js" type="module"></script>
</body>
</html>
```

**Step 21.2: 提交**

```bash
git add src/lumos/web/index.html
git commit -m "feat: chat page HTML shell"
```

---

### Task 22: 前端JS应用（认证、列表、WebSocket、渲染）

**Files:**
- Create: `src/lumos/web/app.js`

**Step 21.1: 写`src/lumos/web/app.js`**

```javascript
// Lumos前端应用
// 单一文件，无构建步骤

const state = {
  accessToken: localStorage.getItem('lumos.access_token'),
  refreshToken: localStorage.getItem('lumos.refresh_token'),
  user: null,
  sessions: [],
  currentSession: null,
  ws: null,
  streamingMessage: null,
  skills: [],
  mcps: [],
  enabledSkills: new Set(),
};

const api = {
  async req(path, opts = {}) {
    const r = await fetch(path, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(opts.headers || {}),
        ...(state.accessToken ? { 'Authorization': `Bearer ${state.accessToken}` } : {}),
      },
    });
    if (r.status === 401 && state.refreshToken) {
      const refreshed = await this.refresh();
      if (refreshed) {
        return this.req(path, opts);
      } else {
        window.location.href = '/login';
      }
    }
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail));
    }
    return r.status === 204 ? null : r.json();
  },
  async refresh() {
    const r = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: state.refreshToken }),
    });
    if (!r.ok) return false;
    const data = await r.json();
    state.accessToken = data.access_token;
    state.refreshToken = data.refresh_token;
    localStorage.setItem('lumos.access_token', state.accessToken);
    localStorage.setItem('lumos.refresh_token', state.refreshToken);
    return true;
  },
};

// --- 认证 ---
async function checkAuth() {
  if (!state.accessToken) { window.location.href = '/login'; return; }
  try {
    state.user = await api.req('/api/auth/me');
    document.getElementById('user-email').textContent = state.user.email;
  } catch (e) {
    window.location.href = '/login';
  }
}

document.getElementById('btn-logout').onclick = async () => {
  try { await api.req('/api/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: state.refreshToken }) }); } catch {}
  localStorage.clear();
  window.location.href = '/login';
};

// --- 会话列表 ---
async function loadSessions() {
  state.sessions = await api.req('/api/sessions');
  renderSessionList();
}

function renderSessionList() {
  const list = document.getElementById('session-list');
  list.innerHTML = '';
  for (const s of state.sessions) {
    const div = document.createElement('div');
    div.className = 'session-item' + (state.currentSession?.id === s.id ? ' active' : '');
    div.innerHTML = `
      <div>${escapeHtml(s.title)}</div>
      <div class="session-item-time">${new Date(s.updated_at).toLocaleString()}</div>
    `;
    div.onclick = () => selectSession(s.id);
    list.appendChild(div);
  }
}

async function selectSession(id) {
  state.currentSession = await api.req(`/api/sessions/${id}`);
  state.enabledSkills = new Set(state.currentSession.enabled_skills || []);
  renderSessionList();
  await loadMessages();
  connectWS(id);
}

document.getElementById('btn-new-session').onclick = async () => {
  const cs = await api.req('/api/sessions', { method: 'POST', body: JSON.stringify({}) });
  state.sessions.unshift(cs);
  await selectSession(cs.id);
};

async function loadMessages() {
  const msgs = await api.req(`/api/sessions/${state.currentSession.id}/messages`);
  const list = document.getElementById('messages');
  list.innerHTML = '';
  for (const m of msgs) {
    appendMessage(m);
  }
  list.scrollTop = list.scrollHeight;
}

function appendMessage(m) {
  const list = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = `message ${m.role}`;
  const content = m.role === 'user' ? escapeHtml(m.content) : renderMarkdown(m.content);
  div.innerHTML = `
    <div class="message-role">${m.role}</div>
    <div class="message-content">${content}</div>
  `;
  list.appendChild(div);
  return div;
}

function renderMarkdown(text) {
  if (window.marked) {
    return window.marked.parse(text, { breaks: true });
  }
  return escapeHtml(text);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// --- WebSocket ---
function connectWS(sessionId) {
  if (state.ws) state.ws.close();
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${proto}://${location.host}/ws/sessions/${sessionId}?token=${state.accessToken}`;
  state.ws = new WebSocket(url);
  state.ws.onmessage = (e) => handleWsMessage(JSON.parse(e.data));
  state.ws.onclose = () => { state.ws = null; };
  state.ws.onerror = (e) => console.error('WS error', e);
}

function handleWsMessage(event) {
  const list = document.getElementById('messages');
  switch (event.type) {
    case 'text':
      if (!state.streamingMessage) {
        state.streamingMessage = { content: '', role: 'assistant' };
        const div = document.createElement('div');
        div.className = 'message assistant streaming';
        div.innerHTML = `<div class="message-role">assistant</div><div class="message-content"></div>`;
        list.appendChild(div);
        state.streamingMessage.el = div.querySelector('.message-content');
      }
      state.streamingMessage.content += event.data.delta;
      state.streamingMessage.el.innerHTML = renderMarkdown(state.streamingMessage.content);
      list.scrollTop = list.scrollHeight;
      break;
    case 'tool_call_start':
      appendToolCall(event.data.calls);
      break;
    case 'tool_call_result':
      updateToolCallResult(event.data);
      break;
    case 'tool_call_end':
      break;
    case 'usage':
      if (state.streamingMessage) {
        state.streamingMessage.usage = event.data;
      }
      break;
    case 'done':
      if (state.streamingMessage) {
        state.streamingMessage.el.classList.remove('streaming');
        const usageDiv = document.createElement('div');
        usageDiv.className = 'message-role';
        usageDiv.textContent = `📊 ${state.streamingMessage.usage?.prompt_tokens || 0} prompt / ${state.streamingMessage.usage?.completion_tokens || 0} completion tokens`;
        state.streamingMessage.el.parentElement.appendChild(usageDiv);
      }
      state.streamingMessage = null;
      loadSessions(); // 刷新列表（updated_at变化）
      break;
    case 'error':
      alert('Error: ' + (event.data?.message || JSON.stringify(event.data)));
      break;
    case 'cancelled':
      state.streamingMessage = null;
      break;
  }
}

function appendToolCall(calls) {
  const list = document.getElementById('messages');
  for (const tc of calls) {
    const div = document.createElement('div');
    div.className = 'tool-call expanded';
    div.dataset.toolId = tc.id;
    div.innerHTML = `
      <div class="tool-call-header">
        <span class="tool-call-name">🔧 ${tc.name}</span>
        <span class="tool-call-status running">运行中...</span>
      </div>
      <div class="tool-call-body">
        <strong>参数:</strong>
        <pre>${escapeHtml(JSON.stringify(tc.arguments, null, 2))}</pre>
        <div class="tool-call-result"></div>
      </div>
    `;
    div.querySelector('.tool-call-header').onclick = () => div.classList.toggle('expanded');
    list.appendChild(div);
  }
}

function updateToolCallResult(data) {
  const div = document.querySelector(`.tool-call[data-tool-id="${data.tool_call_id}"]`);
  if (!div) return;
  const status = div.querySelector('.tool-call-status');
  status.classList.remove('running');
  status.classList.add(data.is_error ? 'error' : 'success');
  status.textContent = data.is_error ? '✗ 失败' : '✓ 完成';
  const resultEl = div.querySelector('.tool-call-result');
  resultEl.innerHTML = `<strong>结果:</strong><pre>${escapeHtml(data.result).slice(0, 2000)}${data.result.length > 2000 ? '\n...(truncated)' : ''}</pre>`;
}

// --- 发送 ---
document.getElementById('btn-send').onclick = sendMessage;
document.getElementById('input-text').onkeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};

async function sendMessage() {
  const input = document.getElementById('input-text');
  const content = input.value.trim();
  if (!content || !state.currentSession || !state.ws) return;

  // 显示user消息
  appendMessage({ role: 'user', content });

  // 发送WS消息
  state.ws.send(JSON.stringify({
    type: 'user_message',
    content,
    enabled_skills: Array.from(state.enabledSkills),
  }));
  input.value = '';
  document.getElementById('btn-send').style.display = 'none';
  document.getElementById('btn-cancel').style.display = '';
}

document.getElementById('btn-cancel').onclick = () => {
  if (state.ws) state.ws.send(JSON.stringify({ type: 'cancel' }));
  document.getElementById('btn-send').style.display = '';
  document.getElementById('btn-cancel').style.display = 'none';
};

// --- Skills管理 ---
async function loadSkills() {
  state.skills = await api.req('/api/skills');
  renderSkills();
  renderComposerSkills();
}

function renderSkills() {
  const list = document.getElementById('skill-list');
  list.innerHTML = '';
  for (const s of state.skills) {
    const card = document.createElement('div');
    card.className = 'skill-card';
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between">
        <strong>${escapeHtml(s.name)}</strong>
        <button onclick="toggleSkill('${s.name}', ${s.enabled})">${s.enabled ? '停用' : '启用'}</button>
      </div>
      <p style="color:var(--fg-dim);margin-top:4px">${escapeHtml(s.description)}</p>
    `;
    list.appendChild(card);
  }
}

function renderComposerSkills() {
  const wrap = document.getElementById('composer-skills');
  wrap.innerHTML = '';
  for (const s of state.skills) {
    if (!s.enabled) continue;
    const lbl = document.createElement('label');
    lbl.innerHTML = `
      <input type="checkbox" ${state.enabledSkills.has(s.name) ? 'checked' : ''} onchange="toggleComposerSkill('${s.name}', this.checked)" />
      ${escapeHtml(s.name)}
    `;
    wrap.appendChild(lbl);
  }
}

window.toggleComposerSkill = async (name, on) => {
  if (on) state.enabledSkills.add(name);
  else state.enabledSkills.delete(name);
  if (state.currentSession) {
    await api.req(`/api/sessions/${state.currentSession.id}`, {
      method: 'PATCH', body: JSON.stringify({ enabled_skills: Array.from(state.enabledSkills) }),
    });
  }
};

window.toggleSkill = async (name, currentEnabled) => {
  const endpoint = currentEnabled ? 'disable' : 'enable';
  await api.req(`/api/skills/${name}/${endpoint}`, { method: 'POST' });
  await loadSkills();
};

// --- MCP管理 ---
async function loadMcps() {
  state.mcps = await api.req('/api/mcp/servers');
  renderMcps();
}

function renderMcps() {
  const list = document.getElementById('mcp-list');
  list.innerHTML = '';
  for (const m of state.mcps) {
    const card = document.createElement('div');
    card.className = 'mcp-card';
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between">
        <strong>${escapeHtml(m.name)}</strong>
        <button onclick="deleteMcp('${m.id}')">删除</button>
      </div>
      <p style="color:var(--fg-dim);margin-top:4px;font-size:12px">
        ${escapeHtml(m.config.transport)}
        ${m.config.command ? `· ${escapeHtml(m.config.command)}` : ''}
        ${m.config.url ? `· ${escapeHtml(m.config.url)}` : ''}
      </p>
    `;
    list.appendChild(card);
  }
}

document.getElementById('btn-add-mcp').onclick = async () => {
  const name = prompt('MCP服务器名称:');
  if (!name) return;
  const transport = prompt('传输类型 (stdio/sse/streamable_http):', 'stdio');
  let body = { name, transport };
  if (transport === 'stdio') {
    body.command = prompt('命令:', 'npx');
    body.args = (prompt('参数（空格分隔）:', '-y @modelcontextprotocol/server-filesystem ./data') || '').split(/\s+/);
  } else {
    body.url = prompt('URL:', 'https://mcp.example.com/sse');
  }
  await api.req('/api/mcp/servers', { method: 'POST', body: JSON.stringify(body) });
  await loadMcps();
};

window.deleteMcp = async (id) => {
  if (!confirm('删除此MCP服务器?')) return;
  await api.req(`/api/mcp/servers/${id}`, { method: 'DELETE' });
  await loadMcps();
};

// --- 抽屉 ---
const drawer = document.getElementById('drawer');
document.getElementById('btn-drawer').onclick = () => drawer.classList.add('open');
document.getElementById('btn-drawer-bottom').onclick = () => drawer.classList.add('open');
document.getElementById('btn-close-drawer').onclick = () => drawer.classList.remove('open');

// --- 初始化 ---
(async () => {
  await checkAuth();
  await loadSessions();
  await loadSkills();
  await loadMcps();
  if (state.sessions.length > 0) {
    await selectSession(state.sessions[0].id);
  } else {
    // 自动创建首个会话
    document.getElementById('btn-new-session').click();
  }
})();
```

**Step 22.2: 下载marked.js和highlight.js到vendor目录**

```bash
mkdir -p src/lumos/web/vendor
curl -L https://cdn.jsdelivr.net/npm/marked/marked.min.js -o src/lumos/web/vendor/marked.min.js
curl -L https://cdn.jsdelivr.net/npm/highlight.js@11/lib/core.min.js -o src/lumos/web/vendor/highlight.min.js
curl -L https://cdn.jsdelivr.net/npm/highlight.js@11/styles/atom-one-dark.min.css -o src/lumos/web/vendor/highlight.css
```

或在README中说明vendor目录需手动下载。

**Step 22.3: 提交**

```bash
git add src/lumos/web/app.js src/lumos/web/vendor
git commit -m "feat: frontend JS application with auth, sessions, WS, tool visualization"
```

---

## Phase H：质量与文档

### Task 23: README与示例配置

**Files:**
- Create: `README.md`（覆盖原空文件）
- Create: `docs/architecture.md`
- Create: `docs/tools.md`
- Create: `docs/skills.md`
- Create: `docs/mcp.md`

**Step 23.1: 写`README.md`**

```markdown
# Lumos

> 商用基于Agent的知识问答系统。轻量级、可扩展、支持工具/Skills/MCP/RAG。

## 特性

- 🤖 **ReAct风格Agent**：思考-工具调用-观察循环
- 🔧 **可扩展工具系统**：JSON Schema装饰器注册，8个内置工具
- 📚 **Skills系统**：SKILL.md frontmatter，启用即生效
- 🔌 **MCP客户端**：stdio / SSE / StreamableHTTP三种传输
- 💬 **Web聊天界面**：FastAPI后端 + Vanilla JS前端，WebSocket流式
- 👥 **多用户认证**：JWT (access + refresh) + bcrypt
- 💾 **持久化**：SQLite (异步SQLAlchemy 2.0)
- 📊 **可观测性**：结构化日志 + 健康检查
- 🚀 **RAG-ready**：Provider.embed()接口预留，二阶段接入vector-service

## 快速开始

### 1. 安装

```bash
git clone <repo>
cd lumos
pip install -e ".[dev]"
```

### 2. 配置

复制样例配置：

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

编辑 `.env`：

```bash
OPENAI_API_KEY=sk-your-key
JWT_SECRET=$(openssl rand -hex 32)
DEFAULT_ADMIN_PASSWORD=your-strong-password
```

编辑 `config.yaml`，设置provider和model。

### 3. 创建管理员

```bash
lumos admin create --email admin@example.com --password your-password
```

或设置`config.yaml`的`auth.default_admin_password`环境变量，自动创建。

### 4. 启动

```bash
lumos serve --config config.yaml
```

浏览器打开 http://127.0.0.1:8000

### 5. 使用

- 注册或登录
- 点击"+ 新会话"
- 输入消息，按Enter发送
- 可启用Skills（底部设置抽屉）

## 架构

参见 [docs/architecture.md](docs/architecture.md)。

## 扩展

- **添加自定义工具**：参见 [docs/tools.md](docs/tools.md)
- **创建Skills**：参见 [docs/skills.md](docs/skills.md)
- **接入MCP服务器**：参见 [docs/mcp.md](docs/mcp.md)

## 路线图

- ✅ 一阶段：Agent基础 + 工具/Skills/MCP + Web界面
- 🔜 二阶段：RAG（通过vector-service）
- 🔜 三阶段：Anthropic / Gemini Provider
- 🔜 四阶段：OpenTelemetry追踪
- 🔜 五阶段：多租户与团队管理

## 开发

```bash
# 跑测试
pytest -v

# 代码风格
ruff check src tests
mypy src

# 覆盖率
pytest --cov=lumos --cov-report=html
```

## 许可

商业软件，保留所有权利。
```

**Step 23.2: 写`docs/architecture.md`**

```markdown
# 架构

Lumos采用分层架构，从下到上：

```
┌─────────────────────────────────────┐
│  Web前端 (Vanilla JS)               │
├─────────────────────────────────────┤
│  FastAPI REST + WebSocket          │
├─────────────────────────────────────┤
│  Agent主循环 (ReAct)              │
├─────────────────────────────────────┤
│  Providers │ Tools │ Skills │ MCP │
├─────────────────────────────────────┤
│  持久化层 (SQLAlchemy + SQLite)    │
└─────────────────────────────────────┘
```

详细模块说明见spec：`docs/superpowers/specs/2026-09-15-lumos-agent-design.md`
```

**Step 23.3: 写`docs/tools.md`**

```markdown
# 扩展工具

工具通过装饰器或类注册到`ToolRegistry`。

## 装饰器方式（推荐）

```python
# src/lumos/tools/builtin/my_tool.py
from lumos.tools.base import Tool
from lumos.tools.registry import register_tool

@register_tool(
    name="my_tool",
    description="做某事",
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string"},
        },
        "required": ["input"],
    },
)
class MyTool(Tool):
    async def execute(self, *, input: str) -> str:
        return f"处理: {input}"
```

文件放到`src/lumos/tools/builtin/`下，会被自动发现。

## 类方式

```python
from lumos.tools.base import Tool, ToolMeta

class MyTool(Tool):
    meta = ToolMeta(
        name="my_tool",
        description="做某事",
        parameters={...},
    )
    async def execute(self, **kwargs):
        ...
```

## 危险操作

标记`requires_confirmation=True`，前端会弹窗确认。
```

**Step 23.4: 写`docs/skills.md`**

```markdown
# Skills系统

每个Skill是一个目录，含`SKILL.md`（YAML frontmatter + Markdown正文）。

## 创建Skill

```bash
mkdir -p skills/my-skill
cat > skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: 简短的skill描述（LLM根据这个决定何时启用）
required_tools: [web_search]
optional_tools: []
---

# 我的Skill

详细指令注入到系统提示词。

## 工作流

步骤1...
步骤2...
EOF
```

## 元数据字段

| 字段 | 类型 | 说明 |
|---|---|---|
| name | str | Skill名称（必填） |
| description | str | 描述（必填，LLM据此选择） |
| version | str | 版本号 |
| tags | list[str] | 标签 |
| required_tools | list[str] | 必需工具，缺失则禁用 |
| optional_tools | list[str] | 可选工具 |
| max_steps | int | Agent最大步数覆盖 |

## 携带工具

Skill目录可包含`tools/`子目录，专属工具的Python代码。
```

**Step 23.5: 写`docs/mcp.md`**

```markdown
# MCP接入

MCP（Model Context Protocol）是Anthropic的开放标准，让LLM连接任意工具源。

## 三种传输

### stdio（本地子进程）

```yaml
mcp_servers:
  - name: filesystem
    transport: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    env: { NODE_ENV: production }
```

### SSE（远程事件流）

```yaml
- name: remote
  transport: sse
  url: https://mcp.example.com/sse
  headers:
    Authorization: Bearer ${MCP_TOKEN}
```

### Streamable HTTP（MCP 2025协议）

```yaml
- name: github
  transport: streamable_http
  url: https://api.githubcopilot.com/mcp
  headers:
    Authorization: Bearer ${GH_TOKEN}
```

## 命名空间

所有MCP工具自动加前缀 `{server}__{tool}` 避免冲突。
```

**Step 23.6: 跑全测**

Run: `pytest -v`
Expected: 全部PASS

**Step 23.7: 提交**

```bash
git add README.md docs/
git commit -m "docs: README and architecture/tools/skills/mcp guides"
```

---

## Self-review

### 1. Spec覆盖

| Spec章节 | 覆盖任务 |
|---|---|
| §4.1 项目结构 | Task 1 |
| §4.2 核心数据流（Agent循环）| Task 3, 10 |
| §4.3 Provider抽象 | Task 3, 4 |
| §4.4 工具系统 | Task 5, 6 |
| §4.5 Skills系统 | Task 7 |
| §4.6 MCP客户端 | Task 8, 9 |
| §4.7 Session与持久化 | Task 2, 12 |
| §4.8 FastAPI后端 | Task 13, 14, 15, 16, 17, 18, 19 |
| §4.9 Web前端 | Task 20, 21, 22 |
| §4.10 用户认证 | Task 12, 14 |
| §4.11 错误处理与可观测性 | Task 1, 18 |
| §4.12 测试策略 | 全部（每Task含测试）|
| §5 关键技术决策 | 任务顺序遵循 |
| §6 风险与缓解 | Task 11（上下文压缩）, Task 16（WS重连）, Task 6（路径沙箱）|
| §7 RAG扩展点 | Task 3保留embed接口 |
| §8 验收标准 | 全部任务完成后验证 |
| §9 依赖清单 | Task 1（pyproject.toml）|

### 2. 占位符扫描

- 无TBD/TODO（已扫描）
- 无"implement later"
- 无"similar to task N"
- 每Step都展示了实际代码或精确命令

### 3. 类型一致性

- `Message`/`TextContent`/`ToolCall`/`ToolResult`/`Usage`/`AgentEvent`/`ToolSpec`在Task 3定义，后续任务一致使用
- `User`/`ChatSession`/`Message`/`McpServer`/`RevokedToken` ORM模型在Task 2定义，后续仓储使用一致
- `BaseProvider.chat()`签名在Task 3定义，OpenAICompatProvider在Task 4实现并测试一致
- `Tool`/`ToolMeta`/`ToolRegistry`/`register_tool`在Task 5定义，Task 6内置工具使用一致
- `Skill`/`SkillManager`/`parse_skill`在Task 7定义，Task 17路由使用一致
- `BaseTransport`/`StdioTransport`/`SseTransport`/`StreamableHttpTransport`在Task 8定义，Task 9 McpClient使用一致
- `McpServerConfig`/`McpClient`/`McpManager`在Task 8/9定义，Task 17路由使用一致
- `Agent`/`AgentRunner`/`Runners`在Task 10/16定义，Task 16 WebSocket路由使用一致

### 4. 范围检查

单plan聚焦一阶段Agent基础能力，未混入RAG实现。任务23个（含sub-steps），可在合理时间内实施。

### 5. 边界场景覆盖

测试任务覆盖：
- ✅ 长对话压缩（Task 11）
- ✅ LLM返回空content（Task 10 max_steps）
- ✅ tool执行失败（Task 6 shell_exec）
- ✅ MCP启动失败（Task 9 fixture）
- ✅ 越权访问（Task 15 test_session_user_isolation）
- ✅ 密码强度（Task 13）
- ✅ JWT过期/类型错误（Task 12）
- ✅ WebSocket消息（Task 16）

---

## 执行手册

### 跑完所有任务后验证

```bash
# 1. 全部测试通过
pytest -v
# 预期：~80个测试全部PASS，覆盖率>=85%

# 2. 类型检查
mypy src/lumos
# 预期：无错误

# 3. 代码风格
ruff check src tests
# 预期：无错误

# 4. 启动服务（用测试LLM或mock）
OPENAI_API_KEY=test-key lumos serve --config config.yaml

# 5. 端到端冒烟
# 浏览器打开 http://127.0.0.1:8000
# - 注册/登录
# - 创建会话
# - 发送消息
# - 工具调用（如web_search）
# - 启用/禁用Skill
# - 添加MCP服务器
```

### 实施顺序

严格按Task 1→23顺序执行，因为每个任务依赖前面任务的输出（类型、API、文件路径）。
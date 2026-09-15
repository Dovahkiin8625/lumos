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
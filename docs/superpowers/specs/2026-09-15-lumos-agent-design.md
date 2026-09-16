# Lumos Agent — 一阶段设计文档

**日期**: 2026-09-15
**状态**: 已批准，等待实施计划
**范围**: 一阶段（基础Agent能力；RAG延后到二阶段）

---

## 1. 概述

Lumos 是一个商用的、基于Agent的知识问答系统。本设计文档描述一阶段的范围与架构：

- **目标**：交付一个轻量级、可扩展的Agent运行时，具备工具注册、技能系统、MCP客户端等核心能力。
- **交付形态**：FastAPI后端 + 内置Web聊天页面 + 可选CLI入口。
- **后续**：通过`F:\project\vector-service`工程扩展RAG能力（一阶段不实现）。

## 2. 设计原则

1. **轻量级**：参考nanobot，自研核心循环，依赖最小化（核心<15个第三方包）。
2. **可扩展**：模块清晰边界，工具/技能/MCP可独立替换。
3. **商用就绪**：多用户、认证、持久化、可观测性、健康检查。
4. **异步优先**：纯asyncio代码，与FastAPI天然契合。

## 3. 范围与边界

### 3.1 一阶段包含

- Agent主循环（ReAct风格，并行工具调用）
- LLM Provider抽象（OpenAI兼容，覆盖所有兼容服务）
- 工具系统（注册、JSON Schema、内置8个工具）
- Skills系统（SKILL.md frontmatter格式）
- MCP客户端（stdio / SSE / StreamableHTTP三种传输）
- Session持久化（SQLite + SQLAlchemy异步）
- Web后端（FastAPI + WebSocket流式）
- Web前端（Vanilla JS单页应用）
- 多用户 + JWT认证
- 结构化日志 + 健康检查

### 3.2 一阶段不包含（明确延后）

- RAG能力（向量检索、嵌入、重排序）— 二阶段通过`F:\project\vector-service`接入
- Anthropic / Gemini / Ollama专用Provider — 仅留接口，OpenAI兼容实现即可覆盖
- OpenTelemetry追踪
- 多租户/团队管理
- 计费与配额

## 4. 架构

### 4.1 项目结构

```
lumos/
├── pyproject.toml
├── README.md
├── .env.example
├── docs/
│   ├── architecture.md
│   ├── tools.md
│   ├── skills.md
│   └── mcp.md
├── src/lumos/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  # CLI入口（备用）
│   ├── server.py               # FastAPI app启动入口
│   ├── config.py               # 配置加载（YAML/.env）
│   ├── logging.py              # 结构化日志
│   ├── agent/                  # Agent核心
│   │   ├── core.py
│   │   ├── message.py
│   │   ├── context.py
│   │   └── runner.py
│   ├── providers/              # LLM Provider抽象
│   │   ├── base.py
│   │   └── openai_compat.py
│   ├── tools/                  # 工具系统
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── builtin/
│   │       ├── web_search.py
│   │       ├── web_fetch.py
│   │       ├── file_ops.py
│   │       ├── shell.py
│   │       ├── datetime.py
│   │       ├── calculator.py
│   │       └── http_request.py
│   ├── skills/
│   │   ├── loader.py
│   │   └── manager.py
│   ├── mcp/
│   │   ├── client.py
│   │   ├── config.py
│   │   └── transports/
│   │       ├── stdio.py
│   │       ├── sse.py
│   │       └── streamable_http.py
│   ├── persistence/
│   │   ├── db.py
│   │   ├── models.py
│   │   └── repositories/
│   │       ├── users.py
│   │       ├── sessions.py
│   │       └── messages.py
│   ├── api/
│   │   ├── app.py
│   │   ├── deps.py
│   │   ├── auth.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── sessions.py
│   │       ├── messages.py
│   │       ├── ws.py
│   │       ├── skills.py
│   │       └── mcp.py
│   └── web/                    # 静态前端
│       ├── index.html
│       ├── login.html
│       ├── app.js
│       ├── style.css
│       └── vendor/
│           ├── marked.min.js
│           └── highlight.min.js
├── skills/                     # 内置Skills
│   ├── web-research/SKILL.md
│   ├── code-assistant/SKILL.md
│   └── data-analysis/SKILL.md
├── mcp_servers.example.yaml
├── config.example.yaml
├── tests/
│   ├── unit/
│   ├── api/
│   ├── fixtures/
│   └── e2e/
└── data/
    └── lumos.db
```

### 4.2 核心数据流（Agent循环）

数据类（`agent/message.py`）：

- `TextContent { text: str }`
- `ToolCall { id, name, arguments: dict }`
- `ToolResult { tool_call_id, content, is_error }`
- `Message { role, content, name, tool_call_id }`
- `Usage { prompt_tokens, completion_tokens, total_tokens }`
- `AgentEvent { type, session_id, data }` — 流式事件类型：`text | tool_call_start | tool_call_result | tool_call_end | confirm_required | error | usage | done`

主循环（`agent/core.py`）：

1. 拼装系统提示词 = base prompt + 启用skills的指令
2. 追加user消息到历史
3. 循环（最多`max_steps`）：
   - 可选：上下文压缩（按token数触发）
   - 调用Provider.stream_chat，传入消息+tools+skills system
   - Provider通过`on_text`回调推送token增量
   - 累积text与tool_calls（OpenAI分片流式）
   - 记录assistant消息
   - 若无tool_call：发`done`事件，返回Usage
   - 若有tool_call：并行`asyncio.gather`执行，`on_event`推`tool_call_start/result/end`
   - 把ToolResult加入历史
4. 超过`max_steps`抛`MaxStepsExceededError`

关键特性：

- **并行tool执行**：同一轮多个tool_call并行
- **流式回调**：`on_text`逐字符推送给WebSocket
- **可取消**：`asyncio.Event`传播，前端断开连接时停止
- **上下文压缩**：超过阈值（如80k tokens）触发摘要
- **错误隔离**：单个tool失败不影响主流程

### 4.3 Provider抽象

`providers/base.py`：

```python
class BaseProvider(ABC):
    async def chat(self, messages, *, system, tools, temperature,
                   max_tokens, cancel, on_text) -> tuple[str, list[ToolCall], Usage]: ...
    async def stream_chat(self, **kwargs): ...
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("RAG not implemented in phase 1")
```

`providers/openai_compat.py`：覆盖OpenAI官方 + 所有OpenAI兼容服务（DeepSeek/Qwen/Moonshot/Ollama/vLLM等）。处理分片tool_calls（按index累加）。

配置（`config.yaml`）：

```yaml
provider:
  type: openai_compat
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini
  temperature: 0.7
  max_tokens: 4096
```

### 4.4 工具系统

抽象（`tools/base.py`）：

- `Tool`抽象类（`name`/`description`/`parameters`/`execute`）
- `ToolRegistry`全局注册表
- `ToolSpec`用于跨Provider/MCP传递

注册方式：装饰器或显式类实例。

**内置工具清单**：

| 工具名 | 描述 | 默认实现 |
|---|---|---|
| `web_search` | 联网搜索 | duckduckgo-search |
| `web_fetch` | URL抓取转Markdown | httpx + trafilatura |
| `file_read` | 读取本地文件 | 受限路径 |
| `file_write` | 写入本地文件 | 需前端确认 |
| `shell_exec` | 执行shell命令 | 需前端确认+沙箱 |
| `datetime_now` | 当前时间/时区 | stdlib |
| `calculator` | 数学表达式 | 受限eval |
| `http_request` | 通用HTTP请求 | httpx |

安全策略：危险操作标记`requires_confirmation=True`，前端弹窗确认；文件工具受配置路径限制。

### 4.5 Skills系统

**SKILL.md格式**（Markdown + YAML frontmatter）：

```markdown
---
name: web-research
description: 进行深入的网页研究...
version: 1.0.0
author: Lumos Team
tags: [research, web, analysis]
required_tools: [web_search, web_fetch]
optional_tools: [http_request]
max_steps: 10
---

# 网络研究技能正文（注入到系统提示词）
```

`SkillManager`：

- 启动时从`skills_dirs`扫描`*/SKILL.md`
- 解析frontmatter+正文
- `build_system_prompt(enabled_names)`拼接base + 启用skills
- `enable/disable/list`管理API

Skill可携带专属工具与示例文件：

```
skills/web-research/
├── SKILL.md
├── tools/         # 可选
│   └── advanced_search.py
└── examples/
```

### 4.6 MCP客户端

**配置格式**（`config.yaml`或`mcp_servers.yaml`）：

```yaml
mcp_servers:
  - name: filesystem
    transport: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    enabled: true
  - name: remote-research
    transport: sse
    url: https://mcp.example.com/sse
    headers: { Authorization: Bearer ${MCP_TOKEN} }
    enabled: true
  - name: github
    transport: streamable_http
    url: https://api.githubcopilot.com/mcp
    headers: { Authorization: Bearer ${GH_TOKEN} }
    enabled: false
```

`McpServerConnection`：封装单个MCP服务器连接；`connect()`时初始化并列举tools/resources/prompts。

`McpManager`：管理所有连接，提供`all_tools()`/`call_tool()`/`shutdown()`，启动时`connect_all()`并发初始化。

传输实现（`mcp/transports/`）：

- `StdioTransport`：本地子进程（`asyncio.create_subprocess_exec`）
- `SseTransport`：SSE事件流 + POST到post_url
- `StreamableHttpTransport`：MCP 2025新协议

工具命名加前缀（`{server}__{tool}`）避免冲突。使用官方`mcp` Python SDK。

### 4.7 Session与持久化

**ORM模型**（SQLAlchemy 2.0异步 + aiosqlite）：

- `User { id, email, password_hash, created_at, is_active }`
- `ChatSession { id, user_id, title, created_at, updated_at, enabled_skills, model_config }`
- `Message { id, session_id, role, content(JSON), tool_calls(JSON), tool_call_id, name, created_at, prompt_tokens, completion_tokens }`
- `McpServer { id, user_id, name, config(JSON), enabled }`
- `RevokedToken { jti, user_id, revoked_at, expires_at }`

**仓储模式**：

- `UserRepository`：create、get_by_email、get_by_id
- `ChatSessionRepository`：create、list_by_user、get（带权限检查）、delete、update_skills
- `MessageRepository`：append、list_by_session、load_session_history
- `McpServerRepository`：list_by_user、upsert、delete

迁移策略：一阶段用`Base.metadata.create_all()`自动建表，二阶段引入Alembic。

### 4.8 FastAPI后端

**REST API**：

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/auth/logout
GET    /api/auth/me
GET    /api/sessions
POST   /api/sessions
GET    /api/sessions/{id}
PATCH  /api/sessions/{id}
DELETE /api/sessions/{id}
GET    /api/sessions/{id}/messages
POST   /api/sessions/{id}/messages
WS     /ws/sessions/{id}
GET    /api/skills
GET    /api/skills/{name}
POST   /api/skills/{name}/enable
POST   /api/skills/{name}/disable
GET    /api/mcp/servers
POST   /api/mcp/servers
PATCH  /api/mcp/servers/{id}
DELETE /api/mcp/servers/{id}
POST   /api/mcp/servers/{id}/test
POST   /api/tools/confirm
GET    /api/health
```

**WebSocket协议**（`/ws/sessions/{id}`）：

客户端→服务端：`{type: user_message, content, enabled_skills}`、`{type: tool_confirm, tool_call_id, confirmed}`、`{type: cancel}`

服务端→客户端：`text`、`tool_call_start`、`tool_call_result`、`tool_call_end`、`confirm_required`、`error`、`usage`、`done`。

应用工厂（`api/app.py`）：`create_app(config)`初始化DB、Provider、McpManager；注册路由；挂载静态前端。

### 4.9 Web前端

单页Vanilla JS应用：

- 顶部栏：用户菜单/登出
- 左侧：会话列表、新建按钮
- 主区：消息流（Markdown渲染 + 代码高亮 + 工具调用可视化）
- 底部：消息输入框 + 技能多选 + 发送按钮
- 抽屉：技能管理、MCP服务器管理

本地化vendored：`marked.js`、`highlight.js`。

**不使用框架的理由**：0构建步骤，部署简单，现代浏览器原生支持足够。

### 4.10 用户认证

- 邮箱+密码（bcrypt rounds=12）
- JWT（access TTL=24h + refresh TTL=30d）
- access_token存`localStorage`，refresh_token存`httpOnly` cookie
- 401时自动用refresh刷新一次
- 撤销名单（`revoked_tokens`表）
- 首次启动：自动建admin账号或CLI命令`lumos admin create`

CORS：默认同源（前端由FastAPI托管），分离部署时可配`allowed_origins`。

### 4.11 错误处理与可观测性

**分层异常**：

- `LumosError`基类
- `ProviderError { retryable }`：LLM Provider错误
- `ToolExecutionError`：工具失败
- `McpConnectionError`：MCP连接
- `CancelledError`、`MaxStepsExceededError`、`ContextLengthExceededError`

**错误传播策略**：

- LLM网络错误（5xx/超时）：自动重试3次指数退避
- LLM 4xx：立即失败
- 上下文超限：自动压缩一次，仍超则失败
- 工具失败：返回`is_error=True`结果让LLM重试
- MCP断开：标记离线+重连
- 用户取消：优雅终止+保存已有消息

**日志**：structlog结构化JSON，便于后续接入ELK/Loki。

**指标**（一阶段仅日志）：每条消息记录`prompt_tokens`、`completion_tokens`、`duration_ms`、`tool_calls`、`steps`。

**追踪**：每条消息分配`trace_id`，预留OpenTelemetry接入点。

**健康检查**：`GET /api/health`返回Provider状态、MCP服务器连接状态、DB状态。

### 4.12 测试策略

**测试金字塔**：

- 单元测试：pytest + pytest-asyncio + pytest-mock，覆盖核心模块85%+
- API集成测试：httpx.AsyncClient + 内存SQLite，关键路径全覆盖
- E2E（可选）：Playwright，烟雾测试

**Mock策略**：

- `mock_provider` fixture返回固定响应
- `scripted_provider` fixture按调用次数返回不同响应
- respx mock httpx调用

**关键边界场景**：

- 空会话首条消息
- 长对话触发压缩
- LLM返回空content且无tool_calls
- tool返回超长结果
- 并行tool中一个超时
- MCP启动失败（不影响其他）
- WebSocket中途断开
- 越权访问（A访问B的会话）
- SQL注入/路径穿越

## 5. 关键技术决策

| 决策 | 选择 | 备选 | 理由 |
|---|---|---|---|
| 异步模型 | 全asyncio | 同步+线程池 | 与FastAPI契合，I/O密集场景吞吐高 |
| Provider实现 | OpenAI兼容一统天下 | 多家SDK各自实现 | 减少依赖，覆盖面广（DeepSeek/Qwen/Moonshot/Ollama/vLLM均兼容） |
| MCP传输 | 全部三种 | 仅stdio | 商用场景需要云端MCP服务 |
| Web框架 | FastAPI | Flask/Django | 原生async+WebSocket+OpenAPI文档 |
| 前端 | Vanilla JS | React/Vue | 0构建步骤，依赖少 |
| 持久化 | SQLite | PostgreSQL/JSON | 起步轻量，后续可平滑迁移 |
| 认证 | JWT (access+refresh) | Session cookie | 横向扩展友好 |
| 密码哈希 | bcrypt rounds=12 | argon2/scrypt | 行业标准 |
| 迁移工具 | create_all（一阶段）/ Alembic（二阶段） | Alembic直接上 | 一阶段表结构简单，先跑通 |
| MCP库 | 官方mcp SDK | 自研 | 协议复杂，重复造轮子价值低 |

## 6. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 长对话上下文超限 | LLM调用失败 | 自动压缩 + 错误重试 + 提示用户新建会话 |
| MCP协议版本演进 | 客户端不兼容 | 跟官方SDK更新，封装抽象层降低耦合 |
| WebSocket断线 | 用户体验差 | 自动重连+恢复最近N条消息 |
| bcrypt慢哈希 | 注册/登录慢 | rounds=12（业界标准），预留rounds可配 |
| OpenAI分片tool_calls解析 | 部分LLM兼容差 | 容错：args解析失败标记`_parse_error`让LLM重试 |
| Vanilla JS复杂度 | 大型UI难维护 | 严格分层（state/render/event），关键路径外允许迭代优化 |

## 7. 二阶段RAG扩展点

设计已显式保留以下扩展点：

1. `providers/base.py:embed()` — 二阶段实现`VectorServiceProvider`继承
2. `tools/builtin/knowledge_search.py` — 新增工具调用`VectorServiceProvider.embed()`+向量库检索
3. `skills/rag/` — 新增RAG相关skill（如`doc-qa`、`paper-summary`）
4. `tools/`下的`document_loader.py`（如需）
5. 配置层`config.yaml`新增`vector_service`段

## 8. 验收标准

- [ ] 用户能注册/登录/登出
- [ ] 用户能创建/列出/删除会话
- [ ] 用户能发送消息并接收流式响应
- [ ] LLM在需要时调用工具，结果展示给用户
- [ ] 工具调用可视化（折叠面板+执行状态）
- [ ] 用户能启用/停用skills，提示词随之变化
- [ ] 用户能添加/删除MCP服务器，工具列表随之变化
- [ ] 危险工具调用前弹窗确认
- [ ] 长对话触发上下文压缩
- [ ] WebSocket中途断开不影响其他用户
- [ ] 越权访问返回403
- [ ] 结构化日志输出到stdout
- [ ] `/api/health`返回完整状态
- [ ] 单元测试覆盖率≥85%
- [ ] API集成测试覆盖所有关键端点

## 9. 依赖清单（pyproject.toml）

**核心依赖**：

- `openai>=1.40` — OpenAI兼容LLM客户端
- `httpx>=0.27` — HTTP客户端（异步）
- `mcp>=1.0` — MCP官方SDK
- `fastapi>=0.110` — Web框架
- `uvicorn[standard]>=0.27` — ASGI服务器
- `sqlalchemy[asyncio]>=2.0` — ORM
- `aiosqlite>=0.19` — 异步SQLite驱动
- `pydantic>=2.5` — 数据校验
- `pydantic-settings>=2.1` — 配置加载
- `pyyaml>=6.0` — YAML配置
- `python-frontmatter>=1.1` — SKILL.md解析
- `bcrypt>=4.1` — 密码哈希
- `pyjwt>=2.8` — JWT签发/校验
- `structlog>=24.1` — 结构化日志
- `duckduckgo-search>=6.0` — web_search默认实现
- `trafilatura>=1.6` — web_fetch内容提取
- `python-multipart>=0.0.9` — FastAPI表单解析

**开发依赖**：

- `pytest>=8.0`、`pytest-asyncio>=0.23`、`pytest-mock>=3.12`、`pytest-cov>=4.1`、`respx>=0.21`、`httpx[test]`
- `mypy>=1.8`、`ruff>=0.4`
- `playwright>=1.40`（E2E可选）

## 10. 实施顺序

1. 项目骨架（pyproject.toml、目录、config加载）
2. 持久化层（DB + ORM + 仓储）
3. 用户认证（JWT + bcrypt + auth routes）
4. Provider抽象 + OpenAI兼容实现
5. 工具系统（抽象 + 内置8个）
6. Skills系统（loader + manager）
7. MCP客户端（三种传输）
8. Agent主循环
9. 会话/消息REST API
10. WebSocket流式路由
11. Web前端（HTML+JS）
12. FastAPI应用工厂 + 静态挂载
13. 错误处理 + 日志 + 健康检查
14. 单元测试 + API集成测试
15. 文档与示例
# Lumos

> 商用基于Agent的知识问答系统。轻量级、可扩展、支持工具/Skills/MCP/RAG。

## 特性

- 🤖 **ReAct风格Agent**：思考-工具调用-观察循环
- 🔧 **可扩展工具系统**：JSON Schema装饰器注册，8个内置工具
- 📚 **Skills系统**：SKILL.md frontmatter，启用即生效
- 🔌 **MCP客户端**：stdio / SSE / StreamableHTTP三种传输
- 💬 **Web聊天界面**：FastAPI后端 + Vue 3 + Vite前端（shadcn-vue + Tailwind），WebSocket流式
- 👥 **多用户认证**：JWT (access + refresh) + bcrypt
- 💾 **持久化**：SQLite (异步SQLAlchemy 2.0)
- 📊 **可观测性**：结构化日志 + 健康检查
- 🚀 **知识库 (RAG)**：PDF/DOCX/PPTX/HTML/Markdown 上传 + Docling 解析 + BGE-M3 嵌入 + BGE-Reranker 重排 + Milvus 检索，Admin UI 带引用面板

## 快速开始

### 1. 安装

```bash
git clone <repo>
cd lumos
pip install -e ".[dev]"
```

### 2. 构建前端（首次或前端更新后）

需要 Node.js 18+。

```bash
cd frontend
npm install
npm run build
cd ..
```

开发模式（推荐贡献代码时使用）：

```bash
# 终端 1
lumos serve --config config.yaml

# 终端 2
cd frontend && npm run dev
# 浏览器打开 http://127.0.0.1:5173
```

### 3. 配置

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

### 4. 创建管理员

```bash
lumos admin create --email admin@example.com --password your-password
```

或设置`config.yaml`的`auth.default_admin_password`环境变量，自动创建。

### 5. 启动

```bash
lumos serve --config config.yaml
```

浏览器打开 http://127.0.0.1:8000

### 6. 使用

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
- **管理知识库 / RAG**：参见 [docs/knowledge-base.md](docs/knowledge-base.md)

## 路线图

- ✅ 一阶段：Agent基础 + 工具/Skills/MCP + Web界面
- ✅ 二阶段：知识库 (RAG) — 通过 vector-service
- 🔜 三阶段：聊天 Agent 自动调用知识库工具
- 🔜 四阶段：Anthropic / Gemini Provider
- 🔜 五阶段：OpenTelemetry 追踪
- 🔜 六阶段：多模态检索（图片 / 表格）

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
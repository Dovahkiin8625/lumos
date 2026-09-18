# 架构

Lumos采用分层架构，从下到上：

```
┌─────────────────────────────────────┐
│  Web前端 (Vue 3 + Vite + shadcn-vue) │
├─────────────────────────────────────┤
│  FastAPI REST + WebSocket          │
├─────────────────────────────────────┤
│  Agent主循环 (ReAct)              │
├─────────────────────────────────────┤
│  Providers │ Tools │ Skills │ MCP │ KnowledgeBase │
├─────────────────────────────────────┤
│  持久化层 (SQLAlchemy + SQLite)    │
└─────────────────────────────────────┘
         │ httpx (异步)
┌────────▼────────────────────────────┐
│  vector-service (外部进程)         │
│  BGE-M3 + BGE-Reranker + Docling   │
│  + RecursiveChunker + Milvus        │
└─────────────────────────────────────┘
```

## 前端栈

- **Vue 3** (`<script setup>` + Composition API)
- **Vite 5** 构建工具，开发时 `npm run dev` 启动独立服务（`:5173`），通过代理转发 `/api` 与 `/ws` 到 FastAPI（`:8000`）
- **Pinia** 状态管理（auth / sessions / skills / mcps / theme）
- **vue-router**（`/login` 与 `/chat` 两个路由）
- **Element Plus** 组件库（中文 locale），**highlight.js** + **marked** 渲染 markdown
- **TypeScript** 严格模式，与后端 Pydantic schema 类型对齐

构建产物落在 `frontend/dist/`，由 FastAPI 直接挂载为静态资源。SPA 路由通过 catch-all 回落到 `index.html`。

## 开发双进程模式

```bash
# 终端 1：后端
lumos serve --config config.yaml

# 终端 2：前端
cd frontend && npm run dev
# 浏览器打开 http://127.0.0.1:5173 （Vite 自带 HMR）
```

生产 / 单进程模式：`npm run build` 后只需 `lumos serve`，FastAPI 直接服务 `frontend/dist/`。

## 知识库模块（RAG）

通过 HTTP 调用独立的 [vector-service](F:\project\vector-service) 实现。Lumos 是薄客户端：
不引入 Docling / PyTorch / Milvus 依赖，只负责 KB CRUD、文档落盘、BackgroundTasks 异步索引、检索编排与引用格式化。

模块入口：`src/lumos/knowledge/`。
- `vector_client.py` — httpx 异步客户端
- `manager.py` — KnowledgeManager（编排上传 / 索引 / 删除）
- `retriever.py` — embed → search → rerank → citation

详细文档：[docs/knowledge-base.md](knowledge-base.md)。

详细模块说明见spec：`docs/superpowers/specs/2026-09-15-lumos-agent-design.md`
# 知识库（Knowledge Base / RAG）

Lumos 的知识库功能允许用户上传 PDF / DOCX / PPTX / HTML / Markdown / TXT 文档，自动解析、分片、嵌入并写入 Milvus，
提供带引用（文件名 + 章节 + 页码）的检索面板。

底层依赖独立的 [vector-service](F:\project\vector-service)，Lumos 在这里只承担：
**HTTP 编排 + 持久化 + 鉴权 + 异步任务调度 + 检索 UI**。
所有重型 ML 任务（Docling 解析、BGE-M3 嵌入、BGE-Reranker 重排、Milvus 写入）都由 vector-service 进程完成。

---

## 架构

```
┌──────────────────────────────────────────────────────────────┐
│  Lumos 前端 (Vue 3)                                         │
│  Admin → 知识库 tab                                          │
│   ├─ AdminKnowledgeBase.vue          (KB 卡片列表)           │
│   ├─ AdminKnowledgeBaseDialog.vue    (新建/编辑对话框)       │
│   ├─ AdminKnowledgeBaseDetail.vue    (KB 详情)               │
│   │   ├─ AdminKnowledgeBaseDocumentUpload.vue  (上传)       │
│   │   └─ AdminKnowledgeBaseSearch.vue         (检索面板)    │
│   └─ 路由：/admin/knowledge_base/:id                          │
└──────────────────────────────────────────────────────────────┘
                              │ REST + JWT
┌─────────────────────────────▼─────────────────────────────────┐
│  Lumos 后端 (FastAPI)                                        │
│  /api/knowledge_bases/*  (CRUD + 文档管理 + 检索)            │
│                                                               │
│  src/lumos/knowledge/                                          │
│   ├─ vector_client.py    httpx async 客户端                  │
│   ├─ manager.py          KnowledgeManager 编排               │
│   ├─ retriever.py        embed → search → rerank → cite     │
│   └─ 错误 / Repositories（knowledge_bases / documents /       │
│                          chunks 三个表）                      │
└──────────────────────────────────────────────────────────────┘
                              │ httpx /v1/embeddings · /v1/rerank
                              │ · /v1/databases/.../search · /v1/ingest
┌─────────────────────────────▼─────────────────────────────────┐
│  vector-service (独立进程)                                    │
│   ├─ BGE-M3              1024 维文本嵌入                    │
│   ├─ BGE-Reranker-v2-m3   cross-encoder 重排                 │
│   ├─ Docling             文档解析（PDF/DOCX/PPTX/HTML）      │
│   ├─ RecursiveChunker    500/75 tokens markdown-aware         │
│   └─ Milvus              向量库                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 数据模型

```
KnowledgeBase
  ├─ user_id            （owner）
  ├─ name               （1-64 字符，唯一 per user）
  ├─ description
  ├─ embedding_model    （默认 bge-m3）
  ├─ rerank_model       （默认 bge-reranker-v2-m3）
  ├─ chunk_size / chunk_overlap   （创建后只允许 description/enabled 变更）
  ├─ milvus_collection  （格式：kb_{uuid_hex[:12]}）
  └─ enabled

KnowledgeDocument
  ├─ kb_id, filename, mime_type, file_path   （原文在 data/knowledge_bases/{kb_id}/documents/{doc_id}/filename）
  ├─ status       pending → parsing → chunking → embedding → ready | failed
  ├─ error, chunk_count, page_count, doc_metadata
  └─ indexed_at

KnowledgeChunk
  └─ 占位记录（id = {doc_id}:{chunk_index}；向量本身存在 Milvus）
```

**重要**：向量存在 Milvus collection 中（每个 KB 一个），不是 SQLite。SQLite 只保留
可读的元数据 / 文件路径 / 状态，便于列表查询、统计、调试。文本与向量的真实副本在 Milvus 里。

---

## 端点

所有路径前缀 `/api/knowledge_bases`。需要 `Authorization: Bearer <access_token>`。

### KB CRUD

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api/knowledge_bases` | 列出当前用户的 KB（含 `document_count` / `indexed_chunk_count`） |
| `POST` | `/api/knowledge_bases` | 新建 KB（同步在 vector-service 创建 collection） |
| `GET` | `/api/knowledge_bases/{kb_id}` | KB 详情 |
| `PATCH` | `/api/knowledge_bases/{kb_id}` | 更新描述 / 启用状态（chunk 配置创建后不可改） |
| `DELETE` | `/api/knowledge_bases/{kb_id}` | 删除 KB（含 Milvus collection + 磁盘文件 + chunks） |

### 文档

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api/knowledge_bases/{kb_id}/documents` | 列出 KB 内文档 |
| `POST` | `/api/knowledge_bases/{kb_id}/documents` | 上传（multipart `file` 字段），背景任务索引 |
| `GET` | `/api/knowledge_bases/{kb_id}/documents/{doc_id}` | 文档详情 |
| `DELETE` | `/api/knowledge_bases/{kb_id}/documents/{doc_id}` | 删除（含 Milvus 向量 + 磁盘文件） |
| `GET` | `/api/knowledge_bases/{kb_id}/documents/{doc_id}/status` | 轮询索引状态（前端每 1.5 秒） |

### 检索

| 方法 | 路径 | 用途 |
|------|------|------|
| `POST` | `/api/knowledge_bases/{kb_id}/search` | 检索（见下方请求体） |

`/api/knowledge_bases/{kb_id}/search` 请求：

```json
{
  "query": "如何配置 BGE-M3 的检索前缀？",
  "top_k": 8,
  "search_top_k": 50,
  "use_rerank": true,
  "filter_filename": "report.pdf"
}
```

| 字段 | 默认 | 说明 |
|------|------|------|
| `query` | 必填 | 1-2048 字符 |
| `top_k` | 8 | 最终返回的命中数（重排后），`1 ≤ top_k ≤ 50` |
| `search_top_k` | 50 | 向量检索阶段的 top_k，`1 ≤ search_top_k ≤ 200` |
| `use_rerank` | true | 是否用 BGE-Reranker 重排 |
| `filter_filename` | null | 仅检索该 filename 的 chunks（Milvus `filter_expr`） |

响应：

```json
{
  "query": "如何配置 BGE-M3 的检索前缀？",
  "hits": [
    {
      "text": "...原始 chunk 文本...",
      "score": 0.95,
      "doc_id": "...",
      "chunk_index": 3,
      "section_header": "1. Intro > 1.1 Background",
      "page_number": 1,
      "filename": "report.pdf",
      "title": null,
      "citation": "report.pdf · 1. Intro > 1.1 Background · 第 1 页"
    }
  ],
  "rerank_used": true,
  "took_ms": 142
}
```

`hits[].citation` 是给前端直接展示的字符串（`filename · section_header · 第 X 页`）。

---

## 上传 + 索引流程

1. **前端**：`POST /api/knowledge_bases/{kb_id}/documents`，body 是 `multipart/form-data`，
   字段名 `file`。后端立即返回 `status="pending"` 的 `KnowledgeDocumentOut`。
2. **Lumos 后端**（BackgroundTasks）：在独立 session 中读取磁盘文件，调用 vector-service `/v1/ingest`。
3. **vector-service**：`/v1/ingest` 串起 Docling 解析 → 分片 → BGE-M3 嵌入 → Milvus upsert，
   任何步骤失败按 `doc_id` filter 原子回滚。
4. **Lumos 后端**：根据 `/v1/ingest` 返回值更新 `KnowledgeDocument.status` 为 `ready` 或 `failed`，
   同步插入 `KnowledgeChunk` 占位记录。
5. **前端**：每 1.5 秒轮询 `GET .../status`，直到 `ready` / `failed`。

> 首次上传 PDF 时 Docling 模型加载需 30-60 秒。前端会显示"摄取中..."直到 ready。

---

## 检索流程

1. **Lumos 后端**：校验 KB 存在且启用。
2. **`/v1/embeddings`**：用 KB 配置的 `embedding_model` 嵌入 query（vector-service 自动加 BGE-M3 中文检索前缀）。
3. **`/v1/databases/{db}/collections/{kb_collection}/search`**：`top_k=search_top_k`，`output_fields` 包含 doc_id / chunk_index / section_header / page_number / filename / text。
4. **`/v1/rerank`**（可选）：把候选 texts 送给 BGE-Reranker，按相关度降序返回 `top_n=top_k`。
5. **Lumos 后端**：按 rerank 顺序映射回 Milvus hit，构造 `citation` 字符串。
6. **前端**：以可折叠卡片展示，关键词高亮，分数百分比显示。

---

## 配置

`config.yaml` 顶层的 `knowledge_base:` 段：

```yaml
knowledge_base:
  vector_service_url: "http://localhost:8080"   # vector-service 地址
  database_name: "lumos"                          # Milvus database
  embed_model: "bge-m3"
  rerank_model: "bge-reranker-v2-m3"
  chunk_size: 500
  chunk_overlap: 75
  search_top_k: 50
  rerank_top_n: 8
  auto_load_models: true     # 启动时自动调 /v1/models/{id}/load
  storage_dir: "./data/knowledge_bases"
  max_file_size_mb: 50
  request_timeout: 300       # httpx 总超时（秒）
  allowed_mime_types:
    - "application/pdf"
    - "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    - "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    - "text/markdown"
    - "text/plain"
    - "text/html"
```

字段全集与默认值见 `config.example.yaml` 与 `src/lumos/config.py::KnowledgeBaseConfig`。

---

## 前端使用

### 创建知识库

登录 → **管理 → 知识库** → 「+ 新建知识库」 → 填名称/描述/embedding 模型/chunk 配置 → 保存。
卡片显示在网格中，点击进入详情页。

### 上传文档

详情页左侧 **上传文档** 卡片（拖放或选择文件）→ 自动开始摄取 → 文档列表显示 `pending → parsing → chunking → embedding → ready` 状态。
`ready` 后可点击右上"刷新"更新统计。

### 检索

详情页右侧 **检索** 卡片 → 输入问题 → 调整 `top_k` 与"启用重排"开关 → 检索。
结果以可折叠卡片列表显示：原文片段（关键词高亮）+ 分数（百分比）+ 引用（文件名 · 章节 · 页码）+ 复制按钮。

---

## 错误码与状态

| 场景 | HTTP | KB / Document status |
|------|------|----------------------|
| KB 不存在 | 404 | — |
| 同名 KB 已存在 | 409 | — |
| MIME 不在白名单 | 415 | — |
| 文件超过 `max_file_size_mb` | 413 | — |
| KB 已禁用 | 403（检索） | — |
| chunk_overlap ≥ chunk_size | 422 | — |
| 文档摄取过程中 vector-service 报错 | — | `status="failed"`，`error` 字段记录详情 |
| vector-service 不可达（启动 / 上传时） | 启动时仅记录 warning | 上传时 `status="failed"` |

---

## 内部模块（`src/lumos/knowledge/`）

| 文件 | 职责 |
|------|------|
| `vector_client.py` | `VectorServiceClient`：httpx async 客户端，封装 `/readyz` · `/v1/models/{id}/load` · `/v1/embeddings` · `/v1/rerank` · `/v1/databases` · `/v1/databases/{db}/collections` · `/v1/databases/{db}/collections/{c}/vectors` · `/v1/databases/{db}/collections/{c}/vectors/delete` · `/v1/databases/{db}/collections/{c}/search` · `/v1/ingest` |
| `manager.py` | `KnowledgeManager`：KB CRUD（与 Milvus collection 生命周期联动）、文档上传到磁盘、后台异步索引、删除时清理 Milvus 向量 + 磁盘 |
| `retriever.py` | `Retriever`：embed query → vector search → optional rerank → citation 格式化 |

后台任务（`BackgroundTasks`）使用 `manager.index_document(doc_id, kb_id)` 在独立 session 中调用 `/v1/ingest`，
文件读取走 `loop.run_in_executor` 避免阻塞事件循环。

---

## 部署检查清单

1. **vector-service 在跑**（`http://localhost:8080/readyz` 返回 200）。
2. **embed_model 已加载**（`GET /v1/models` 检查 `bge-m3.loaded = true`）。
   Lumos 启动时若 `auto_load_models=true` 会自动 POST `/v1/models/{id}/load`。
3. **Milvus database `lumos` 可访问**（vector-service 已建或 Lumos 首次创建 KB 时自动建）。
4. **磁盘空间足够**：原文存在 `data/knowledge_bases/`，大文件会显著占用空间。
5. **网络可达**：Lumos → vector-service 走 HTTP，超时 `request_timeout=300` 秒（首次 Docling 加载可能更久）。

---

## 已知限制

- 同一 KB 内的所有文档共享 chunk_size / chunk_overlap（创建后不可改）。如需不同策略，请创建新 KB。
- 删除 KB 会同时删 Milvus collection、磁盘文件、chunks 元数据 —— **不可恢复**。
- 索引失败后需手动重新上传（目前没有"重试"端点）。
- 图片内容（PDF 内嵌图、PPT 配图）暂不参与检索（Phase 2 多模态检索）。
- 没有混合检索（BM25 + dense），目前是纯向量 + rerank。

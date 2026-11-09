// 与后端 Pydantic schema 对齐的类型

export interface UserOut {
  id: number
  email: string
  created_at: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface SessionOut {
  id: string
  title: string
  enabled_skills: string[]
  created_at: string
  updated_at: string
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: string
  is_error?: boolean
}

export interface MessageOut {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  tool_calls?: ToolCall[]
  tool_call_id?: string
  name?: string
  prompt_tokens?: number
  completion_tokens?: number
  created_at: string
}

export interface SkillOut {
  name: string
  description: string
  version: string
  tags: string[]
  required_tools: string[]
  optional_tools: string[]
  max_steps: number | null
  instructions: string
  enabled: boolean
  dir_path: string
}

export interface SkillCreate {
  name: string
  description?: string
  version?: string
  tags?: string[]
  required_tools?: string[]
  optional_tools?: string[]
  max_steps?: number | null
  instructions?: string
}

export interface SkillUpdate {
  description?: string
  version?: string
  tags?: string[]
  required_tools?: string[]
  optional_tools?: string[]
  max_steps?: number | null
  instructions?: string
}

export type McpTransport = 'stdio' | 'sse' | 'streamable_http'

export interface McpServerOut {
  id: number
  name: string
  transport: McpTransport
  enabled: boolean
  config: {
    transport: McpTransport
    command?: string
    args?: string[]
    env?: Record<string, string>
    url?: string
    headers?: Record<string, string>
  }
}

export interface McpServerCreate {
  name: string
  transport: McpTransport
  enabled: boolean
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  headers?: Record<string, string>
}

// ---------------------------------------------------------------------------
// 知识库
// ---------------------------------------------------------------------------

export interface KnowledgeBaseOut {
  id: string
  name: string
  description: string
  embedding_model: string
  rerank_model: string
  chunk_size: number
  chunk_overlap: number
  milvus_collection: string
  enabled: boolean
  document_count: number
  indexed_chunk_count: number
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseCreate {
  name: string
  description?: string
  embedding_model?: string
  rerank_model?: string
  chunk_size?: number
  chunk_overlap?: number
  enabled?: boolean
}

export interface KnowledgeBaseUpdate {
  description?: string
  chunk_size?: number
  chunk_overlap?: number
  enabled?: boolean
}

export type KnowledgeDocumentStatus =
  | 'pending'
  | 'parsing'
  | 'chunking'
  | 'embedding'
  | 'ready'
  | 'failed'
  | 'deleting'

export interface KnowledgeDocumentOut {
  id: string
  kb_id: string
  filename: string
  mime_type: string
  file_size: number
  status: KnowledgeDocumentStatus
  error: string | null
  chunk_count: number
  page_count: number | null
  doc_metadata: Record<string, unknown>
  created_at: string
  indexed_at: string | null
}

export interface KnowledgeDocumentStatusOut {
  id: string
  status: KnowledgeDocumentStatus
  error: string | null
  chunk_count: number
  indexed_at: string | null
}

export interface RetrievalHit {
  text: string
  score: number
  doc_id: string
  chunk_index: number
  section_header: string | null
  page_number: number | null
  filename: string
  title: string | null
  citation: string
}

export interface KnowledgeSearchRequest {
  query: string
  top_k?: number
  search_top_k?: number
  use_rerank?: boolean
  filter_filename?: string | null
}

export interface KnowledgeSearchResponse {
  query: string
  hits: RetrievalHit[]
  rerank_used: boolean
  took_ms: number
}

// WS 事件
export type WsServerEvent =
  | { type: 'text'; session_id: string; data: { delta: string } }
  | { type: 'tool_call_start'; session_id: string; data: { calls: ToolCall[] } }
  | { type: 'tool_call_result'; session_id: string; data: { tool_call_id: string; name: string; result: string; is_error: boolean } }
  | { type: 'tool_call_end'; session_id: string; data: null }
  | { type: 'confirm_required'; session_id: string; data: { tool_call_id: string } }
  | { type: 'error'; session_id: string; data: { message: string } }
  | { type: 'usage'; session_id: string; data: { prompt_tokens: number; completion_tokens: number } }
  | { type: 'done'; session_id: string; data: { usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number } } }
  | { type: 'cancelled'; session_id: string; data: null }

export type WsClientEvent =
  | { type: 'user_message'; content: string; enabled_skills: string[] }
  | { type: 'cancel' }
  | { type: 'confirm'; tool_call_id: string; confirmed: boolean }
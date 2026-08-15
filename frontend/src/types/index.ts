export interface ApiResponse<T> {
  code: number
  message: string
  data: T | null
}

export interface SourceDoc {
  source: string
  chunk_id: string
  score: number
  snippet: string
  rank: number
}

export interface ChatData {
  answer: string
  session_id: string
  sources: SourceDoc[]
  elapsed_ms: number
  grounded: boolean
}

export interface SessionSummary {
  session_id: string
  turn_count: number
  first_timestamp: string | null
  last_timestamp: string | null
  title: string | null
}

export interface HistoryTurn {
  user: string
  bot: string
  sources: SourceDoc[]
  timestamp: string
}

export interface DocInfo {
  name: string
  category: string
  size: number
  chunk_count: number
  updated_at: string
}

export interface KnowledgeOverview {
  ready: boolean
  total_docs: number
  total_chunks: number
  categories: Record<string, number>
  docs: DocInfo[]
}

export interface RebuildResult {
  doc_count: number
  chunk_count: number
  elapsed_ms: number
  cached_chunks: number
}

export interface SystemStats {
  app_version: string
  index_ready: boolean
  doc_count: number
  chunk_count: number
  embedding_model: string
  llm_configured: boolean
  llm_base_url: string
  llm_model: string
  final_top_k: number
  enable_rerank: boolean
  vector_store_dir: string
  knowledge_docs_dir: string
}

export interface Metrics {
  chat_count: number
  total_elapsed_ms: number
  cache_hits: number
  avg_elapsed_ms: number
}

/** SSE 流式事件（由 /api/v1/chat/stream 产生） */
export interface StreamEvent {
  type: 'meta' | 'delta' | 'sources' | 'done' | 'error'
  session_id?: string
  text?: string
  sources?: SourceDoc[]
  elapsed_ms?: number
  message?: string
}

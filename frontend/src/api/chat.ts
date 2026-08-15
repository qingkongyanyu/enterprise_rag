import { request } from './http'
import type { ChatData, HistoryTurn, SessionSummary, StreamEvent } from '@/types'

/** 非流式问答 */
export async function sendChat(question: string, sessionId: string | null): Promise<ChatData> {
  return request<ChatData>('/api/v1/chat', {
    method: 'POST',
    body: JSON.stringify({ question, session_id: sessionId }),
  })
}

/**
 * 流式问答（SSE）。解析后端逐条 `data: {...}` 事件并回调。
 */
export async function streamChat(
  question: string,
  sessionId: string | null,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${import.meta.env.VITE_API_BASE ?? ''}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  })

  if (!res.ok || !res.body) {
    let msg = `流式请求失败 (HTTP ${res.status})`
    try {
      const data = await res.json()
      msg = data.message || data.detail || msg
    } catch {
      /* ignore */
    }
    throw new Error(msg)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let newlineIndex = buffer.indexOf('\n\n')
    while (newlineIndex !== -1) {
      const chunk = buffer.slice(0, newlineIndex)
      buffer = buffer.slice(newlineIndex + 2)
      const line = chunk.split('\n').find((l) => l.startsWith('data: '))
      if (line) {
        try {
          onEvent(JSON.parse(line.slice(6)) as StreamEvent)
        } catch {
          /* 忽略解析失败的单帧 */
        }
      }
      newlineIndex = buffer.indexOf('\n\n')
    }
  }
}

/** 会话列表 */
export async function listSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>('/api/v1/sessions')
}

/** 会话历史 */
export async function getSessionHistory(sessionId: string): Promise<HistoryTurn[]> {
  const data = await request<{ session_id: string; history: HistoryTurn[] }>(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/history`,
  )
  return data.history
}

/** 删除会话 */
export async function deleteSession(sessionId: string): Promise<void> {
  await request(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
}

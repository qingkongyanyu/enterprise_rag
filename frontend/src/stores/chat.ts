import { defineStore } from 'pinia'

import { deleteSession, getSessionHistory, listSessions, sendChat, streamChat } from '@/api/chat'
import type { HistoryTurn, SessionSummary, SourceDoc } from '@/types'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources: SourceDoc[]
  streaming?: boolean
  error?: boolean
  elapsedMs?: number
  grounded?: boolean
}

let seq = 0
const msgId = () => `m_${Date.now()}_${seq++}`

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as ChatMessage[],
    sessions: [] as SessionSummary[],
    currentSessionId: localStorage.getItem('rag_session_id') ?? null,
    sending: false,
    sessionsOpen: true,
    activeController: null as AbortController | null,
  }),

  getters: {
    isSending: (s) => s.sending,
  },

  actions: {
    // ---------- 会话管理 ----------
    async refreshSessions() {
      this.sessions = await listSessions()
    },

    async openSession(sessionId: string) {
      this.currentSessionId = sessionId
      localStorage.setItem('rag_session_id', sessionId)
      this.messages = []
      const history = await getSessionHistory(sessionId)
      for (const turn of history) {
        this.messages.push({
          id: msgId(),
          role: 'user',
          content: turn.user,
          sources: [],
        })
        this.messages.push({
          id: msgId(),
          role: 'assistant',
          content: turn.bot,
          sources: turn.sources,
        })
      }
    },

    async newSession() {
      this.currentSessionId = null
      localStorage.removeItem('rag_session_id')
      this.messages = []
    },

    async removeSession(sessionId: string) {
      await deleteSession(sessionId)
      if (this.currentSessionId === sessionId) {
        await this.newSession()
      }
      await this.refreshSessions()
    },

    // ---------- 提问 ----------
    async ask(question: string) {
      if (this.sending) return
      this.sending = true

      const userMsg: ChatMessage = { id: msgId(), role: 'user', content: question, sources: [] }
      const botMsg: ChatMessage = {
        id: msgId(),
        role: 'assistant',
        content: '',
        sources: [],
        streaming: true,
      }
      this.messages.push(userMsg, botMsg)

      const controller = new AbortController()
      this.activeController = controller
      try {
        await streamChat(
          question,
          this.currentSessionId,
          (event) => {
            if (event.type === 'meta' && event.session_id) {
              this.currentSessionId = event.session_id
              localStorage.setItem('rag_session_id', event.session_id!)
            } else if (event.type === 'delta') {
              botMsg.content += event.text ?? ''
            } else if (event.type === 'sources') {
              botMsg.sources = event.sources ?? []
            } else if (event.type === 'done') {
              botMsg.elapsedMs = event.elapsed_ms
            } else if (event.type === 'error') {
              botMsg.error = true
              botMsg.content = event.message ?? '生成失败'
            }
          },
          controller.signal,
        )
      } catch (err) {
        const isAbort = (err as Error)?.name === 'AbortError'
        if (!isAbort) {
          botMsg.error = true
          botMsg.content = (err as Error).message || '网络错误，请稍后重试'
        }
      } finally {
        botMsg.streaming = false
        this.sending = false
        this.activeController = null
        this.refreshSessions()
      }
    },

    /** 中断当前正在生成的消息 */
    stopStreaming() {
      this.activeController?.abort()
    },

    /** 非流式兜底（流式不可用时） */
    async askOnce(question: string) {
      if (this.sending) return
      this.sending = true
      const userMsg: ChatMessage = { id: msgId(), role: 'user', content: question, sources: [] }
      this.messages.push(userMsg)
      try {
        const data = await sendChat(question, this.currentSessionId)
        this.currentSessionId = data.session_id
        localStorage.setItem('rag_session_id', data.session_id)
        this.messages.push({
          id: msgId(),
          role: 'assistant',
          content: data.answer,
          sources: data.sources,
          elapsedMs: data.elapsed_ms,
          grounded: data.grounded,
        })
      } catch (err) {
        this.messages.push({
          id: msgId(),
          role: 'assistant',
          content: (err as Error).message || '请求失败',
          sources: [],
          error: true,
        })
      } finally {
        this.sending = false
        this.refreshSessions()
      }
    },
  },
})

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
    async ask(
      question: string,
      options: { appendUser?: boolean; insertAt?: number } = {},
    ) {
      if (this.sending) return
      this.sending = true

      const userMsg: ChatMessage = { id: msgId(), role: 'user', content: question, sources: [] }
      // 重答场景：用户消息已在列表中，不再重复插入；bot 消息原位替换
      if (options.appendUser !== false) {
        this.messages.push(userMsg)
      }
      const insertAt = options.insertAt ?? this.messages.length
      // ⚠️ 必须先插入再取引用：插入响应式数组后 Vue 会包装成代理对象，
      // 只有通过数组索引取回的引用（liveMsg）才能触发视图更新。
      // 直接持有插入前的原始对象去改 content，页面不会刷新（刷新后才可见）。
      this.messages.splice(insertAt, 0, {
        id: msgId(),
        role: 'assistant',
        content: '',
        sources: [],
        streaming: true,
      } as ChatMessage)
      const liveMsg = this.messages[insertAt]

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
              liveMsg.content += event.text ?? ''
            } else if (event.type === 'sources') {
              liveMsg.sources = event.sources ?? []
            } else if (event.type === 'done') {
              liveMsg.elapsedMs = event.elapsed_ms
            } else if (event.type === 'error') {
              liveMsg.error = true
              liveMsg.content = event.message ?? '生成失败'
            }
          },
          controller.signal,
        )
      } catch (err) {
        const isAbort = (err as Error)?.name === 'AbortError'
        if (!isAbort) {
          liveMsg.error = true
          liveMsg.content = (err as Error).message || '网络错误，请稍后重试'
        }
      } finally {
        liveMsg.streaming = false
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

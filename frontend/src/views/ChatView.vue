<script setup lang="ts">
import { MessageSquareText, PanelLeftClose, PanelLeftOpen, Plus, Sparkles, Trash2 } from 'lucide-vue-next'
import { nextTick, onMounted, ref, watch } from 'vue'

import ChatInput from '@/components/chat/ChatInput.vue'
import MessageItem from '@/components/chat/MessageItem.vue'
import { useChatStore } from '@/stores/chat'

const chat = useChatStore()
const scrollArea = ref<HTMLElement | null>(null)
const sessionPanel = ref<HTMLElement | null>(null)

const suggestions = [
  '员工请假流程是什么？',
  '差旅住宿标准是多少？',
  '费用报销需要什么材料？',
]

async function scrollToBottom(behavior: ScrollBehavior = 'smooth') {
  await nextTick()
  const el = scrollArea.value
  if (el) el.scrollTo({ top: el.scrollHeight, behavior })
}

watch(
  () => [chat.messages.length, chat.messages.map((m) => m.content).join('').length],
  () => scrollToBottom(),
)

onMounted(async () => {
  await Promise.allSettled([chat.refreshSessions()])
  if (chat.currentSessionId) {
    await chat.openSession(chat.currentSessionId).catch(() => chat.newSession())
  }
  scrollToBottom('auto')
})

function onSend(text: string) {
  chat.ask(text)
}

function onRegenerate(index: number) {
  // 找到该条助手消息之前的用户消息，原位替换重答（旧 bot 移除，新 bot 插入原位置）
  for (let i = index - 1; i >= 0; i--) {
    if (chat.messages[i].role === 'user') {
      const question = chat.messages[i].content
      chat.messages.splice(index, 1)
      chat.ask(question, { appendUser: false, insertAt: index })
      return
    }
  }
}

function formatTime(t: string | null) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <div class="chat-page">
    <!-- 顶栏 -->
    <header class="topbar glass">
      <button class="icon-btn" title="会话列表" @click="chat.sessionsOpen = !chat.sessionsOpen">
        <PanelLeftClose v-if="chat.sessionsOpen" :size="18" />
        <PanelLeftOpen v-else :size="18" />
      </button>
      <div class="topbar-title">
        <Sparkles :size="16" class="title-icon" />
        <span>知知 · 企业知识库智能问答</span>
      </div>
      <button class="btn btn-primary" @click="chat.newSession">
        <Plus :size="16" />
        新对话
      </button>
    </header>

    <div class="chat-body">
      <!-- 会话列表 -->
      <aside v-show="chat.sessionsOpen" ref="sessionPanel" class="session-panel glass animate-in">
        <div class="session-head">
          <span>历史会话</span>
          <span class="session-count">{{ chat.sessions.length }}</span>
        </div>
        <div class="session-list">
          <button
            v-for="s in chat.sessions"
            :key="s.session_id"
            class="session-item"
            :class="{ active: s.session_id === chat.currentSessionId }"
            @click="chat.openSession(s.session_id)"
          >
            <MessageSquareText :size="15" class="sess-icon" />
            <div class="sess-info">
              <div class="sess-title">{{ s.title || '未命名会话' }}</div>
              <div class="sess-meta">{{ s.turn_count }} 轮 · {{ formatTime(s.last_timestamp) }}</div>
            </div>
            <button class="sess-del" title="删除" @click.stop="chat.removeSession(s.session_id)">
              <Trash2 :size="13" />
            </button>
          </button>
          <div v-if="!chat.sessions.length" class="session-empty">
            暂无历史会话<br />发送一条消息试试
          </div>
        </div>
      </aside>

      <!-- 消息区 -->
      <div ref="scrollArea" class="messages-area">
        <!-- 空状态 -->
        <div v-if="!chat.messages.length" class="empty-state animate-up">
          <div class="empty-orb">
            <img src="@/assets/avatar-zhizhi.png" alt="知知" class="orb-img" />
          </div>
          <h1 class="empty-title">
            你好，我是 <span class="text-gradient">知知</span>
          </h1>
          <p class="empty-sub">企业私有知识库智能助手 · 懂制度、懂流程、懂产品</p>
          <div class="suggestion-list">
            <button
              v-for="q in suggestions"
              :key="q"
              class="suggestion"
              :disabled="chat.isSending"
              @click="onSend(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>

        <!-- 消息流 -->
        <div v-else class="messages">
          <MessageItem
            v-for="(m, idx) in chat.messages"
            :key="m.id"
            :message="m"
            @regenerate="onRegenerate(idx)"
          />
        </div>
      </div>
    </div>

    <ChatInput
      :sending="chat.isSending"
      :disabled="false"
      @send="onSend"
      @stop="chat.stopStreaming()"
    />
  </div>
</template>

<style scoped>
.chat-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(10, 16, 30, 0.6);
  border-radius: 0;
}
.topbar-title {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 15px;
  font-weight: 600;
}
.title-icon { color: var(--accent-1); }
.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: var(--text-2);
  transition: background 0.15s;
}
.icon-btn:hover { background: var(--surface-3); color: var(--text-1); }

.chat-body {
  flex: 1;
  min-height: 0;
  display: flex;
}
.session-panel {
  width: var(--sessions-w);
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  background: rgba(10, 16, 30, 0.55);
  border-radius: 0;
}
.session-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 10px;
  font-size: 13px;
  color: var(--text-3);
  letter-spacing: 0.5px;
}
.session-count { color: var(--text-2); }
.session-list { flex: 1; overflow-y: auto; padding: 4px 10px 14px; }
.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 11px 10px;
  border-radius: var(--radius-md);
  transition: background 0.15s;
  border: 1px solid transparent;
}
.session-item:hover { background: var(--surface-2); }
.session-item.active {
  background: var(--surface-3);
  border-color: rgba(129, 140, 248, 0.35);
}
.sess-icon { color: var(--accent-2); flex-shrink: 0; }
.sess-info { flex: 1; min-width: 0; }
.sess-title {
  font-size: 13px;
  color: var(--text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sess-meta { font-size: 11px; color: var(--text-3); margin-top: 2px; }
.sess-del {
  opacity: 0;
  color: var(--text-3);
  padding: 4px;
  border-radius: 6px;
  transition: all 0.15s;
}
.session-item:hover .sess-del { opacity: 1; }
.sess-del:hover { color: var(--danger); background: rgba(248, 113, 113, 0.12); }
.session-empty {
  text-align: center;
  padding: 40px 10px;
  font-size: 12px;
  color: var(--text-3);
  line-height: 1.9;
}

.messages-area { flex: 1; min-width: 0; overflow-y: auto; padding: 20px 0 30px; }
.messages { max-width: 860px; margin: 0 auto; padding: 0 24px; }

.empty-state {
  max-width: 620px;
  margin: 0 auto;
  padding-top: 16vh;
  text-align: center;
}
.empty-orb {
  width: 74px;
  height: 74px;
  margin: 0 auto 22px;
  border-radius: 22px;
  display: grid;
  place-items: center;
  overflow: hidden;
  color: #08101f;
  background: var(--gradient-primary);
  box-shadow: var(--shadow-glow);
  animation: float 5s ease-in-out infinite;
}
.orb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.empty-title { font-size: 30px; font-weight: 700; letter-spacing: 0.5px; }
.empty-sub { color: var(--text-2); margin-top: 10px; font-size: 15px; }
.suggestion-list {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 32px;
}
.suggestion {
  padding: 10px 18px;
  border-radius: 999px;
  font-size: 14px;
  color: var(--text-2);
  background: var(--surface);
  border: 1px solid var(--border);
  transition: all 0.18s;
}
.suggestion:hover {
  color: var(--text-1);
  border-color: rgba(129, 140, 248, 0.5);
  background: var(--surface-3);
  transform: translateY(-2px);
}
</style>

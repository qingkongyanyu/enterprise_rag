<script setup lang="ts">
import { Copy, RotateCcw, User } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import SourcesPanel from '@/components/chat/SourcesPanel.vue'
import TypingIndicator from '@/components/chat/TypingIndicator.vue'
import type { ChatMessage } from '@/stores/chat'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{ message: ChatMessage }>()
const emit = defineEmits<{ (e: 'regenerate'): void }>()

const copied = ref(false)
const html = computed(() =>
  props.message.error ? '' : renderMarkdown(props.message.content),
)

async function copy() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    setTimeout(() => (copied.value = false), 1600)
  } catch {
    /* clipboard 不可用时静默 */
  }
}
</script>

<template>
  <div class="msg" :class="[message.role, { streaming: message.streaming }]">
    <!-- 头像 -->
    <div class="avatar" :class="message.role">
      <img
        v-if="message.role === 'user'"
        src="@/assets/avatar-user.png"
        alt="我"
        class="avatar-img"
      />
      <img v-else src="@/assets/avatar-zhizhi.png" alt="知知" class="avatar-img" />
    </div>

    <!-- 内容 -->
    <div class="bubble-wrap">
      <div class="bubble" :class="message.role">
        <!-- 用户消息：纯文本 -->
        <div v-if="message.role === 'user'" class="plain-text">{{ message.content }}</div>

        <!-- 助手消息：Markdown 渲染 -->
        <div v-else class="markdown-body" v-html="html" />

        <!-- 流式生成中 -->
        <TypingIndicator v-if="message.streaming && !message.content" />
      </div>

      <!-- 工具条 -->
      <div v-if="message.role === 'assistant'" class="toolbar">
        <button class="tool" title="复制" @click="copy">
          <Copy :size="14" />
          <span>{{ copied ? '已复制' : '复制' }}</span>
        </button>
        <button v-if="!message.streaming" class="tool" title="重新生成" @click="emit('regenerate')">
          <RotateCcw :size="14" />
          <span>重答</span>
        </button>
        <span v-if="message.elapsedMs != null && !message.streaming" class="elapsed">
          {{ message.elapsedMs }}ms
        </span>
      </div>

      <!-- 来源引用 -->
      <SourcesPanel v-if="message.role === 'assistant' && message.sources.length" :sources="message.sources" />
    </div>
  </div>
</template>

<style scoped>
.msg {
  display: flex;
  gap: 14px;
  padding: 18px 0;
  animation: fade-up 0.3s ease both;
}
.msg.user { flex-direction: row-reverse; }

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  font-weight: 700;
}
.avatar.user {
  background: linear-gradient(135deg, #1e293b, #334155);
  color: var(--text-2);
  border: 1px solid var(--border-strong);
}
.avatar.assistant {
  background: var(--gradient-primary);
  color: #08101f;
  box-shadow: var(--shadow-glow);
}
.avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 12px;
  object-fit: cover;
  display: block;
}

.bubble-wrap {
  max-width: 78%;
  min-width: 0;
}
.msg.user .bubble-wrap { display: flex; flex-direction: column; align-items: flex-end; }

.bubble {
  padding: 13px 17px;
  border-radius: var(--radius-lg);
  font-size: 15px;
  line-height: 1.75;
}
.bubble.user {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.14), rgba(129, 140, 248, 0.18));
  border: 1px solid rgba(129, 140, 248, 0.25);
  color: var(--text-1);
}
.bubble.assistant {
  background: var(--surface);
  border: 1px solid var(--border);
  backdrop-filter: blur(12px);
}
.bubble.assistant.streaming { border-color: rgba(129, 140, 248, 0.35); }

.plain-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}
.msg:hover .toolbar { opacity: 1; }
.tool {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 9px;
  border-radius: 7px;
  font-size: 12px;
  color: var(--text-3);
  transition: all 0.15s;
}
.tool:hover { background: var(--surface-2); color: var(--text-1); }
.elapsed { font-size: 11px; color: var(--text-3); margin-left: 6px; }
</style>

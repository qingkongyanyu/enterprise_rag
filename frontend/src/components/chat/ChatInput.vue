<script setup lang="ts">
import { ArrowUp, Square } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{ sending: boolean; disabled: boolean }>()
const emit = defineEmits<{ (e: 'send', text: string): void; (e: 'stop'): void }>()

const text = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)

function autoResize() {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    submit()
  }
}

function submit() {
  const value = text.value.trim()
  if (!value || props.sending) return
  emit('send', value)
  text.value = ''
  autoResize()
}

onMounted(() => textarea.value?.focus())
watch(() => props.disabled, () => textarea.value?.focus())

defineExpose({ focus: () => textarea.value?.focus() })
</script>

<template>
  <div class="input-zone">
    <div class="input-panel">
      <textarea
        ref="textarea"
        v-model="text"
        class="input-box"
        :placeholder="disabled ? '知识库未就绪，请先到「知识库」页构建索引' : '输入你的问题，Enter 发送 · Shift + Enter 换行'"
        :disabled="disabled"
        rows="1"
        @keydown="onKeydown"
        @input="autoResize"
      />
      <button
        v-if="!sending"
        class="send-btn"
        :class="{ can: !disabled && text.trim() }"
        :disabled="disabled || !text.trim()"
        title="发送"
        @click="submit"
      >
        <ArrowUp :size="18" />
      </button>
      <button v-else class="send-btn stop" title="停止生成" @click="emit('stop')">
        <Square :size="15" />
      </button>
    </div>
    <div class="input-hint">回答严格基于企业私有知识库 · 混合检索 + 大模型生成</div>
  </div>
</template>

<style scoped>
.input-zone {
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
  padding: 0 24px 20px;
}
.input-panel {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 12px 12px 18px;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(18px);
  transition: border-color 0.2s, box-shadow 0.2s;
  box-shadow: 0 8px 30px rgba(2, 6, 18, 0.4);
}
.input-panel:focus-within {
  border-color: rgba(129, 140, 248, 0.55);
  box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.14), 0 8px 30px rgba(2, 6, 18, 0.4);
}
.input-box {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-1);
  max-height: 160px;
}
.input-box::placeholder { color: var(--text-3); }
.input-box:disabled { opacity: 0.6; }

.send-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--text-3);
  background: var(--surface-3);
  border: 1px solid var(--border);
  transition: all 0.18s;
}
.send-btn.can {
  background: var(--gradient-primary);
  color: #08101f;
  border: none;
  box-shadow: 0 3px 14px rgba(129, 140, 248, 0.4);
}
.send-btn.can:hover { filter: brightness(1.1); }
.send-btn.stop { color: var(--danger); }
.input-hint {
  text-align: center;
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-3);
}
</style>

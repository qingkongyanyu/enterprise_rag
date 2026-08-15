<script setup lang="ts">
import { FileText, ChevronDown } from 'lucide-vue-next'
import { ref } from 'vue'

import type { SourceDoc } from '@/types'

const props = defineProps<{ sources: SourceDoc[] }>()
const expanded = ref(false)

const topSources = () => props.sources.slice(0, 3)
</script>

<template>
  <div v-if="props.sources.length" class="sources">
    <div class="sources-head">
      <span class="sources-label">
        <FileText :size="13" />
        引用来源 · {{ props.sources.length }}
      </span>
      <button
        v-if="props.sources.length > 3"
        class="sources-toggle"
        @click="expanded = !expanded"
      >
        {{ expanded ? '收起' : '展开全部' }}
        <ChevronDown :size="13" :class="{ rotated: expanded }" />
      </button>
    </div>

    <div class="sources-list" :class="{ open: expanded }">
      <div
        v-for="s in expanded ? props.sources : topSources()"
        :key="s.rank + s.chunk_id"
        class="source-chip"
        :title="s.snippet"
      >
        <span class="source-rank">#{{ s.rank }}</span>
        <span class="source-name">{{ s.source }}</span>
        <span class="source-score">{{ Math.round(s.score * 100) }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sources {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}
.sources-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.sources-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-3);
}
.sources-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--accent-1);
}
.sources-toggle svg { transition: transform 0.2s; }
.sources-toggle svg.rotated { transform: rotate(180deg); }
.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 74px;
  overflow: hidden;
  transition: max-height 0.25s ease;
}
.sources-list.open { max-height: 320px; overflow: auto; }
.source-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-size: 12px;
  cursor: default;
  transition: border-color 0.15s;
}
.source-chip:hover { border-color: var(--accent-2); }
.source-rank { color: var(--accent-1); font-weight: 600; }
.source-name { color: var(--text-2); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-score { color: var(--text-3); font-size: 11px; }
</style>

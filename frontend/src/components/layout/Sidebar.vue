<script setup lang="ts">
import { Database, Gauge, MessageSquareText, Sparkles } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { getSystemStats } from '@/api/system'

const route = useRoute()

const navItems = [
  { to: '/chat', label: '智能问答', icon: MessageSquareText },
  { to: '/knowledge', label: '知识库', icon: Database },
  { to: '/system', label: '系统状态', icon: Gauge },
]

const indexReady = ref<boolean | null>(null)
const llmReady = ref<boolean | null>(null)

onMounted(async () => {
  try {
    const stats = await getSystemStats()
    indexReady.value = stats.index_ready
    llmReady.value = stats.llm_configured
  } catch {
    /* 服务未启动 */
  }
})

const overallStatus = computed(() => {
  if (indexReady.value && llmReady.value) return 'all'
  if (indexReady.value === false || llmReady.value === false) return 'partial'
  return 'unknown'
})
</script>

<template>
  <aside class="sidebar glass">
    <!-- 品牌 -->
    <div class="brand">
      <div class="brand-mark"><Sparkles :size="20" /></div>
      <div class="brand-text">
        <div class="brand-name">知知</div>
        <div class="brand-sub">Enterprise RAG</div>
      </div>
    </div>

    <!-- 导航 -->
    <nav class="nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: route.path === item.to }"
      >
        <component :is="item.icon" :size="18" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="spacer" />

    <!-- 系统状态 -->
    <div class="status-card">
      <div class="status-title">系统状态</div>
      <div class="status-row">
        <span class="dot" :class="indexReady ? 'ok' : 'warn'" />
        <span>知识库索引</span>
        <span class="status-val">{{ indexReady === true ? '就绪' : indexReady === false ? '未构建' : '未知' }}</span>
      </div>
      <div class="status-row">
        <span class="dot" :class="llmReady ? 'ok' : 'warn'" />
        <span>大模型服务</span>
        <span class="status-val">{{ llmReady === true ? '已配置' : llmReady === false ? '未配置' : '未知' }}</span>
      </div>
      <div class="status-hint" :class="overallStatus">
        {{ overallStatus === 'all' ? '● 一切就绪，开始提问吧' : overallStatus === 'partial' ? '○ 存在未就绪项，见各页' : '○ 等待服务连接' }}
      </div>
    </div>

    <div class="version">v2.0 · FastAPI + Vue3</div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-w);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 18px 14px 14px;
  border-right: 1px solid var(--border);
  border-radius: 0;
  background: rgba(10, 16, 30, 0.72);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 8px 20px;
}
.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: #08101f;
  background: var(--gradient-primary);
  box-shadow: var(--shadow-glow);
}
.brand-name {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.brand-sub {
  font-size: 12px;
  color: var(--text-3);
  letter-spacing: 1px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 12px;
  border-radius: var(--radius-md);
  color: var(--text-2);
  font-size: 14px;
  font-weight: 500;
  transition: all 0.18s ease;
  position: relative;
}
.nav-item:hover {
  background: var(--surface-2);
  color: var(--text-1);
}
.nav-item.active {
  background: var(--surface-3);
  color: var(--text-1);
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 22%;
  bottom: 22%;
  width: 3px;
  border-radius: 3px;
  background: var(--gradient-primary);
}

.spacer { flex: 1; }

.status-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px 14px;
}
.status-title {
  font-size: 12px;
  color: var(--text-3);
  letter-spacing: 1px;
  margin-bottom: 10px;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-2);
  padding: 3px 0;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-3);
}
.dot.ok { background: var(--success); box-shadow: 0 0 8px rgba(52, 211, 153, 0.6); }
.dot.warn { background: var(--warning); box-shadow: 0 0 8px rgba(251, 191, 36, 0.5); }
.status-val {
  margin-left: auto;
  color: var(--text-1);
  font-size: 12px;
}
.status-hint {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border);
  font-size: 12px;
  color: var(--text-3);
}
.status-hint.all { color: var(--success); }
.status-hint.partial { color: var(--warning); }

.version {
  margin-top: 12px;
  text-align: center;
  font-size: 11px;
  color: var(--text-3);
}
</style>

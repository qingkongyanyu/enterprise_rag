<script setup lang="ts">
import { Activity, Bot, Cpu, FolderOpen, Gauge, RefreshCw } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

import { getMetrics, getSystemStats } from '@/api/system'
import type { Metrics, SystemStats } from '@/types'

const stats = ref<SystemStats | null>(null)
const metrics = ref<Metrics | null>(null)
const error = ref('')

async function load() {
  error.value = ''
  try {
    const [s, m] = await Promise.all([getSystemStats(), getMetrics()])
    stats.value = s
    metrics.value = m
  } catch (err) {
    error.value = (err as Error).message
  }
}

onMounted(load)

function statusDot(ok: boolean | null | undefined) {
  if (ok === true) return 'ok'
  if (ok === false) return 'err'
  return 'unknown'
}

function hostOf(url: string) {
  try {
    return new URL(url).host
  } catch {
    return url
  }
}
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="page-title">系统状态</h1>
        <p class="page-sub">服务运行情况与配置摘要（不含密钥）</p>
      </div>
      <button class="btn" @click="load"><RefreshCw :size="15" /> 刷新</button>
    </header>

    <div v-if="error" class="error-box card">{{ error }}</div>

    <template v-if="stats">
      <div class="grid">
        <!-- 应用 -->
        <section class="card panel">
          <h2 class="panel-title"><Gauge :size="16" /> 应用信息</h2>
          <div class="row"><span>服务版本</span><b>{{ stats.app_version }}</b></div>
          <div class="row"><span>向量索引</span><b>{{ stats.index_ready ? '已就绪' : '未构建' }}</b></div>
          <div class="row"><span>文档数</span><b>{{ stats.doc_count }}</b></div>
          <div class="row"><span>分块数</span><b>{{ stats.chunk_count }}</b></div>
        </section>

        <!-- LLM -->
        <section class="card panel">
          <h2 class="panel-title"><Bot :size="16" /> 大模型服务</h2>
          <div class="row">
            <span>配置状态</span>
            <b :class="statusDot(stats.llm_configured)">{{ stats.llm_configured ? '已配置' : '未配置' }}</b>
          </div>
          <div class="row"><span>模型</span><b>{{ stats.llm_model }}</b></div>
          <div class="row"><span>服务商</span><b>{{ hostOf(stats.llm_base_url) }}</b></div>
        </section>

        <!-- 检索 -->
        <section class="card panel">
          <h2 class="panel-title"><Cpu :size="16" /> 检索配置</h2>
          <div class="row"><span>嵌入模型</span><b>{{ stats.embedding_model }}</b></div>
          <div class="row"><span>最终 Top-K</span><b>{{ stats.final_top_k }}</b></div>
          <div class="row"><span>重排</span><b :class="statusDot(stats.enable_rerank)">{{ stats.enable_rerank ? '开启' : '关闭' }}</b></div>
        </section>

        <!-- 运行指标 -->
        <section class="card panel">
          <h2 class="panel-title"><Activity :size="16" /> 运行指标</h2>
          <div class="row"><span>累计对话</span><b>{{ metrics?.chat_count ?? '-' }}</b></div>
          <div class="row"><span>平均耗时</span><b>{{ metrics?.avg_elapsed_ms ?? '-' }} ms</b></div>
          <div class="row"><span>缓存命中</span><b>{{ metrics?.cache_hits ?? '-' }}</b></div>
        </section>
      </div>

      <!-- 目录 -->
      <section class="card panel">
        <h2 class="panel-title"><FolderOpen :size="16" /> 数据目录</h2>
        <div class="dir-row"><span>文档目录</span><code>{{ stats.knowledge_docs_dir }}</code></div>
        <div class="dir-row"><span>索引目录</span><code>{{ stats.vector_store_dir }}</code></div>
      </section>
    </template>

    <div v-else class="loading card">正在加载系统信息…</div>
  </div>
</template>

<style scoped>
.page {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 26px 32px 40px;
  max-width: 980px;
  margin: 0 auto;
  width: 100%;
}
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 22px;
}
.page-title { font-size: 24px; font-weight: 700; }
.page-sub { color: var(--text-2); margin-top: 6px; font-size: 14px; }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}
.panel { padding: 20px; }
.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-2);
  margin-bottom: 14px;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 0;
  font-size: 13px;
  color: var(--text-2);
}
.row b { color: var(--text-1); font-weight: 500; font-size: 13px; }
.row b.ok { color: var(--success); }
.row b.err { color: var(--danger); }
.row b.unknown { color: var(--warning); }
.dir-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  font-size: 13px;
  color: var(--text-2);
}
.dir-row code {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-1);
  background: var(--surface-2);
  padding: 3px 8px;
  border-radius: 6px;
  word-break: break-all;
}
.error-box { padding: 16px; color: var(--danger); margin-bottom: 16px; }
.loading { padding: 40px; text-align: center; color: var(--text-3); }
</style>

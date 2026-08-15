<script setup lang="ts">
import {
  AlertTriangle,
  Database,
  FileText,
  HardDrive,
  Layers,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { useKnowledgeStore } from '@/stores/knowledge'

const kb = useKnowledgeStore()
const fileInput = ref<HTMLInputElement | null>(null)
const uploadMsg = ref('')
const uploadError = ref('')
const uploading = ref(false)

const categories = computed(() =>
  Object.entries(kb.overview?.categories ?? {}).sort((a, b) => b[1] - a[1]),
)

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}
function formatTime(t: string) {
  return t ? t.replace('T', ' ').slice(0, 16) : '-'
}

async function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  uploadMsg.value = ''
  uploadError.value = ''
  try {
    uploadMsg.value = await kb.upload(file)
  } catch (err) {
    uploadError.value = (err as Error).message
  } finally {
    uploading.value = false
  }
}

async function onDelete(name: string) {
  if (!window.confirm(`确定删除文档「${name}」？删除后将同步重建索引。`)) return
  try {
    await kb.remove(name)
  } catch (err) {
    uploadError.value = (err as Error).message
  }
}

onMounted(() => kb.refresh())
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="page-title">知识库管理</h1>
        <p class="page-sub">文档上传、索引构建与检索统计</p>
      </div>
      <div class="head-actions">
        <button class="btn" :disabled="kb.loading" @click="kb.refresh()">
          <RefreshCw :size="15" :class="{ spin: kb.loading }" />
          刷新
        </button>
        <input ref="fileInput" type="file" accept=".txt,.md" hidden @change="onPickFile" />
        <button class="btn btn-primary" :disabled="uploading" @click="fileInput?.click()">
          <Upload :size="15" />
          {{ uploading ? '上传中…' : '上传文档' }}
        </button>
      </div>
    </header>

    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card card">
        <div class="stat-icon" :class="kb.ready ? 'ok' : 'warn'">
          <Database :size="20" />
        </div>
        <div>
          <div class="stat-label">索引状态</div>
          <div class="stat-value" :class="kb.ready ? 'ok' : 'warn'">
            {{ kb.ready ? '已就绪' : '未构建' }}
          </div>
        </div>
      </div>
      <div class="stat-card card">
        <div class="stat-icon accent"><FileText :size="20" /></div>
        <div>
          <div class="stat-label">文档总数</div>
          <div class="stat-value">{{ kb.totalDocs }}</div>
        </div>
      </div>
      <div class="stat-card card">
        <div class="stat-icon violet"><Layers :size="20" /></div>
        <div>
          <div class="stat-label">分块总数</div>
          <div class="stat-value">{{ kb.totalChunks }}</div>
        </div>
      </div>
      <div class="stat-card card">
        <div class="stat-icon cyan"><HardDrive :size="20" /></div>
        <div>
          <div class="stat-label">分类数量</div>
          <div class="stat-value">{{ categories.length }}</div>
        </div>
      </div>
    </div>

    <!-- 操作提示条 -->
    <div class="notice card" :class="{ warn: !kb.ready }">
      <AlertTriangle v-if="!kb.ready" :size="17" />
      <span>
        {{
          kb.ready
            ? '索引已构建，可直接在「智能问答」中提问。'
            : '索引尚未构建：点击下方「构建索引」，或命令行执行 python scripts/init_knowledge.py'
        }}
      </span>
      <button class="btn btn-primary" :disabled="kb.building || kb.totalDocs === 0" @click="kb.rebuild">
        <RefreshCw :size="15" :class="{ spin: kb.building }" />
        {{ kb.building ? '构建中…' : '构建索引' }}
      </button>
    </div>

    <div v-if="kb.message" class="notice card success">{{ kb.message }}</div>
    <div v-if="uploadMsg" class="notice card success">{{ uploadMsg }}</div>
    <div v-if="uploadError" class="notice card err">{{ uploadError }}</div>

    <!-- 分类分布 -->
    <div v-if="categories.length" class="cat-row">
      <div v-for="[cat, n] in categories" :key="cat" class="cat-chip card">
        <span class="cat-name">{{ cat }}</span>
        <span class="cat-num">{{ n }}</span>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="table-card card">
      <div class="table-head">
        <span>文档列表</span>
        <span>{{ kb.totalDocs }} 篇</span>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>分类</th>
              <th>大小</th>
              <th>更新时间</th>
              <th class="th-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in kb.overview?.docs ?? []" :key="doc.name">
              <td class="cell-name"><FileText :size="14" />{{ doc.name }}</td>
              <td><span class="badge">{{ doc.category }}</span></td>
              <td class="cell-muted">{{ formatSize(doc.size) }}</td>
              <td class="cell-muted">{{ formatTime(doc.updated_at) }}</td>
              <td class="td-right">
                <button class="row-del" title="删除" @click="onDelete(doc.name)">
                  <Trash2 :size="14" />
                </button>
              </td>
            </tr>
            <tr v-if="!kb.overview?.docs?.length">
              <td colspan="5" class="table-empty">暂无文档，点击右上角「上传文档」添加</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 26px 32px 40px;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}
.page-title { font-size: 24px; font-weight: 700; }
.page-sub { color: var(--text-2); margin-top: 6px; font-size: 14px; }
.head-actions { display: flex; gap: 10px; }

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  background: var(--surface-2);
  color: var(--text-2);
}
.stat-icon.ok { color: var(--success); background: rgba(52, 211, 153, 0.12); }
.stat-icon.warn { color: var(--warning); background: rgba(251, 191, 36, 0.12); }
.stat-icon.accent { color: var(--accent-1); background: rgba(34, 211, 238, 0.12); }
.stat-icon.violet { color: var(--accent-2); background: rgba(129, 140, 248, 0.14); }
.stat-icon.cyan { color: var(--accent-3); background: rgba(232, 121, 249, 0.12); }
.stat-label { font-size: 12px; color: var(--text-3); }
.stat-value { font-size: 22px; font-weight: 700; margin-top: 2px; }
.stat-value.ok { color: var(--success); }
.stat-value.warn { color: var(--warning); }

.notice {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  margin-bottom: 14px;
  font-size: 14px;
  color: var(--text-2);
}
.notice .btn { margin-left: auto; }
.notice.warn { border-color: rgba(251, 191, 36, 0.3); color: var(--text-2); }
.notice.success { border-color: rgba(52, 211, 153, 0.3); color: var(--success); }
.notice.err { border-color: rgba(248, 113, 113, 0.35); color: var(--danger); }

.cat-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border-radius: 999px;
  font-size: 13px;
}
.cat-name { color: var(--text-1); }
.cat-num {
  background: var(--gradient-primary);
  color: #08101f;
  font-weight: 700;
  padding: 1px 9px;
  border-radius: 999px;
  font-size: 12px;
}

.table-card { overflow: hidden; }
.table-head {
  display: flex;
  justify-content: space-between;
  padding: 15px 20px;
  font-size: 13px;
  color: var(--text-3);
  border-bottom: 1px solid var(--border);
  letter-spacing: 0.5px;
}
.table-wrap { overflow-x: auto; }
.table { width: 100%; border-collapse: collapse; font-size: 14px; }
.table th {
  text-align: left;
  padding: 12px 20px;
  font-size: 12px;
  color: var(--text-3);
  font-weight: 500;
  border-bottom: 1px solid var(--border);
}
.table td { padding: 12px 20px; border-bottom: 1px solid var(--border); }
.table tbody tr { transition: background 0.12s; }
.table tbody tr:hover { background: var(--surface); }
.cell-name { display: flex; align-items: center; gap: 8px; color: var(--text-1); }
.cell-muted { color: var(--text-3); font-size: 13px; }
.th-right, .td-right { text-align: right; }
.row-del {
  color: var(--text-3);
  padding: 5px;
  border-radius: 7px;
  transition: all 0.15s;
}
.row-del:hover { color: var(--danger); background: rgba(248, 113, 113, 0.12); }
.table-empty { text-align: center; color: var(--text-3); padding: 30px !important; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>

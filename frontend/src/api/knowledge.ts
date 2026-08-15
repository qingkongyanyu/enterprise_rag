import { request } from './http'
import type { KnowledgeOverview, RebuildResult } from '@/types'

/** 知识库概览 */
export async function getOverview(): Promise<KnowledgeOverview> {
  return request<KnowledgeOverview>('/api/v1/knowledge/documents')
}

/** 构建 / 重建索引 */
export async function rebuildIndex(): Promise<RebuildResult> {
  return request<RebuildResult>('/api/v1/knowledge/rebuild', { method: 'POST' })
}

/** 上传文档 */
export async function uploadDocument(file: File): Promise<{ name: string }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${import.meta.env.VITE_API_BASE ?? ''}/api/v1/knowledge/upload`, {
    method: 'POST',
    body: form,
  })
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(body?.message || body?.detail || '上传失败')
  }
  return body?.data ?? body
}

/** 删除文档 */
export async function deleteDocument(name: string): Promise<void> {
  await request(`/api/v1/knowledge/documents/${encodeURIComponent(name)}`, { method: 'DELETE' })
}

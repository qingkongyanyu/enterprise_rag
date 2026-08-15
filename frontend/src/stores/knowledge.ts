import { defineStore } from 'pinia'

import { deleteDocument, getOverview, rebuildIndex, uploadDocument } from '@/api/knowledge'
import type { KnowledgeOverview } from '@/types'

export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    overview: null as KnowledgeOverview | null,
    loading: false,
    building: false,
    message: '' as string,
  }),

  getters: {
    ready: (s) => s.overview?.ready ?? false,
    totalDocs: (s) => s.overview?.total_docs ?? 0,
    totalChunks: (s) => s.overview?.total_chunks ?? 0,
  },

  actions: {
    async refresh() {
      this.loading = true
      try {
        this.overview = await getOverview()
      } finally {
        this.loading = false
      }
    },

    async rebuild() {
      if (this.building) return
      this.building = true
      this.message = ''
      try {
        const result = await rebuildIndex()
        await this.refresh()
        this.message = `✅ 索引构建完成：${result.doc_count} 篇文档 → ${result.chunk_count} 个分块，耗时 ${result.elapsed_ms}ms`
      } catch (err) {
        this.message = `❌ ${(err as Error).message}`
        throw err
      } finally {
        this.building = false
      }
    },

    async upload(file: File) {
      try {
        await uploadDocument(file)
        await this.refresh()
        return `✅ 已上传「${file.name}」并完成索引更新`
      } catch (err) {
        throw new Error((err as Error).message)
      }
    },

    async remove(name: string) {
      await deleteDocument(name)
      await this.refresh()
    },
  },
})

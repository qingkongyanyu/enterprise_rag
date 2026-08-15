/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API 基础路径，默认为同源（后端直接托管 dist） */
  readonly VITE_API_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

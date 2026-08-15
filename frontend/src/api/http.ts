import type { ApiResponse } from '@/types'

const BASE = import.meta.env.VITE_API_BASE ?? ''

/**
 * 统一请求封装：解析 { code, message, data } 包裹结构。
 * code !== 0 或 HTTP 非 2xx 时抛出带可读信息的 Error。
 */
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  })

  let body: ApiResponse<T> | null = null
  try {
    body = (await res.json()) as ApiResponse<T>
  } catch {
    /* 非 JSON 响应 */
  }

  if (!res.ok) {
    const msg =
      body?.message ||
      (body as { detail?: string } | null)?.detail ||
      `请求失败 (HTTP ${res.status})`
    throw new Error(msg)
  }
  if (body && typeof body.code === 'number' && body.code !== 0) {
    throw new Error(body.message || '接口返回错误')
  }
  return (body?.data ?? body) as T
}

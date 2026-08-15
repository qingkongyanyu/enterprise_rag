import { request } from './http'
import type { Metrics, SystemStats } from '@/types'

/** 健康检查 */
export async function healthCheck(): Promise<{ status: string }> {
  return request<{ status: string }>('/health')
}

/** 系统状态 */
export async function getSystemStats(): Promise<SystemStats> {
  return request<SystemStats>('/api/v1/system/stats')
}

/** 运行指标 */
export async function getMetrics(): Promise<Metrics> {
  return request<Metrics>('/api/v1/system/metrics')
}

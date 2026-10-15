import client from './client'
import type { LiveAnalyticsStats } from '@/types'

export async function getCurrentLiveAnalytics(): Promise<LiveAnalyticsStats> {
  const { data } = await client.get('/api/analytics/live/current')
  return data
}

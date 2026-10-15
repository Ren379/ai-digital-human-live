import client from './client'
import type { LivestreamStatus, LivetalkingSession } from '@/types'

export async function getLivetalkingSessions(): Promise<{ code: number; sessions: LivetalkingSession[] }> {
  const { data } = await client.get('/api/livetalking/sessions')
  return data
}

export async function startLivestream(roomId: string, sessionId: string, platform: string = 'bilibili'): Promise<void> {
  await client.post('/api/livestream/start', { room_id: roomId || '', session_id: sessionId, platform })
}

export async function stopLivestream(): Promise<void> {
  await client.post('/api/livestream/stop')
}

export async function getLivestreamStatus(): Promise<LivestreamStatus> {
  const { data } = await client.get('/api/livestream/status')
  return data
}

export async function interruptLivestream(): Promise<void> {
  await client.post('/api/livestream/interrupt')
}

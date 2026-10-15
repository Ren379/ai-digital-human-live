import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getLivestreamStatus, startLivestream as apiStart, stopLivestream as apiStop, getLivetalkingSessions } from '@/api/livestream'
import type { LivestreamStatus, LivetalkingSession } from '@/types'
import { wsClient } from '@/api/ws'

export const useLivestreamStore = defineStore('livestream', () => {
  const running = ref(false)
  const roomId = ref('')
  const sessionId = ref('')
  const danmakuCount = ref(0)
  const isSpeaking = ref(false)
  const ltBaseUrl = ref('http://127.0.0.1:8010')
  const ltSessions = ref<LivetalkingSession[]>([])
  const fetchingSessions = ref(false)

  async function fetchStatus() {
    try {
      const status = await getLivestreamStatus()
      running.value = status.running
      roomId.value = status.room_id
      sessionId.value = status.session_id
      danmakuCount.value = status.danmaku_count
      isSpeaking.value = status.is_speaking
    } catch {
      // ignore
    }
  }

  async function fetchSessions() {
    fetchingSessions.value = true
    try {
      const result = await getLivetalkingSessions()
      ltSessions.value = result.sessions || []
    } catch {
      ltSessions.value = []
    } finally {
      fetchingSessions.value = false
    }
  }

  async function startLive(rid: string, sid: string, platform: string = 'bilibili') {
    await apiStart(rid, sid, platform)
    running.value = true
    roomId.value = rid
    sessionId.value = sid
    danmakuCount.value = 0
  }

  async function stopLive() {
    await apiStop()
    running.value = false
  }

  // Listen to WebSocket status events
  wsClient.on('status_change', (msg) => {
    running.value = msg.running
    if (msg.room_id) roomId.value = msg.room_id
  })

  wsClient.on('danmaku', () => { danmakuCount.value++ })
  wsClient.on('gift', () => { danmakuCount.value++ })

  return {
    running, roomId, sessionId, danmakuCount, isSpeaking,
    ltBaseUrl, ltSessions, fetchingSessions,
    fetchStatus, fetchSessions, startLive, stopLive,
  }
})

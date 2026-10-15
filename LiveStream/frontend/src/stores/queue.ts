import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { QueueItem } from '@/types'
import { wsClient } from '@/api/ws'

export const useQueueStore = defineStore('queue', () => {
  const highItems = ref<QueueItem[]>([])
  const lowItems = ref<QueueItem[]>([])
  const currentItem = ref<{ id: string; source: string; content_preview: string } | null>(null)

  function updateFromSnapshot(snapshot: { high: QueueItem[]; low: QueueItem[] }) {
    highItems.value = snapshot.high || []
    lowItems.value = snapshot.low || []
  }

  function startPolling() {
    // no-op, 队列现在通过 WS 实时推送，无需 HTTP 轮询
  }

  function stopPolling() {
    highItems.value = []
    lowItems.value = []
    currentItem.value = null
  }

  // 队列变更由后端广播（put_high/put_low/get_next 触发）
  wsClient.on('queue_update', (msg) => {
    if (msg.data) {
      updateFromSnapshot(msg.data)
    }
  })

  // 标记当前正在播放的 item
  wsClient.on('playback_started', (msg) => {
    if (msg.item_id) {
      currentItem.value = {
        id: msg.item_id,
        source: msg.source || '',
        content_preview: msg.content_preview || '',
      }
    }
  })

  return { highItems, lowItems, currentItem, updateFromSnapshot, startPolling, stopPolling }
})

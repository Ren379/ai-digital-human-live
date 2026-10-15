<template>
  <el-card>
    <template #header>
      <span><el-icon><ChatLineSquare /></el-icon> 实时弹幕流</span>
      <el-tag size="small" style="margin-left: 8px" :type="store.running ? 'success' : 'info'">
        {{ store.running ? '接收中' : '未连接' }}
      </el-tag>
    </template>
    <div ref="scrollRef" style="height: 400px; overflow-y: auto; padding: 8px">
      <div v-if="events.length === 0" style="color: #999; text-align: center; padding-top: 180px">
        暂无弹幕消息
      </div>
      <div
        v-for="(evt, i) in events"
        :key="i"
        :style="{ padding: '4px 0', borderBottom: '1px solid #f0f0f0', fontSize: '13px' }"
      >
        <el-tag :type="tagType(evt.type)" size="small" style="margin-right: 6px">
          {{ tagLabel(evt.type) }}
        </el-tag>
        <span style="color: #409eff; margin-right: 6px">{{ evt.sender }}</span>
        <span>{{ evt.content }}</span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { useLivestreamStore } from '@/stores/livestream'
import { wsClient } from '@/api/ws'
import type { DanmakuEvent } from '@/types'

const store = useLivestreamStore()
const events = ref<DanmakuEvent[]>([])
const scrollRef = ref<HTMLElement>()

function tagType(type: string): string {
  const map: Record<string, string> = { danmaku: '', gift: 'danger', follow: 'success', enter: 'info' }
  return map[type] || ''
}

function tagLabel(type: string): string {
  const map: Record<string, string> = { danmaku: '弹幕', gift: '礼物', follow: '关注', enter: '进入' }
  return map[type] || type
}

function handleMessage(msg: any) {
  const evt: DanmakuEvent = {
    type: msg.type,
    platform: msg.platform || '',
    sender: msg.sender || '',
    content: msg.content || '',
    timestamp: msg.timestamp || Date.now(),
  }
  events.value.push(evt)
  // Keep max 200 items
  if (events.value.length > 200) {
    events.value.splice(0, events.value.length - 200)
  }
  // Auto-scroll
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
}

onMounted(() => {
  wsClient.on('danmaku', handleMessage)
  wsClient.on('gift', handleMessage)
  wsClient.on('follow', handleMessage)
  wsClient.on('enter', handleMessage)
})

onUnmounted(() => {
  wsClient.off('danmaku', handleMessage)
  wsClient.off('gift', handleMessage)
  wsClient.off('follow', handleMessage)
  wsClient.off('enter', handleMessage)
})
</script>

<template>
  <el-card>
    <template #header>
      <div class="analytics-header">
        <span><el-icon><DataAnalysis /></el-icon> 直播运营数据</span>
        <el-tag :type="anchorStatus.type" size="small">
          {{ anchorStatus.label }}
        </el-tag>
      </div>
    </template>

    <el-row :gutter="12">
      <el-col v-for="item in metrics" :key="item.label" :span="8">
        <div class="metric-item">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getCurrentLiveAnalytics } from '@/api/analytics'
import { useLivestreamStore } from '@/stores/livestream'
import { useQueueStore } from '@/stores/queue'
import type { LiveAnalyticsStats } from '@/types'

const livestream = useLivestreamStore()
const queue = useQueueStore()

const stats = ref<LiveAnalyticsStats>({
  running: false,
  started_at: null,
  duration_seconds: 0,
  danmaku_count: 0,
  ai_reply_count: 0,
  auto_script_count: 0,
  product_consultation_count: 0,
  intent_consultation_count: 0,
})

let refreshTimer: ReturnType<typeof setInterval> | null = null

function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds || 0))
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60
  return [hours, minutes, remainingSeconds]
    .map((part) => String(part).padStart(2, '0'))
    .join(':')
}

const anchorStatus = computed(() => {
  if (!livestream.running) {
    return { label: '已停止', type: 'info' as const }
  }

  const source = queue.currentItem?.source
  if (source === 'script') {
    return { label: '自动话术播报中', type: 'warning' as const }
  }
  if (source && ['danmaku', 'gift', 'follow'].includes(source)) {
    return { label: '回答观众问题', type: 'success' as const }
  }
  if (livestream.isSpeaking) {
    return { label: '回答观众问题', type: 'success' as const }
  }
  return { label: '等待互动', type: 'info' as const }
})

const metrics = computed(() => [
  { label: '直播时长', value: formatDuration(stats.value.duration_seconds) },
  { label: '弹幕数量', value: stats.value.danmaku_count },
  { label: 'AI回复', value: stats.value.ai_reply_count },
  { label: '自动话术', value: stats.value.auto_script_count },
  { label: '产品咨询', value: stats.value.product_consultation_count },
  { label: '意向咨询', value: stats.value.intent_consultation_count },
])

async function refreshAnalytics() {
  try {
    stats.value = await getCurrentLiveAnalytics()
  } catch {
    // 保留上一次成功获取的数据
  }
}

onMounted(() => {
  void refreshAnalytics()
  refreshTimer = setInterval(() => {
    void refreshAnalytics()
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.analytics-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.metric-item {
  margin-bottom: 12px;
  padding: 14px 10px;
  text-align: center;
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.metric-label {
  margin-bottom: 8px;
  color: #909399;
  font-size: 12px;
}

.metric-value {
  color: #303133;
  font-size: 22px;
  font-weight: 600;
  line-height: 1;
}
</style>

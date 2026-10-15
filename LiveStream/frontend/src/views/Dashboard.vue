<template>
  <div>
    <h1 style="margin: 0 0 20px 0; font-size: 22px">直播控制面板</h1>

    <!-- Session 选择 + 控制按钮 -->
    <el-card style="margin-bottom: 20px">
      <el-row :gutter="16" align="middle">
        <!-- LiveTalking URL -->
        <!-- <el-col :span="6">
          <el-input v-model="store.ltBaseUrl" placeholder="LiveTalking URL" size="default">
            <template #prepend>URL</template>
          </el-input>
        </el-col> -->
        <!-- Session 选择 -->
        <el-col :span="8">
          <el-select
            v-model="store.sessionId"
            placeholder="选择 LiveTalking Session"
            style="width: 100%"
            :loading="store.fetchingSessions"
          >
            <el-option
              v-for="s in store.ltSessions"
              :key="s.sessionid"
              :label="`${s.sessionid.slice(0, 8)}... (${s.model || '?'} / ${s.transport || '?'})`"
              :value="s.sessionid"
            />
          </el-select>
        </el-col>
        <el-col :span="2">
          <el-button @click="store.fetchSessions()" :loading="store.fetchingSessions" type="primary" plain>
            刷新
          </el-button>
        </el-col>
        <!-- 平台 -->
        <el-col :span="3">
          <el-select v-model="platform" :disabled="store.running" size="default" style="width: 100%">
            <el-option label="抖音" value="douyin" />
            <el-option label="视频号" value="wxlive" />
            <el-option label="B站" value="bilibili" />
          </el-select>
        </el-col>
        <!-- 房间号（仅 B 站需要） -->
        <el-col v-if="platform === 'bilibili'" :span="3">
          <el-input v-model="roomId" placeholder="房间号" size="default" :disabled="store.running" />
        </el-col>
        <!-- 控制按钮 -->
        <el-col :span="5">
          <el-button
            v-if="!store.running"
            type="success"
            :disabled="!canStart"
            @click="handleStart"
          >
            <el-icon><VideoPlay /></el-icon> 开始直播
          </el-button>
          <el-button v-else type="danger" @click="handleStop">
            <el-icon><VideoPause /></el-icon> 停止直播
          </el-button>
          <!-- <el-button v-if="store.running" @click="handleInterrupt" type="warning" plain>
            打断
          </el-button> -->
        </el-col>
      </el-row>
    </el-card>

    <AvatarVideo
      :base-url="store.ltBaseUrl"
      @session-created="handleSessionCreated"
    />

    <!-- 模拟弹幕测试 -->
    <el-card v-if="store.running" style="margin-bottom: 20px">
      <template #header>
        <span><el-icon><Tools /></el-icon> 弹幕测试</span>
      </template>
      <el-row :gutter="8" align="middle">
        <el-col :span="4">
          <el-select v-model="mockType" size="small" style="width: 100%">
            <el-option label="弹幕" value="danmaku" />
            <el-option label="礼物" value="gift" />
            <el-option label="关注" value="follow" />
          </el-select>
        </el-col>
        <el-col :span="3">
          <el-input v-model="mockSender" size="small" placeholder="发送者" />
        </el-col>
        <el-col :span="6">
          <el-input v-model="mockContent" size="small" placeholder="内容" @keyup.enter="sendMock" />
        </el-col>
        <el-col :span="2">
          <el-button size="small" type="primary" @click="sendMock" :loading="mockSending">发送</el-button>
        </el-col>
        <el-col :span="9">
          <el-button size="small" @click="quickMock('danmaku', '观众A', '主播好厉害！')">弹幕</el-button>
          <el-button size="small" @click="quickMock('danmaku', '观众B', '今天天气怎么样')">知识问答</el-button>
          <el-button size="small" @click="quickMock('gift', '大佬', '火箭 x1')" type="warning">礼物</el-button>
          <el-button size="small" @click="quickMock('follow', '新粉丝', '')" type="success">关注</el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="16">
      <!-- 弹幕流 -->
      <el-col :span="14">
        <LiveAnalytics style="margin-bottom: 16px" />
        <LiveChat />
      </el-col>
      <!-- 队列状态 -->
      <el-col :span="10">
        <QueueStatus />
      </el-col>
    </el-row>

    <!-- 状态栏 -->
    <div style="margin-top: 16px; color: #909399; font-size: 13px">
      <el-tag :type="store.running ? 'success' : 'info'" size="small">
        {{ store.running ? '直播中' : '已停止' }}
      </el-tag>
      <span v-if="store.running" style="margin-left: 12px">
        房间: {{ store.roomId }} | Session: {{ store.sessionId?.slice(0, 12) }}... |
        弹幕数: {{ store.danmakuCount }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useLivestreamStore } from '@/stores/livestream'
import { useQueueStore } from '@/stores/queue'
import LiveChat from '@/components/dashboard/LiveChat.vue'
import QueueStatus from '@/components/dashboard/QueueStatus.vue'
import AvatarVideo from '@/components/dashboard/AvatarVideo.vue'
import LiveAnalytics from '@/components/dashboard/LiveAnalytics.vue'
import client from '@/api/client'

const store = useLivestreamStore()
const queueStore = useQueueStore()
const roomId = ref('')
const platform = ref('douyin')

const mockType = ref('danmaku')
const mockSender = ref('测试观众')
const mockContent = ref('主播好厉害！')
const mockSending = ref(false)

async function sendMock() {
  mockSending.value = true
  try {
    const form = new FormData()
    form.append('content', mockContent.value)
    form.append('sender', mockSender.value)
    form.append('msg_type', mockType.value)
    await client.post('/api/mock/danmaku', form)
  } catch {
    // error handled by interceptor
  } finally {
    mockSending.value = false
  }
}

async function quickMock(type: string, sender: string, content: string) {
  mockType.value = type
  mockSender.value = sender
  mockContent.value = content
  await sendMock()
}

const canStart = computed(() => {
  if (!store.sessionId) return false
  if (platform.value === 'bilibili' && !roomId.value) return false
  return true
})

onMounted(() => {
  store.fetchStatus()
  store.fetchSessions()
})

async function handleSessionCreated(sessionId: string) {
  await store.fetchStatus()
  const wasRunning = store.running
  const previousSessionId = store.sessionId
  const activeRoomId = store.roomId || roomId.value

  store.sessionId = sessionId
  await store.fetchSessions()

  if (wasRunning && previousSessionId !== sessionId) {
    try {
      await store.stopLive()
      queueStore.stopPolling()
      await store.startLive(activeRoomId, sessionId, platform.value)
      queueStore.startPolling()
      ElMessage.success('数字人视频已连接，直播已切换至当前 Session')
    } catch {
      store.sessionId = previousSessionId
      // error handled by interceptor
    }
    return
  }

  ElMessage.success('数字人视频已连接')
}

async function handleStart() {
  try {
    await store.startLive(roomId.value, store.sessionId, platform.value)
    queueStore.startPolling()
    ElMessage.success('直播已启动')
  } catch {
    // error handled by interceptor
  }
}

async function handleStop() {
  try {
    await store.stopLive()
    queueStore.stopPolling()
    ElMessage.success('直播已停止')
  } catch {
    // error handled by interceptor
  }
}

async function handleInterrupt() {
  try {
    const { interruptLivestream } = await import('@/api/livestream')
    await interruptLivestream()
    ElMessage.info('已打断')
  } catch {
    // ignore
  }
}
</script>

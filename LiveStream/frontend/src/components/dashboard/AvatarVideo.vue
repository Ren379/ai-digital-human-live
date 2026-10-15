<template>
  <el-card class="avatar-video-card">
    <template #header>
      <div class="card-header">
        <span><el-icon><VideoCamera /></el-icon> 数字人画面</span>
        <div class="connection-status">
          <el-tag :type="statusTagType" size="small">{{ statusText }}</el-tag>
          <el-button
            v-if="connectionStatus !== 'connected'"
            type="primary"
            size="small"
            :loading="connectionStatus === 'connecting'"
            @click="connect"
          >
            连接数字人
          </el-button>
          <el-button v-else size="small" @click="disconnect">断开</el-button>
        </div>
      </div>
    </template>

    <div class="video-container">
      <video ref="videoRef" autoplay playsinline muted controls />
      <audio ref="audioRef" autoplay />
      <div v-if="connectionStatus !== 'connected'" class="video-placeholder">
        {{ errorMessage || '点击“连接数字人”建立 LiveTalking WebRTC 连接' }}
      </div>
    </div>

    <div v-if="sessionId" class="session-info">
      Session: {{ sessionId }}
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'failed'

interface OfferAnswer {
  sdp: string
  type: RTCSdpType
  sessionid: string
}

const props = withDefaults(defineProps<{
  baseUrl?: string
}>(), {
  baseUrl: 'http://127.0.0.1:8010',
})

const emit = defineEmits<{
  sessionCreated: [sessionId: string]
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const audioRef = ref<HTMLAudioElement | null>(null)
const connectionStatus = ref<ConnectionStatus>('disconnected')
const sessionId = ref('')
const errorMessage = ref('')
let peerConnection: RTCPeerConnection | null = null
let mediaStream: MediaStream | null = null

const statusText = computed(() => ({
  disconnected: '未连接',
  connecting: '连接中',
  connected: '已连接',
  failed: '连接失败',
}[connectionStatus.value]))

const statusTagType = computed(() => ({
  disconnected: 'info',
  connecting: 'warning',
  connected: 'success',
  failed: 'danger',
}[connectionStatus.value] as 'info' | 'warning' | 'success' | 'danger'))

function waitForIceGatheringComplete(pc: RTCPeerConnection): Promise<void> {
  if (pc.iceGatheringState === 'complete') return Promise.resolve()

  return new Promise((resolve) => {
    const handleStateChange = () => {
      if (pc.iceGatheringState === 'complete') {
        pc.removeEventListener('icegatheringstatechange', handleStateChange)
        resolve()
      }
    }
    pc.addEventListener('icegatheringstatechange', handleStateChange)
  })
}

async function playAudio() {
  const audio = audioRef.value
  if (!audio) return

  console.log('[AvatarVideo] audio.readyState:', audio.readyState)
  console.log('[AvatarVideo] audio.paused:', audio.paused)
  try {
    await audio.play()
    console.log('[AvatarVideo] audio.play() succeeded')
    console.log('[AvatarVideo] audio.readyState:', audio.readyState)
    console.log('[AvatarVideo] audio.paused:', audio.paused)
  } catch (error) {
    console.error('[AvatarVideo] audio.play() failed:', error)
  }
}

async function connect() {
  disconnect()
  connectionStatus.value = 'connecting'
  errorMessage.value = ''

  const pc = new RTCPeerConnection()
  peerConnection = pc
  const stream = new MediaStream()
  mediaStream = stream
  if (videoRef.value) videoRef.value.srcObject = stream
  if (audioRef.value) {
    audioRef.value.srcObject = stream
    audioRef.value.onloadedmetadata = () => { void playAudio() }
  }
  pc.addTransceiver('video', { direction: 'recvonly' })
  pc.addTransceiver('audio', { direction: 'recvonly' })
  pc.ontrack = (event) => {
    if (mediaStream !== stream) return
    if (!stream.getTracks().some((track) => track.id === event.track.id)) {
      stream.addTrack(event.track)
    }
    console.log('[AvatarVideo] track.kind:', event.track.kind)
    console.log('[AvatarVideo] stream.getAudioTracks().length:', stream.getAudioTracks().length)
    if (event.track.kind === 'audio' && audioRef.value?.readyState) {
      void playAudio()
    }
  }
  pc.addEventListener('connectionstatechange', () => {
    if (peerConnection !== pc) return
    if (pc.connectionState === 'connected') {
      connectionStatus.value = 'connected'
    } else if (pc.connectionState === 'failed') {
      connectionStatus.value = 'failed'
      errorMessage.value = 'WebRTC 连接失败，请确认 LiveTalking 8010 服务正常'
    } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'closed') {
      connectionStatus.value = 'disconnected'
    }
  })

  try {
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await waitForIceGatheringComplete(pc)

    const response = await fetch(`${props.baseUrl.replace(/\/$/, '')}/offer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sdp: pc.localDescription?.sdp,
        type: pc.localDescription?.type,
      }),
    })
    if (!response.ok) throw new Error(`LiveTalking 返回 HTTP ${response.status}`)

    const answer = await response.json() as OfferAnswer
    await pc.setRemoteDescription({ sdp: answer.sdp, type: answer.type })
    sessionId.value = answer.sessionid
    emit('sessionCreated', answer.sessionid)
  } catch (error) {
    if (peerConnection === pc) {
      connectionStatus.value = 'failed'
      errorMessage.value = error instanceof Error ? error.message : '无法连接 LiveTalking'
      pc.close()
      peerConnection = null
    }
  }
}

function disconnect() {
  if (peerConnection) {
    peerConnection.close()
    peerConnection = null
  }
  if (videoRef.value) videoRef.value.srcObject = null
  if (audioRef.value) {
    audioRef.value.onloadedmetadata = null
    audioRef.value.srcObject = null
  }
  mediaStream = null
  sessionId.value = ''
  connectionStatus.value = 'disconnected'
}

onBeforeUnmount(disconnect)
</script>

<style scoped>
.avatar-video-card {
  margin-bottom: 20px;
}

.card-header,
.connection-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: 6px;
  background: #101010;
}

video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #a8abb2;
  text-align: center;
}

.session-info {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
  word-break: break-all;
}
</style>

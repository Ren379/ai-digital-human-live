// ── Persona ──
export interface PersonaConfig {
  id: number
  name: string
  personality: string
  style: string
  knowledge_scope: string
  forbidden_topics: string[]
  updated_at: string | null
}

// ── Script ──
export interface Script {
  id: number
  title: string
  type: 'text' | 'audio' | 'video'
  content: string
  file_path: string | null
  tags: string[]
  enabled: boolean
  play_count: number
  last_used_at: string | null
  created_at: string | null
  updated_at: string | null
}

// ── Knowledge ──
export interface KnowledgeDoc {
  id: number
  title: string
  content_preview: string
  source_type: 'text' | 'file'
  file_path: string | null
  chunk_count: number
  created_at: string | null
}

// ── Danmaku ──
export interface DanmakuEvent {
  type: string
  platform: string
  sender: string
  content: string
  timestamp: number
}

// ── Queue ──
export interface QueueItem {
  id: string
  type: string
  source: string
  content_preview: string
  level: 'high' | 'low'
}

export interface QueueSnapshot {
  high: QueueItem[]
  low: QueueItem[]
}

// ── Livestream ──
export interface LivestreamStatus {
  running: boolean
  room_id: string
  session_id: string
  queue_high_count: number
  queue_low_count: number
  danmaku_count: number
  is_speaking: boolean
}

export interface LiveAnalyticsStats {
  running: boolean
  started_at: string | null
  duration_seconds: number
  danmaku_count: number
  ai_reply_count: number
  auto_script_count: number
  product_consultation_count: number
  intent_consultation_count: number
}

export interface LivetalkingSession {
  sessionid: string
  model: string
  speaking: boolean
  avatar_id: string
  transport: string
}

// ── WS Message ──
export interface WSMessage {
  type: string
  [key: string]: any
}

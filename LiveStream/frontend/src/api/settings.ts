import client from './client'

export interface AppSettingsData {
  livetalking_base_url: string
  llm_api_key: string
  llm_base_url: string
  llm_model: string
  embedding_api_key: string
  embedding_base_url: string
  embedding_model: string
}

export async function getSettings(): Promise<AppSettingsData> {
  const { data } = await client.get('/api/settings')
  return data.data
}

export async function updateSettings(payload: Partial<AppSettingsData>): Promise<AppSettingsData> {
  const { data } = await client.put('/api/settings', payload)
  return data.data
}

export async function reloadSettings(): Promise<void> {
  await client.post('/api/settings/reload')
}

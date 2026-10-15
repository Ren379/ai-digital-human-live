import client from './client'
import type { Script } from '@/types'

export async function getScripts(params?: { enabled_only?: boolean; type_filter?: string }): Promise<Script[]> {
  const { data } = await client.get('/api/scripts', { params })
  return data
}

export async function createScript(payload: { title: string; type: string; content: string; tags: string[] }): Promise<Script> {
  const { data } = await client.post('/api/scripts', payload)
  return data
}

export async function updateScript(id: number, payload: Partial<Script>): Promise<Script> {
  const { data } = await client.put(`/api/scripts/${id}`, payload)
  return data
}

export async function deleteScript(id: number): Promise<void> {
  await client.delete(`/api/scripts/${id}`)
}

export async function toggleScript(id: number): Promise<{ enabled: boolean }> {
  const { data } = await client.post(`/api/scripts/${id}/toggle`)
  return data
}

export async function uploadFile(scriptId: number, file: File): Promise<{ file_path: string }> {
  const form = new FormData()
  form.append('script_id', String(scriptId))
  form.append('file', file)
  const { data } = await client.post('/api/scripts/upload-file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

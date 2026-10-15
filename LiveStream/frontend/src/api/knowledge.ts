import client from './client'
import type { KnowledgeDoc } from '@/types'

export async function getDocuments(): Promise<KnowledgeDoc[]> {
  const { data } = await client.get('/api/knowledge/documents')
  return data
}

export async function createDocument(payload: { title: string; content: string; source_type: string }): Promise<KnowledgeDoc> {
  const { data } = await client.post('/api/knowledge/documents', payload)
  return data
}

export async function uploadDocument(title: string, file: File): Promise<{ id: number }> {
  const form = new FormData()
  form.append('title', title)
  form.append('file', file)
  const { data } = await client.post('/api/knowledge/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

export async function deleteDocument(id: number): Promise<void> {
  await client.delete(`/api/knowledge/documents/${id}`)
}

export async function rebuildIndex(): Promise<void> {
  await client.post('/api/knowledge/rebuild')
}

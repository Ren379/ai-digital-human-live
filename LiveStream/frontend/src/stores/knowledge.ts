import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDocuments } from '@/api/knowledge'
import type { KnowledgeDoc } from '@/types'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const documents = ref<KnowledgeDoc[]>([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      documents.value = await getDocuments()
    } finally {
      loading.value = false
    }
  }

  return { documents, loading, fetchAll }
})

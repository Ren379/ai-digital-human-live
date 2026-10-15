import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getScripts } from '@/api/scripts'
import type { Script } from '@/types'

export const useScriptsStore = defineStore('scripts', () => {
  const scripts = ref<Script[]>([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      scripts.value = await getScripts()
    } finally {
      loading.value = false
    }
  }

  return { scripts, loading, fetchAll }
})

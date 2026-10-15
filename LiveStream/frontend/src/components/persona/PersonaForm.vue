<template>
  <el-form :model="form" label-width="100px" style="max-width: 700px" v-loading="store.loading">
    <el-form-item label="主播名称">
      <el-input v-model="form.name" placeholder="如：小助手" />
    </el-form-item>
    <el-form-item label="性格特点">
      <el-input
        v-model="form.personality"
        type="textarea"
        :rows="2"
        placeholder="如：热情友好、耐心细致、幽默风趣"
      />
    </el-form-item>
    <el-form-item label="说话风格">
      <el-input
        v-model="form.style"
        type="textarea"
        :rows="2"
        placeholder="如：轻松活泼，喜欢用简短的句子"
      />
    </el-form-item>
    <el-form-item label="知识范围">
      <el-input
        v-model="form.knowledge_scope"
        type="textarea"
        :rows="2"
        placeholder="如：日常闲聊、生活百科、娱乐八卦"
      />
    </el-form-item>
    <el-form-item label="禁止话题">
      <el-select
        v-model="form.forbidden_topics"
        multiple
        filterable
        allow-create
        placeholder="输入后按回车添加"
        style="width: 100%"
      />
    </el-form-item>
    <el-form-item label=" ">
      <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
      <el-button @click="handleReset">重置</el-button>
    </el-form-item>

    <!-- Preview -->
    <el-divider />
    <div style="font-size: 13px; color: #909399">
      <div style="font-weight: 600; margin-bottom: 6px">System Prompt 预览</div>
      <pre style="background: #f5f7fa; padding: 12px; border-radius: 4px; white-space: pre-wrap; font-size: 12px">{{ previewText }}</pre>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { usePersonaStore } from '@/stores/persona'
import { updatePersona } from '@/api/persona'

const store = usePersonaStore()
const saving = ref(false)

const form = reactive({
  name: '',
  personality: '',
  style: '',
  knowledge_scope: '',
  forbidden_topics: [] as string[],
})

const previewText = computed(() => {
  const parts = [
    `你是${form.name || '小助手'}，一位正在直播的主播。`,
    `性格特点：${form.personality || '...'}`,
    `说话风格：${form.style || '...'}`,
    `知识范围：${form.knowledge_scope || '...'}`,
  ]
  if (form.forbidden_topics.length > 0) {
    parts.push(`禁止谈论：${form.forbidden_topics.join('、')}`)
  }
  return parts.join('\n')
})

onMounted(async () => {
  await store.fetch()
  const p = store.persona
  form.name = p.name
  form.personality = p.personality
  form.style = p.style
  form.knowledge_scope = p.knowledge_scope
  form.forbidden_topics = [...p.forbidden_topics]
})

async function handleSave() {
  saving.value = true
  try {
    await updatePersona({ ...form })
    ElMessage.success('人设已保存')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  store.fetch().then(() => {
    const p = store.persona
    form.name = p.name
    form.personality = p.personality
    form.style = p.style
    form.knowledge_scope = p.knowledge_scope
    form.forbidden_topics = [...p.forbidden_topics]
  })
}
</script>

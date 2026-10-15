<template>
  <div>
    <h1 style="margin: 0 0 20px 0; font-size: 22px">系统配置</h1>

    <el-card style="margin-bottom: 20px">
      <template #header><span>服务连接</span></template>
      <el-form :model="form" label-width="160px" style="max-width: 600px">
        <el-form-item label="LiveTalking URL">
          <el-input v-model="form.livetalking_base_url" placeholder="http://127.0.0.1:8010" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-bottom: 20px">
      <template #header><span>LLM 配置</span></template>
      <el-form :model="form" label-width="160px" style="max-width: 600px">
        <el-form-item label="API Key">
          <el-input v-model="form.llm_api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.llm_base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
        </el-form-item>
        <el-form-item label="Model">
          <el-input v-model="form.llm_model" placeholder="qwen-plus" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-bottom: 20px">
      <template #header><span>Embedding 配置</span></template>
      <el-form :model="form" label-width="160px" style="max-width: 600px">
        <el-form-item label="API Key">
          <el-input v-model="form.embedding_api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.embedding_base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
        </el-form-item>
        <el-form-item label="Model">
          <el-input v-model="form.embedding_model" placeholder="text-embedding-v4" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-row>
      <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
      <el-button @click="handleReload" :loading="reloading" type="warning">应用并重启服务</el-button>
      <el-button @click="handleReset">重置</el-button>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSettings, reloadSettings } from '@/api/settings'

const saving = ref(false)
const reloading = ref(false)

const form = reactive({
  livetalking_base_url: '',
  llm_api_key: '',
  llm_base_url: '',
  llm_model: '',
  embedding_api_key: '',
  embedding_base_url: '',
  embedding_model: '',
})

onMounted(async () => {
  try {
    const s = await getSettings()
    Object.assign(form, s)
  } catch { /* ignore */ }
})

async function handleSave() {
  saving.value = true
  try {
    await updateSettings(form)
    ElMessage.success('配置已保存')
  } finally {
    saving.value = false
  }
}

async function handleReload() {
  reloading.value = true
  try {
    await updateSettings(form)
    await reloadSettings()
    ElMessage.success('配置已应用，LLM 和 Embedding 已重载')
  } catch { /* error handled by interceptor */ }
  finally {
    reloading.value = false
  }
}

async function handleReset() {
  try {
    const s = await getSettings()
    Object.assign(form, s)
  } catch { /* ignore */ }
}
</script>

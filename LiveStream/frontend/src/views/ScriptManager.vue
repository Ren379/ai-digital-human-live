<template>
  <div>
    <h1 style="margin: 0 0 20px 0; font-size: 22px">话术管理</h1>
    <el-card style="margin-bottom: 20px">
      <template #header><span><el-icon><Plus /></el-icon> 添加话术</span></template>
      <ScriptForm @created="onCreated" />
    </el-card>
    <el-card>
      <template #header>
        <span><el-icon><Document /></el-icon> 话术列表</span>
        <el-button size="small" style="float: right" @click="store.fetchAll()" :loading="store.loading">
          刷新
        </el-button>
      </template>
      <el-table :data="store.scripts" stripe v-loading="store.loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题" min-width="150" />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.type === 'audio' ? 'warning' : row.type === 'video' ? 'danger' : ''" size="small">
              {{ typeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="内容预览" min-width="200">
          <template #default="{ row }">
            <span style="font-size: 13px; color: #666">{{ row.content?.slice(0, 80) || row.file_path || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="播放次数" width="80" prop="play_count" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch
              :model-value="row.enabled"
              @change="handleToggle(row)"
              size="small"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="handleDelete(row.id)" text>删除</el-button>
            <el-upload
              v-if="row.type === 'audio' || row.type === 'video' || !row.content"
              :show-file-list="false"
              :before-upload="(f: UploadFile) => handleUpload(row.id, f)"
              :accept="row.type === 'video' ? 'video/*' : 'audio/*'"
              style="display: inline-block; margin-left: 4px"
            >
              <el-button size="small" type="primary" text>
                {{ row.type === 'video' ? '上传视频' : '上传音频' }}
              </el-button>
            </el-upload>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { useScriptsStore } from '@/stores/scripts'
import { deleteScript, toggleScript, uploadFile } from '@/api/scripts'
import ScriptForm from '@/components/scripts/ScriptForm.vue'

const store = useScriptsStore()

onMounted(() => store.fetchAll())

const TYPE_LABELS: Record<string, string> = { text: '文字', audio: '音频', video: '视频' }
function typeLabel(t: string): string { return TYPE_LABELS[t] || t }

async function onCreated() {
  await store.fetchAll()
}

async function handleToggle(row: any) {
  try {
    const result = await toggleScript(row.id)
    row.enabled = result.enabled
  } catch {
    // error handled by interceptor
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
    await deleteScript(id)
    ElMessage.success('已删除')
    await store.fetchAll()
  } catch {
    // cancelled or error
  }
}

async function handleUpload(scriptId: number, file: UploadFile) {
  try {
    await uploadFile(scriptId, file as unknown as File)
    ElMessage.success('文件已上传')
    await store.fetchAll()
  } catch {
    // error handled
  }
  return false
}
</script>

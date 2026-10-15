<template>
  <div>
    <h1 style="margin: 0 0 20px 0; font-size: 22px">知识库管理</h1>

    <el-card style="margin-bottom: 20px">
      <template #header><span><el-icon><Upload /></el-icon> 添加知识</span></template>
      <el-row :gutter="16">
        <el-col :span="6">
          <el-input v-model="newDocTitle" placeholder="文档标题" />
        </el-col>
        <el-col :span="14">
          <el-input
            v-model="newDocContent"
            type="textarea"
            :rows="3"
            placeholder="粘贴文档内容..."
          />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="handleAddText" :disabled="!newDocTitle || !newDocContent">
            添加文本
          </el-button>
        </el-col>
      </el-row>
      <el-divider />
      <el-upload
        :before-upload="handleFileUpload"
        :show-file-list="false"
        accept=".txt,.md,.pdf"
      >
        <el-button type="primary" plain>
          <el-icon><Upload /></el-icon> 上传文档文件
        </el-button>
      </el-upload>
    </el-card>

    <el-card>
      <template #header>
        <span><el-icon><Collection /></el-icon> 文档列表</span>
        <el-button size="small" style="float: right; margin-left: 8px" @click="handleRebuild" type="warning" plain>
          重建索引
        </el-button>
        <el-button size="small" style="float: right" @click="store.fetchAll()" :loading="store.loading">
          刷新
        </el-button>
      </template>
      <el-table :data="store.documents" stripe v-loading="store.loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题" min-width="150" />
        <el-table-column label="类型" width="80">
          <template #default="{ row }"><el-tag size="small">{{ row.source_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="内容" min-width="200">
          <template #default="{ row }">
            <span style="font-size: 13px; color: #666">{{ row.content_preview }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数" width="80" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="handleDelete(row.id)" text>删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { useKnowledgeStore } from '@/stores/knowledge'
import { createDocument, uploadDocument, deleteDocument, rebuildIndex } from '@/api/knowledge'

const store = useKnowledgeStore()
const newDocTitle = ref('')
const newDocContent = ref('')

onMounted(() => store.fetchAll())

async function handleAddText() {
  try {
    await createDocument({
      title: newDocTitle.value,
      content: newDocContent.value,
      source_type: 'text',
    })
    ElMessage.success('已添加')
    newDocTitle.value = ''
    newDocContent.value = ''
    await store.fetchAll()
  } catch {
    // error handled
  }
}

async function handleFileUpload(file: UploadFile) {
  try {
    await uploadDocument(file.name || 'unnamed', file as unknown as File)
    ElMessage.success('已上传')
    await store.fetchAll()
  } catch {
    // error handled
  }
  return false
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
    await deleteDocument(id)
    ElMessage.success('已删除')
    await store.fetchAll()
  } catch {
    // cancelled or error
  }
}

async function handleRebuild() {
  try {
    await rebuildIndex()
    ElMessage.success('索引已重建')
  } catch {
    // error handled
  }
}
</script>

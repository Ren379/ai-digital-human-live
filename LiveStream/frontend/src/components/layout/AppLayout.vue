<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="background: #1d1e1f; color: #fff">
      <SideNav />
    </el-aside>
    <el-container>
      <el-main style="background: #f5f7fa; padding: 20px">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { wsClient } from '@/api/ws'
import SideNav from './SideNav.vue'

// WS 连接在 App 级别管理，路由切换不会断
onMounted(() => {
  wsClient.connect('/ws')
})

onUnmounted(() => {
  wsClient.disconnect()
})
</script>

<template>
  <div style="padding: 20px 16px">
    <h2 style="color: #409eff; font-size: 18px; margin: 0 0 24px 0">
      <el-icon><Monitor /></el-icon> LiveStream
    </h2>
    <el-menu
      :default-active="route.path"
      router
      background-color="#1d1e1f"
      text-color="#aaa"
      active-text-color="#409eff"
      style="border-right: none"
    >
      <el-menu-item index="/">
        <el-icon><Odometer /></el-icon>
        <span>直播控制</span>
      </el-menu-item>
      <el-menu-item index="/persona">
        <el-icon><UserFilled /></el-icon>
        <span>人设配置</span>
      </el-menu-item>
      <el-menu-item index="/scripts">
        <el-icon><Document /></el-icon>
        <span>话术管理</span>
      </el-menu-item>
      <el-menu-item index="/knowledge">
        <el-icon><Collection /></el-icon>
        <span>知识库</span>
      </el-menu-item>
      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
        <span>系统配置</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

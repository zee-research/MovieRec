<!--
  管理员布局：左侧侧边栏 + 右侧内容区域
-->
<template>
  <el-container class="admin-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="admin-aside">
      <div class="logo-area">
        <el-icon :size="28" color="#409EFF"><Film /></el-icon>
        <span v-show="!isCollapse" class="logo-text">后台管理</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#409EFF"
        router
        unique-opened
      >
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>数据概览</template>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/movies">
          <el-icon><Film /></el-icon>
          <template #title>电影管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/ratings">
          <el-icon><Star /></el-icon>
          <template #title>评分管理</template>
        </el-menu-item>
        <el-menu-item index="/admin/graph">
          <el-icon><Share /></el-icon>
          <template #title>知识图谱</template>
        </el-menu-item>
        <el-menu-item index="/admin/evaluate">
          <el-icon><TrendCharts /></el-icon>
          <template #title>模型评估</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧 -->
    <el-container>
      <!-- 顶栏 -->
      <el-header class="admin-header">
        <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>管理后台</el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="header-right">
          <span class="admin-name">{{ userStore.username }}</span>
          <el-dropdown @command="handleCommand">
            <el-icon :size="18" style="cursor:pointer;color:#333"><Setting /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="home">回到前台</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容 -->
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)

// 当前激活菜单
const activeMenu = computed(() => route.path)

// 当前页标题
const currentTitle = computed(() => route.meta.title || '')

const handleCommand = (cmd) => {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (cmd === 'home') {
    router.push('/home')
  }
}
</script>

<style scoped>
.admin-layout {
  height: 100vh;
}
.admin-aside {
  background: #001529;
  transition: width 0.3s;
  overflow: hidden;
}
.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-bottom: 1px solid #ffffff1a;
}
.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}
.admin-header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #eee;
  padding: 0 20px;
  height: 60px;
  gap: 16px;
}
.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #333;
}
.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}
.admin-name {
  font-size: 14px;
  color: #666;
}
.admin-main {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}

/* Element Plus Menu 深色覆盖 */
:deep(.el-menu) {
  border-right: none;
}
</style>

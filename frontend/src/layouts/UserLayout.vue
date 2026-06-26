<!--
  用户端布局：顶部导航栏 + 内容区域
-->
<template>
  <el-container class="user-layout">
    <!-- 顶部导航 -->
    <el-header class="user-header">
      <div class="header-left">
        <el-icon :size="28" color="#409EFF"><Film /></el-icon>
        <span class="brand" @click="router.push('/home')">电影推荐系统</span>
        <el-menu
          :default-active="activeMenu"
          mode="horizontal"
          :ellipsis="false"
          router
          class="nav-menu"
        >
          <el-menu-item index="/home">首页</el-menu-item>
          <el-menu-item index="/movies">电影列表</el-menu-item>
          <el-menu-item index="/recommend" v-if="userStore.isLoggedIn">个性化推荐</el-menu-item>
          <el-menu-item index="/knowledge-graph">知识图谱</el-menu-item>
        </el-menu>
      </div>

      <div class="header-right">
        <template v-if="userStore.isLoggedIn">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              {{ userStore.username }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="my-ratings">我的评分</el-dropdown-item>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item v-if="userStore.isAdmin" command="admin" divided>管理后台</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button type="primary" @click="router.push('/login')">登录</el-button>
          <el-button @click="router.push('/register')">注册</el-button>
        </template>
      </div>
    </el-header>

    <!-- 内容 -->
    <el-main class="user-main">
      <router-view />
    </el-main>

    <!-- 底部 -->
    <el-footer class="user-footer">
      电影推荐系统 — 基于知识图谱的个性化推荐
    </el-footer>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 当前激活菜单
const activeMenu = computed(() => {
  // movie/:id 也高亮 movies 菜单
  if (route.path.startsWith('/movie/')) return '/movies'
  return route.path
})

const handleCommand = (cmd) => {
  switch (cmd) {
    case 'my-ratings': router.push('/my-ratings'); break
    case 'profile': router.push('/profile'); break
    case 'admin': router.push('/admin'); break
    case 'logout':
      userStore.logout()
      router.push('/login')
      break
  }
}
</script>

<style scoped>
.user-layout {
  min-height: 100vh;
  background: #f5f7fa;
}
.user-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  padding: 0 24px;
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  cursor: pointer;
  margin-right: 12px;
  user-select: none;
}
.nav-menu {
  border-bottom: none !important;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
}
.user-main {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
  min-height: calc(100vh - 120px);
}
.user-footer {
  text-align: center;
  color: #999;
  font-size: 13px;
  height: 48px;
  line-height: 48px;
  background: #fff;
  border-top: 1px solid #eee;
}
</style>

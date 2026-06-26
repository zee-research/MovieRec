<!--
  用户管理：表格 + 搜索 + 分页 + 重置密码 + 删除
-->
<template>
  <div class="user-manage">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用户名" prefix-icon="Search" clearable
        style="width:240px" @keyup.enter="search" @clear="search" />
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <el-table v-loading="loading" :data="users" stripe border style="width:100%">
      <el-table-column prop="userId" label="用户ID" width="100" />
      <el-table-column prop="username" label="用户名" min-width="150" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : ''">{{ row.role === 'admin' ? '管理员' : '用户' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ratingCount" label="评分数" width="100" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-popconfirm title="确认重置该用户密码为 123456 ？" @confirm="handleReset(row.userId)">
            <template #reference>
              <el-button size="small" type="warning" text>重置密码</el-button>
            </template>
          </el-popconfirm>
          <el-popconfirm title="确认删除该用户？" @confirm="handleDelete(row.userId)">
            <template #reference>
              <el-button size="small" type="danger" text :disabled="row.role === 'admin'">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="loadUsers"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUsers, deleteUser, resetUserPassword } from '@/api/admin'

const users = ref([])
const keyword = ref('')
const page = ref(1)
const pageSize = 15
const total = ref(0)
const loading = ref(false)

const loadUsers = async () => {
  loading.value = true
  try {
    const params = { page: page.value, pageSize }
    if (keyword.value) params.keyword = keyword.value
    const res = await getUsers(params)
    if (res.code === 200) {
      users.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } finally {
    loading.value = false
  }
}

const search = () => { page.value = 1; loadUsers() }

const handleReset = async (userId) => {
  try {
    const res = await resetUserPassword(userId)
    if (res.code === 200) ElMessage.success('密码已重置为 123456')
    else ElMessage.error(res.message || '重置失败')
  } catch (e) { ElMessage.error('重置失败') }
}

const handleDelete = async (userId) => {
  try {
    const res = await deleteUser(userId)
    if (res.code === 200) {
      ElMessage.success('已删除')
      loadUsers()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) { ElMessage.error('删除失败') }
}

onMounted(() => loadUsers())
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: center; }
</style>

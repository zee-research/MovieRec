<!--
  评分管理：表格 + 分页 + 删除
-->
<template>
  <div class="rating-manage">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用户名或电影名" prefix-icon="Search" clearable
        style="width:260px" @keyup.enter="search" @clear="search" />
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <el-table v-loading="loading" :data="ratings" stripe border style="width:100%">
      <el-table-column prop="userId" label="用户ID" width="90" />
      <el-table-column prop="username" label="用户名" width="130" />
      <el-table-column prop="movieId" label="电影ID" width="90" />
      <el-table-column prop="title" label="电影名称" min-width="200" show-overflow-tooltip />
      <el-table-column label="评分" width="180">
        <template #default="{ row }">
          <el-rate :model-value="row.rating" disabled :max="5" size="small" allow-half />
        </template>
      </el-table-column>
      <el-table-column prop="date_str" label="时间" width="160" />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-popconfirm title="确认删除该评分？" @confirm="handleDelete(row.userId, row.movieId)">
            <template #reference>
              <el-button type="danger" size="small" text>删除</el-button>
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
        @current-change="loadRatings"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getRatings, deleteRating } from '@/api/admin'

const ratings = ref([])
const keyword = ref('')
const page = ref(1)
const pageSize = 15
const total = ref(0)
const loading = ref(false)

const loadRatings = async () => {
  loading.value = true
  try {
    const params = { page: page.value, pageSize }
    if (keyword.value) params.keyword = keyword.value
    const res = await getRatings(params)
    if (res.code === 200) {
      ratings.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } finally {
    loading.value = false
  }
}

const search = () => { page.value = 1; loadRatings() }

const handleDelete = async (userId, movieId) => {
  try {
    const res = await deleteRating(userId, movieId)
    if (res.code === 200) {
      ElMessage.success('已删除')
      loadRatings()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) { ElMessage.error('删除失败') }
}

onMounted(() => loadRatings())
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: center; }
</style>

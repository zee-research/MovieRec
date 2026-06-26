<!--
  我的评分页面
-->
<template>
  <div class="my-ratings">
    <h2 class="page-title">⭐ 我的评分</h2>

    <el-table v-loading="loading" :data="ratings" stripe style="width:100%">
      <el-table-column label="电影" min-width="200">
        <template #default="{ row }">
          <el-link type="primary" @click="router.push(`/movie/${row.movieId}`)">{{ row.title }}</el-link>
        </template>
      </el-table-column>
      <el-table-column label="评分" width="200">
        <template #default="{ row }">
          <el-rate :model-value="row.rating" disabled :max="5" allow-half />
        </template>
      </el-table-column>
      <el-table-column label="评分时间" prop="date_str" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-popconfirm title="确认删除该评分？" @confirm="handleDelete(row.movieId)">
            <template #reference>
              <el-button type="danger" size="small" text>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && ratings.length === 0" description="还没有评分记录，去浏览电影评分吧">
      <el-button type="primary" @click="router.push('/movies')">浏览电影</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMyRatings, deleteRating } from '@/api/rating'

const router = useRouter()
const ratings = ref([])
const loading = ref(false)

const loadRatings = async () => {
  loading.value = true
  try {
    const res = await getMyRatings()
    if (res.code === 200) ratings.value = res.data.list || res.data || []
  } finally {
    loading.value = false
  }
}

const handleDelete = async (movieId) => {
  try {
    const res = await deleteRating(movieId)
    if (res.code === 200) {
      ElMessage.success('已删除')
      loadRatings()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => loadRatings())
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 16px; color: #303133; }
</style>

<!--
  电影管理：表格 + 搜索筛选 + 分页
-->
<template>
  <div class="movie-manage">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索电影名称" prefix-icon="Search" clearable
        style="width:240px" @keyup.enter="search" @clear="search" />
      <el-select v-model="selectedGenre" placeholder="全部类型" clearable @change="search" style="width:160px">
        <el-option v-for="g in genres" :key="g" :label="g" :value="g" />
      </el-select>
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <el-table v-loading="loading" :data="movies" stripe border style="width:100%">
      <el-table-column prop="movieId" label="ID" width="80" sortable />
      <el-table-column prop="title" label="电影名称" min-width="250" show-overflow-tooltip />
      <el-table-column label="类型" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="g in (row.genreNames || [])" :key="g" size="small" style="margin:2px">{{ g }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="avgRating" label="平均评分" width="100" sortable>
        <template #default="{ row }">{{ (row.avgRating || 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="ratingCount" label="评分数" width="90" sortable />
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="loadMovies"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getMovieList, getGenres } from '@/api/movie'

const movies = ref([])
const genres = ref([])
const keyword = ref('')
const selectedGenre = ref('')
const page = ref(1)
const pageSize = 15
const total = ref(0)
const loading = ref(false)

const loadMovies = async () => {
  loading.value = true
  try {
    const params = { page: page.value, pageSize }
    if (keyword.value) params.keyword = keyword.value
    if (selectedGenre.value) params.genre = selectedGenre.value
    const res = await getMovieList(params)
    if (res.code === 200) {
      movies.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } finally {
    loading.value = false
  }
}

const search = () => { page.value = 1; loadMovies() }

const loadGenres = async () => {
  try {
    const res = await getGenres()
    if (res.code === 200) {
      const data = res.data || []
      genres.value = data.map(g => typeof g === 'string' ? g : g.name)
    }
  } catch (e) { /* ignore */ }
}

onMounted(() => { loadGenres(); loadMovies() })
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: center; }
</style>

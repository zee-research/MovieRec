<!--
  电影列表：搜索、按类型筛选、分页，卡片式展示
-->
<template>
  <div class="movie-list">
    <h2 class="page-title">电影列表</h2>

    <!-- 搜索 & 筛选 -->
    <div class="filter-bar">
      <el-input v-model="keyword" placeholder="搜索电影名称…" prefix-icon="Search" clearable
        style="width:280px" @keyup.enter="search" @clear="search" />
      <el-select v-model="selectedGenre" placeholder="全部类型" clearable @change="search" style="width:160px">
        <el-option v-for="g in genres" :key="g" :label="g" :value="g" />
      </el-select>
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <!-- 电影卡片 -->
    <div v-loading="loading" class="movie-grid">
      <div v-for="m in movies" :key="m.movieId" class="movie-card" @click="goDetail(m.movieId)">
        <div class="card-poster">
          <MoviePoster :title="m.title" :genres="m.genres" :year="m.year" />
        </div>
        <div class="card-info">
          <div class="card-title" :title="m.title">{{ m.title }}</div>
          <div class="card-meta">
            <el-rate :model-value="m.avgRating || 0" disabled :max="5" size="small" />
            <span class="score-text">{{ (m.avgRating || 0).toFixed(1) }}</span>
          </div>
          <div class="card-genres">
            <el-tag v-for="g in getGenreList(m).slice(0, 3)" :key="g" size="small" type="info">{{ g }}</el-tag>
          </div>
        </div>
      </div>
      <el-empty v-if="!loading && movies.length === 0" description="暂无匹配电影" />
    </div>

    <!-- 分页 -->
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
import { useRouter } from 'vue-router'
import { getMovieList, getGenres } from '@/api/movie'
import { getGenreList } from '@/utils/genre'
import MoviePoster from '@/components/MoviePoster.vue'

const router = useRouter()

const movies = ref([])
const genres = ref([])
const keyword = ref('')
const selectedGenre = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)

const goDetail = (id) => router.push(`/movie/${id}`)

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

const search = () => {
  page.value = 1
  loadMovies()
}

const loadGenres = async () => {
  try {
    const res = await getGenres()
    if (res.code === 200) {
      const data = res.data || []
      genres.value = data.map(g => typeof g === 'string' ? g : g.name)
    }
  } catch (e) { /* ignore */ }
}

onMounted(() => {
  loadGenres()
  loadMovies()
})
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 16px; color: #303133; }
.filter-bar {
  display: flex; gap: 12px; align-items: center; margin-bottom: 20px;
  flex-wrap: wrap;
}
.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px; min-height: 200px;
}
.movie-card {
  background: #fff; border-radius: 8px; overflow: hidden;
  cursor: pointer; transition: box-shadow 0.2s, transform 0.2s;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.movie-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.12); transform: translateY(-2px);
}
.card-poster {
  height: 140px;
  display: flex; align-items: center; justify-content: center;
}
.card-info { padding: 12px; }
.card-title {
  font-size: 15px; font-weight: 600; color: #303133;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 6px;
}
.card-meta { display: flex; align-items: center; gap: 4px; margin-bottom: 6px; }
.score-text { font-size: 13px; color: #e6a23c; font-weight: 600; }
.card-genres { display: flex; gap: 4px; flex-wrap: wrap; overflow: hidden; }
.card-genres .el-tag { flex-shrink: 0; }
.pagination-wrap { margin-top: 24px; display: flex; justify-content: center; }
</style>

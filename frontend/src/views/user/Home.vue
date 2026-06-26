<!--
  首页：热门电影 + 个性化推荐（登录后显示）
-->
<template>
  <div class="home">
    <!-- 欢迎横幅 -->
    <div class="banner">
      <h1>🎬 欢迎来到 电影推荐系统</h1>
      <p>基于知识图谱的个性化电影推荐系统</p>
    </div>

    <!-- 个性化推荐（仅登录用户） -->
    <template v-if="userStore.isLoggedIn">
      <div class="section">
        <div class="section-header">
          <h2>🎯 为你推荐</h2>
          <el-button text type="primary" @click="router.push('/recommend')">查看更多 →</el-button>
        </div>
        <div v-loading="recLoading" class="movie-grid">
          <div v-for="m in recMovies" :key="m.movieId" class="movie-card" @click="goDetail(m.movieId)">
            <div class="card-poster">
              <MoviePoster :title="m.title" :genres="m.genres" :year="m.year" />
            </div>
            <div class="card-info">
              <div class="card-title" :title="m.title">{{ m.title }}</div>
              <div class="card-meta">
                <el-rate v-model="m.score" disabled :max="5" size="small" />
                <span class="score-text">{{ (m.score || 0).toFixed(1) }}</span>
              </div>
              <div class="card-genres">
                <el-tag v-for="g in getGenreList(m).slice(0, 3)" :key="g" size="small" type="info">{{ g }}</el-tag>
              </div>
            </div>
          </div>
          <el-empty v-if="!recLoading && recMovies.length === 0" description="暂无推荐，去评分更多电影吧" />
        </div>
      </div>
    </template>

    <!-- 热门电影 -->
    <div class="section">
      <div class="section-header">
        <h2>🔥 热门电影</h2>
        <el-button text type="primary" @click="router.push('/movies')">浏览全部 →</el-button>
      </div>
      <div v-loading="hotLoading" class="movie-grid">
        <div v-for="m in hotMovies" :key="m.movieId" class="movie-card" @click="goDetail(m.movieId)">
          <div class="card-poster">
            <MoviePoster :title="m.title" :genres="m.genres" :year="m.year" />
          </div>
          <div class="card-info">
            <div class="card-title" :title="m.title">{{ m.title }}</div>
            <div class="card-meta">
              <el-rate :model-value="m.avgRating || 0" disabled :max="5" size="small" />
              <span class="score-text">{{ (m.avgRating || 0).toFixed(1) }}</span>
            </div>
            <div class="card-extra">
              <span>{{ m.ratingCount || 0 }} 人评分</span>
            </div>
            <div class="card-genres">
              <el-tag v-for="g in getGenreList(m).slice(0, 3)" :key="g" size="small" type="info">{{ g }}</el-tag>
            </div>
          </div>
        </div>
        <el-empty v-if="!hotLoading && hotMovies.length === 0" description="暂无热门电影" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getHotMovies } from '@/api/movie'
import { getHybridRecommend } from '@/api/recommend'
import { getGenreList } from '@/utils/genre'
import MoviePoster from '@/components/MoviePoster.vue'

const router = useRouter()
const userStore = useUserStore()

const hotMovies = ref([])
const recMovies = ref([])
const hotLoading = ref(false)
const recLoading = ref(false)

const goDetail = (id) => router.push(`/movie/${id}`)

// 加载热门电影
const loadHot = async () => {
  hotLoading.value = true
  try {
    const res = await getHotMovies({ limit: 12 })
    if (res.code === 200) hotMovies.value = res.data || []
  } finally {
    hotLoading.value = false
  }
}

// 加载个性化推荐
const loadRec = async () => {
  if (!userStore.isLoggedIn) return
  recLoading.value = true
  try {
    const res = await getHybridRecommend({ limit: 8 })
    if (res.code === 200) recMovies.value = res.data || []
  } finally {
    recLoading.value = false
  }
}

onMounted(() => {
  loadHot()
  loadRec()
})
</script>

<style scoped>
.banner {
  text-align: center;
  padding: 40px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: #fff;
  margin-bottom: 32px;
}
.banner h1 { font-size: 28px; margin-bottom: 8px; }
.banner p { font-size: 16px; opacity: 0.9; }

.section { margin-bottom: 32px; }
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.section-header h2 { font-size: 20px; color: #303133; }

.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  min-height: 100px;
}
.movie-card {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.movie-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}
.card-poster {
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-info { padding: 12px; }
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}
.card-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
}
.score-text { font-size: 13px; color: #e6a23c; font-weight: 600; }
.card-extra { font-size: 12px; color: #909399; margin-bottom: 6px; }
.card-genres { display: flex; gap: 4px; flex-wrap: wrap; overflow: hidden; }
.card-genres .el-tag { flex-shrink: 0; }
</style>

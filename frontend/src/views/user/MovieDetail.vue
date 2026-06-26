<!--
  电影详情：信息展示 + 知识图谱 + 评分 + 相似推荐
-->
<template>
  <div v-loading="loading" class="movie-detail">
    <template v-if="movie">
      <!-- 基本信息 -->
      <el-card class="info-card">
        <div class="info-layout">
          <div class="poster-area">
            <el-icon :size="80" color="#ddd"><Film /></el-icon>
          </div>
          <div class="meta-area">
            <h1 class="movie-title">{{ movie.title }}</h1>
            <div class="genres-row">
              <el-tag v-for="g in getGenreList(movie)" :key="g" type="primary">{{ g }}</el-tag>
            </div>
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-label">平均评分</span>
                <div class="stat-value">
                  <el-rate :model-value="movie.avgRating || 0" disabled :max="5" />
                  <span class="big-score">{{ (movie.avgRating || 0).toFixed(1) }}</span>
                </div>
              </div>
              <div class="stat-item">
                <span class="stat-label">评分人数</span>
                <span class="stat-value">{{ movie.ratingCount || 0 }}</span>
              </div>
            </div>

            <!-- 用户评分 -->
            <div v-if="userStore.isLoggedIn" class="user-rating">
              <span class="stat-label">我的评分：</span>
              <el-rate v-model="userRating" :max="5" allow-half @change="submitRating" />
              <span v-if="userRating" class="my-score">{{ userRating }}</span>
            </div>
            <el-button v-else type="primary" plain @click="router.push('/login')">登录后评分</el-button>
          </div>
        </div>
      </el-card>

      <!-- 知识图谱可视化 -->
      <el-card class="graph-card">
        <template #header><span>📊 知识图谱</span></template>
        <div ref="graphRef" class="graph-container"></div>
      </el-card>

      <!-- 相似电影推荐 -->
      <div class="similar-section">
        <h3>🎬 相似电影</h3>
        <div v-loading="simLoading" class="similar-grid">
          <div v-for="m in similarMovies" :key="m.movieId" class="similar-card" @click="goDetail(m.movieId)">
            <div class="sim-title" :title="m.title">{{ m.title }}</div>
            <div class="sim-meta">
              <el-rate :model-value="m.avgRating || 0" disabled :max="5" size="small" />
            </div>
          </div>
          <el-empty v-if="!simLoading && similarMovies.length === 0" description="暂无相似电影" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { getMovieDetail, getSimilarMovies } from '@/api/movie'
import { addRating, getRatingStatus } from '@/api/rating'
import { getMovieGraph } from '@/api/graph'
import { getGenreList } from '@/utils/genre'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const movie = ref(null)
const loading = ref(false)
const userRating = ref(0)
const similarMovies = ref([])
const simLoading = ref(false)
const graphRef = ref(null)
let chartInstance = null

const movieId = () => route.params.id

const goDetail = (id) => {
  router.push(`/movie/${id}`)
}

// 加载电影详情
const loadDetail = async () => {
  loading.value = true
  try {
    const res = await getMovieDetail(movieId())
    if (res.code === 200) {
      movie.value = res.data
    }
  } finally {
    loading.value = false
  }
  // 加载当前用户对该电影的评分
  if (userStore.isLoggedIn) {
    try {
      const rRes = await getRatingStatus(movieId())
      if (rRes.code === 200 && rRes.data) {
        userRating.value = rRes.data.rating || 0
      } else {
        userRating.value = 0
      }
    } catch { userRating.value = 0 }
  }
}

// 提交评分
const submitRating = async (val) => {
  if (!val) return
  try {
    const res = await addRating({ movieId: Number(movieId()), rating: val })
    if (res.code === 200) {
      ElMessage.success('评分成功')
      loadDetail() // 刷新评分
    } else {
      ElMessage.error(res.message || '评分失败')
    }
  } catch (e) {
    ElMessage.error('评分失败')
  }
}

// 加载相似电影
const loadSimilar = async () => {
  simLoading.value = true
  try {
    const res = await getSimilarMovies(movieId(), 6)
    if (res.code === 200) similarMovies.value = res.data || []
  } finally {
    simLoading.value = false
  }
}

// 知识图谱可视化
const loadGraph = async () => {
  try {
    const res = await getMovieGraph(movieId())
    if (res.code === 200) {
      await nextTick()
      renderGraph(res.data)
    }
  } catch (e) { /* ignore */ }
}

const renderGraph = (data) => {
  if (!graphRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(graphRef.value)

  const nodes = (data.nodes || []).map(n => {
    const lower = (n.type || '').toLowerCase()
    const tp = lower === 'movie' ? 'Movie' : (lower === 'genre' ? 'Genre' : 'User')
    return {
      id: String(n.id),
      name: n.label || n.name || String(n.id),
      symbolSize: tp === 'Movie' ? 40 : 28,
      category: tp === 'Movie' ? 0 : (tp === 'Genre' ? 1 : 2),
      itemStyle: {
        color: tp === 'Movie' ? '#409EFF' : (tp === 'Genre' ? '#67C23A' : '#E6A23C')
      }
    }
  })
  const links = (data.links || []).map(l => ({
    source: String(l.source),
    target: String(l.target),
    value: l.type || ''
  }))

  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { data: ['电影', '类型', '用户'], top: 10 },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      label: { show: true, fontSize: 11 },
      categories: [{ name: '电影' }, { name: '类型' }, { name: '用户' }],
      data: nodes,
      links,
      force: { repulsion: 200, edgeLength: 120 },
      lineStyle: { color: '#aaa', width: 1 },
    }]
  })
}

// 路由参数变化时重新加载
watch(() => route.params.id, (newId) => {
  if (newId) {
    loadDetail()
    loadSimilar()
    loadGraph()
  }
})

onMounted(() => {
  loadDetail()
  loadSimilar()
  loadGraph()
})
</script>

<style scoped>
.movie-detail { max-width: 960px; margin: 0 auto; }
.info-card { margin-bottom: 20px; }
.info-layout { display: flex; gap: 24px; }
.poster-area {
  width: 200px; height: 260px; background: #f5f7fa; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.meta-area { flex: 1; }
.movie-title { font-size: 24px; margin-bottom: 12px; color: #303133; }
.genres-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.stats-row { display: flex; gap: 32px; margin-bottom: 16px; }
.stat-item { display: flex; flex-direction: column; }
.stat-label { font-size: 13px; color: #909399; margin-bottom: 4px; }
.stat-value { display: flex; align-items: center; gap: 4px; font-size: 16px; color: #303133; }
.big-score { font-size: 22px; font-weight: 700; color: #e6a23c; }
.user-rating { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
.my-score { font-size: 16px; font-weight: 600; color: #e6a23c; }

.graph-card { margin-bottom: 20px; }
.graph-container { width: 100%; height: 400px; }

.similar-section { margin-bottom: 20px; }
.similar-section h3 { margin-bottom: 12px; color: #303133; }
.similar-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px;
}
.similar-card {
  background: #fff; padding: 12px; border-radius: 8px; cursor: pointer;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06); transition: box-shadow 0.2s;
}
.similar-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.sim-title {
  font-size: 14px; font-weight: 600; color: #303133;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px;
}
</style>

<!--
  个性化推荐页面：协同过滤 / SVD / 知识图谱 / 混合推荐
-->
<template>
  <div class="recommend-page">
    <h2 class="page-title">🎯 个性化推荐</h2>

    <!-- 算法选项卡 -->
    <el-tabs v-model="activeTab" @tab-change="loadRecommend">
      <el-tab-pane label="混合推荐" name="hybrid" />
      <el-tab-pane label="协同过滤" name="cf" />
      <el-tab-pane label="SVD 矩阵分解" name="svd" />
      <el-tab-pane label="知识图谱推荐" name="kg" />
    </el-tabs>

    <div class="algo-desc">
      <el-alert :title="algoDesc[activeTab]" type="info" show-icon :closable="false" />
    </div>

    <!-- 推荐结果 -->
    <div v-loading="loading" class="movie-grid">
      <div v-for="m in movies" :key="m.movieId" class="movie-card" @click="goDetail(m.movieId)">
        <div class="card-poster">
          <MoviePoster :title="m.title" :genres="m.genres" :year="m.year" />
        </div>
        <div class="card-info">
          <div class="card-title" :title="m.title">{{ m.title }}</div>
          <div class="card-meta">
            <el-rate :model-value="m.score || m.avgRating || 0" disabled :max="5" size="small" />
            <span class="score-text">{{ (m.score || m.avgRating || 0).toFixed(1) }}</span>
          </div>
          <div class="card-genres">
            <el-tag v-for="g in getGenreList(m).slice(0, 3)" :key="g" size="small" type="info">{{ g }}</el-tag>
          </div>
        </div>
      </div>
      <el-empty v-if="!loading && movies.length === 0" description="暂无推荐结果，请先评分一些电影" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCollaborativeRecommend, getSvdRecommend, getKnowledgeRecommend, getHybridRecommend } from '@/api/recommend'
import { getGenreList } from '@/utils/genre'
import MoviePoster from '@/components/MoviePoster.vue'

const router = useRouter()

const activeTab = ref('hybrid')
const movies = ref([])
const loading = ref(false)

const algoDesc = {
  hybrid: '综合协同过滤、SVD、知识图谱三种算法的加权融合推荐',
  cf: '基于用户-物品协同过滤，寻找相似用户喜好进行推荐',
  svd: '基于 SVD 矩阵分解，通过隐向量预测用户评分',
  kg: '基于 Neo4j 知识图谱，通过电影的类型、关系路径进行推荐',
}

const apiMap = {
  hybrid: getHybridRecommend,
  cf: getCollaborativeRecommend,
  svd: getSvdRecommend,
  kg: getKnowledgeRecommend,
}

const goDetail = (id) => router.push(`/movie/${id}`)

const loadRecommend = async () => {
  loading.value = true
  movies.value = []
  try {
    const fn = apiMap[activeTab.value]
    const res = await fn(20)
    if (res.code === 200) movies.value = res.data || []
  } finally {
    loading.value = false
  }
}

onMounted(() => loadRecommend())
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 16px; color: #303133; }
.algo-desc { margin-bottom: 20px; }
.movie-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
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
</style>

<!--
  知识图谱浏览器：全局图谱 + 搜索指定电影图谱
-->
<template>
  <div class="kg-page">
    <h2 class="page-title">📊 知识图谱</h2>

    <div class="toolbar">
      <el-autocomplete
        v-model="searchText"
        :fetch-suggestions="queryMovies"
        placeholder="输入电影名称搜索"
        style="width:300px"
        value-key="label"
        @select="handleSelect"
        @keyup.enter="handleEnter"
        clearable
      />
      <el-button type="primary" @click="handleEnter" :disabled="!selectedMovieId">查看电影图谱</el-button>
      <el-button @click="loadGlobal">全局图谱</el-button>
      <el-divider direction="vertical" />
      <span style="color:#606266;font-size:13px;white-space:nowrap">电影数量：</span>
      <el-input-number v-model="nodeLimit" :min="5" :max="200" :step="5" size="small" style="width:130px" />
      <el-button size="small" @click="onLimitChange">刷新</el-button>
      <span v-if="nodeCount" style="color:#909399;font-size:12px;white-space:nowrap">当前 {{ nodeCount }} 个节点</span>
    </div>

    <el-card>
      <div ref="graphRef" v-loading="loading" class="graph-container"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { getMovieGraph, getGlobalGraph } from '@/api/graph'
import { getMovieList } from '@/api/movie'
import * as echarts from 'echarts'

const graphRef = ref(null)
const loading = ref(false)
const searchText = ref('')
const selectedMovieId = ref(null)
const nodeLimit = ref(50)
const nodeCount = ref(0)
let chartInstance = null
let currentMode = 'global'  // 'global' | 'movie'

const colorMap = {
  Movie: '#409EFF',
  Genre: '#67C23A',
  User: '#E6A23C',
}

const typeNormalize = (t) => {
  if (!t) return ''
  const lower = t.toLowerCase()
  if (lower === 'movie') return 'Movie'
  if (lower === 'genre') return 'Genre'
  if (lower === 'user') return 'User'
  return t
}

const renderGraph = (data) => {
  if (!graphRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(graphRef.value)

  const nodes = (data.nodes || []).map(n => {
    const tp = typeNormalize(n.type)
    return {
      id: String(n.id),
      name: n.label || n.name || String(n.id),
      symbolSize: tp === 'Movie' ? 36 : 24,
      category: tp === 'Movie' ? 0 : (tp === 'Genre' ? 1 : 2),
      itemStyle: { color: colorMap[tp] || '#909399' },
    }
  })
  nodeCount.value = nodes.length
  const links = (data.links || []).map(l => ({
    source: String(l.source),
    target: String(l.target),
    value: l.type || '',
  }))

  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { data: ['电影', '类型', '用户'], top: 10 },
    animationDuration: 600,
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      label: { show: true, fontSize: 10, position: 'right' },
      categories: [{ name: '电影' }, { name: '类型' }, { name: '用户' }],
      data: nodes,
      links,
      force: { repulsion: 300, edgeLength: [80, 200], gravity: 0.1 },
      lineStyle: { color: '#ccc', width: 1, curveness: 0.1 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
    }],
  })
}

const loadGlobal = async () => {
  currentMode = 'global'
  loading.value = true
  try {
    const res = await getGlobalGraph(nodeLimit.value, Math.max(10, Math.floor(nodeLimit.value / 2)))
    if (res.code === 200) renderGraph(res.data)
  } finally {
    loading.value = false
  }
}

const queryMovies = async (query, cb) => {
  if (!query) { cb([]); return }
  try {
    const res = await getMovieList({ keyword: query, page: 1, pageSize: 10 })
    if (res.code === 200) {
      const list = (res.data.list || []).map(m => ({
        value: m.movieId,
        label: m.title,
      }))
      cb(list)
    } else { cb([]) }
  } catch { cb([]) }
}

const handleSelect = (item) => {
  selectedMovieId.value = item.value
  loadMovieGraph(item.value)
}

const handleEnter = () => {
  if (selectedMovieId.value) loadMovieGraph(selectedMovieId.value)
}

const loadMovieGraph = async (movieId) => {
  if (!movieId) {
    ElMessage.warning('请先搜索并选择一部电影')
    return
  }
  currentMode = 'movie'
  loading.value = true
  try {
    const res = await getMovieGraph(movieId, nodeLimit.value)
    if (res.code === 200) renderGraph(res.data)
    else ElMessage.error(res.msg || '未找到该电影')
  } finally {
    loading.value = false
  }
}

const onLimitChange = () => {
  if (currentMode === 'movie' && selectedMovieId.value) {
    loadMovieGraph(selectedMovieId.value)
  } else {
    loadGlobal()
  }
}

onMounted(() => loadGlobal())

onBeforeUnmount(() => {
  if (chartInstance) chartInstance.dispose()
})
</script>

<style scoped>
.page-title { font-size: 22px; margin-bottom: 16px; color: #303133; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.graph-container { width: 100%; height: 600px; }
</style>

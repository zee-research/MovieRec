<!--
  知识图谱管理：可视化展示全局图谱
-->
<template>
  <div class="graph-manage">
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
      <span class="limit-label">电影数量：</span>
      <el-input-number v-model="limit" :min="5" :max="500" :step="10" size="small" style="width:130px" />
      <el-button size="small" @click="onLimitChange">刷新</el-button>
      <span v-if="nodeCount" class="limit-label">当前 {{ nodeCount }} 个节点</span>
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
const limit = ref(100)
const nodeCount = ref(0)
let chart = null
let currentMode = 'global'

const colorMap = { Movie: '#409EFF', Genre: '#67C23A', User: '#E6A23C' }

const typeNormalize = (t) => {
  if (!t) return ''
  const lower = t.toLowerCase()
  if (lower === 'movie') return 'Movie'
  if (lower === 'genre') return 'Genre'
  if (lower === 'user') return 'User'
  return t
}

const render = (data) => {
  if (!graphRef.value) return
  if (chart) chart.dispose()
  chart = echarts.init(graphRef.value)

  const nodes = (data.nodes || []).map(n => {
    const tp = typeNormalize(n.type)
    return {
      id: String(n.id), name: n.label || n.name || String(n.id),
      symbolSize: tp === 'Movie' ? 36 : 22,
      category: tp === 'Movie' ? 0 : (tp === 'Genre' ? 1 : 2),
      itemStyle: { color: colorMap[tp] || '#909399' },
    }
  })
  nodeCount.value = nodes.length
  const links = (data.links || []).map(l => ({
    source: String(l.source), target: String(l.target),
  }))

  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { data: ['电影', '类型', '用户'], top: 10 },
    series: [{
      type: 'graph', layout: 'force', roam: true, draggable: true,
      label: { show: true, fontSize: 10 },
      categories: [{ name: '电影' }, { name: '类型' }, { name: '用户' }],
      data: nodes, links,
      force: { repulsion: 250, edgeLength: [60, 180], gravity: 0.08 },
      lineStyle: { color: '#ccc', width: 1 },
      emphasis: { focus: 'adjacency' },
    }],
  })
}

const loadGlobal = async () => {
  currentMode = 'global'
  loading.value = true
  try {
    const res = await getGlobalGraph(limit.value, Math.max(10, Math.floor(limit.value / 2)))
    if (res.code === 200) render(res.data)
  } finally { loading.value = false }
}

const queryMovies = async (query, cb) => {
  if (!query) { cb([]); return }
  try {
    const res = await getMovieList({ keyword: query, page: 1, pageSize: 10 })
    if (res.code === 200) {
      const list = (res.data.list || []).map(m => ({ value: m.movieId, label: m.title }))
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
  if (!movieId) { ElMessage.warning('请先搜索并选择一部电影'); return }
  currentMode = 'movie'
  loading.value = true
  try {
    const res = await getMovieGraph(movieId, limit.value)
    if (res.code === 200) render(res.data)
    else ElMessage.error(res.msg || '未找到')
  } finally { loading.value = false }
}

const onLimitChange = () => {
  if (currentMode === 'movie' && selectedMovieId.value) {
    loadMovieGraph(selectedMovieId.value)
  } else {
    loadGlobal()
  }
}

onMounted(() => loadGlobal())
onBeforeUnmount(() => { if (chart) chart.dispose() })
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
.limit-label { font-size: 13px; color: #909399; white-space: nowrap; }
.graph-container { width: 100%; height: 600px; }
</style>

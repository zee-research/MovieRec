<!--
  管理端仪表盘：统计概览 + echarts 图表
-->
<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background:#409EFF"><el-icon :size="28"><Film /></el-icon></div>
          <div class="stat-text">
            <div class="stat-num">{{ stats.movieCount || 0 }}</div>
            <div class="stat-label">电影总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background:#67C23A"><el-icon :size="28"><User /></el-icon></div>
          <div class="stat-text">
            <div class="stat-num">{{ stats.userCount || 0 }}</div>
            <div class="stat-label">用户总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background:#E6A23C"><el-icon :size="28"><Star /></el-icon></div>
          <div class="stat-text">
            <div class="stat-num">{{ stats.avgRating || 0 }}</div>
            <div class="stat-label">平均评分</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background:#F56C6C"><el-icon :size="28"><Collection /></el-icon></div>
          <div class="stat-text">
            <div class="stat-num">{{ stats.genreCount || 0 }}</div>
            <div class="stat-label">类型总数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><span>评分分布</span></template>
          <div ref="ratingChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>电影类型分布</span></template>
          <div ref="genreChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { getStatistics, getRatingDistribution, getGenreStats } from '@/api/admin'
import * as echarts from 'echarts'

const stats = ref({})
const ratingChartRef = ref(null)
const genreChartRef = ref(null)
let ratingChart = null
let genreChart = null

// 加载统计
const loadStats = async () => {
  try {
    const res = await getStatistics()
    if (res.code === 200) stats.value = res.data || {}
  } catch (e) { /* ignore */ }
}

// 评分分布图表
const loadRatingDist = async () => {
  try {
    const res = await getRatingDistribution()
    if (res.code === 200 && ratingChartRef.value) {
      ratingChart = echarts.init(ratingChartRef.value)
      const data = res.data || []
      ratingChart.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: data.map(d => d.rating), name: '评分' },
        yAxis: { type: 'value', name: '数量' },
        series: [{
          type: 'bar',
          data: data.map(d => d.count),
          itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] },
        }],
        grid: { top: 30, bottom: 40, left: 60, right: 20 },
      })
    }
  } catch (e) { /* ignore */ }
}

// 类型分布图表
const loadGenreStats = async () => {
  try {
    const res = await getGenreStats()
    if (res.code === 200 && genreChartRef.value) {
      genreChart = echarts.init(genreChartRef.value)
      const data = res.data || []
      genreChart.setOption({
        tooltip: {
          formatter: (info) => {
            const val = info.value
            return `${info.name}: ${val} 部`
          },
        },
        series: [{
          type: 'treemap',
          data: data.map(d => ({ name: d.genre, value: d.count })),
          breadcrumb: { show: false },
          label: { show: true, formatter: '{b}\n{c}', fontSize: 12 },
          itemStyle: { borderColor: '#fff', borderWidth: 2, gapWidth: 2 },
          levels: [{
            itemStyle: { borderColor: '#fff', borderWidth: 2, gapWidth: 2 },
            upperLabel: { show: false },
          }],
        }],
      })
    }
  } catch (e) { /* ignore */ }
}

onMounted(() => {
  loadStats()
  loadRatingDist()
  loadGenreStats()
})

onBeforeUnmount(() => {
  if (ratingChart) ratingChart.dispose()
  if (genreChart) genreChart.dispose()
})
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card {
  display: flex; align-items: center; padding: 0;
}
.stat-card :deep(.el-card__body) {
  display: flex; align-items: center; gap: 16px; width: 100%; padding: 20px;
}
.stat-icon {
  width: 56px; height: 56px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0;
}
.stat-num { font-size: 24px; font-weight: 700; color: #303133; }
.stat-label { font-size: 13px; color: #909399; }
.chart-box { width: 100%; height: 320px; }
</style>

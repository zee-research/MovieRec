<!--
  模型评估：展示 CF / SVD / 混合 / KG 的 RMSE、MAE、Coverage（后台计算 + 轮询）
-->
<template>
  <div class="model-evaluate">
    <div class="toolbar">
      <el-button type="primary" :loading="loading" @click="runEvaluate">
        {{ loading ? `评估中（${completedCount}/4）…` : '运行模型评估' }}
      </el-button>
      <el-alert v-if="!started" title="点击按钮运行模型评估，结果将实时显示（切换页面不会中断计算）" type="info" show-icon :closable="false" />
    </div>

    <template v-if="started">
      <!-- 指标表格 -->
      <el-table :data="tableData" stripe border style="width:100%;margin-bottom:20px">
        <el-table-column prop="model" label="推荐算法" width="180" />
        <el-table-column prop="rmse" label="RMSE" width="120">
          <template #default="{ row }">
            <span v-if="row.pending" class="loading-dot">计算中…</span>
            <span v-else>{{ row.rmse ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="mae" label="MAE" width="120">
          <template #default="{ row }">
            <span v-if="row.pending" class="loading-dot">计算中…</span>
            <span v-else>{{ row.mae ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="coverage" label="Coverage (%)">
          <template #default="{ row }">
            <span v-if="row.pending" class="loading-dot">计算中…</span>
            <span v-else>{{ row.coverage != null ? row.coverage + '%' : '-' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 柱状图对比 -->
      <el-card>
        <template #header><span>模型指标对比</span></template>
        <div ref="chartRef" class="chart-box"></div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { startEvaluate, getEvaluateProgress } from '@/api/admin'
import * as echarts from 'echarts'

const loading = ref(false)
const started = ref(false)
const completedCount = ref(0)
const tableData = ref([])
const chartRef = ref(null)
const allResults = ref([])
let chart = null
let pollTimer = null

const MODEL_NAMES = ['协同过滤', 'SVD矩阵分解', '混合推荐模型', '知识图谱路径']

// 页面加载时检查是否有正在运行的评估任务
onMounted(async () => {
  try {
    const res = await getEvaluateProgress()
    if (res.code === 200 && res.data) {
      const { running, done, results } = res.data
      if (running || (done && results.length > 0)) {
        // 有正在运行或刚完成的任务，恢复显示
        started.value = true
        initTable()
        updateFromResults(results)
        if (running) {
          loading.value = true
          startPolling()
        }
      }
    }
  } catch (e) { /* 忽略 */ }
})

const initTable = () => {
  tableData.value = MODEL_NAMES.map(name => ({
    model: name, rmse: null, mae: null, coverage: null, pending: true
  }))
}

const updateFromResults = (results) => {
  allResults.value = results
  completedCount.value = results.length
  for (const val of results) {
    const idx = tableData.value.findIndex(r => r.model === val.method)
    if (idx >= 0) {
      tableData.value[idx] = {
        model: val.method,
        rmse: val.rmse != null ? Number(val.rmse).toFixed(4) : null,
        mae: val.mae != null ? Number(val.mae).toFixed(4) : null,
        coverage: val.coverage != null ? Number(val.coverage).toFixed(1) : null,
        pending: false,
      }
    }
  }
  nextTick(() => renderChart())
}

const runEvaluate = async () => {
  if (loading.value) return
  loading.value = true
  started.value = true
  completedCount.value = 0
  allResults.value = []
  initTable()

  try {
    const res = await startEvaluate()
    if (res.code === 200) {
      startPolling()
    } else {
      ElMessage.error(res.msg || '启动评估失败')
      loading.value = false
    }
  } catch (e) {
    ElMessage.error('启动评估失败')
    loading.value = false
  }
}

const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await getEvaluateProgress()
      if (res.code !== 200) return
      const { done, results } = res.data
      updateFromResults(results)
      if (done) {
        stopPolling()
        loading.value = false
        ElMessage.success('评估完成')
      }
    } catch (e) {
      console.warn('轮询失败:', e)
    }
  }, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const renderChart = () => {
  if (!chartRef.value) return
  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)

  const list = allResults.value
  const labels = MODEL_NAMES

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['RMSE', 'MAE', 'Coverage(%)'], top: 10 },
    xAxis: { type: 'category', data: labels },
    yAxis: [
      { type: 'value', name: 'RMSE / MAE', min: 0, max: 2, position: 'left' },
      { type: 'value', name: 'Coverage(%)', min: 0, max: 100, position: 'right' },
    ],
    grid: { top: 50, bottom: 30, left: 60, right: 60 },
    series: [
      {
        name: 'RMSE', type: 'bar', yAxisIndex: 0,
        data: labels.map(name => {
          const v = list.find(r => r.method === name)
          return v && v.rmse != null ? +Number(v.rmse).toFixed(4) : 0
        }),
        itemStyle: { color: '#409EFF' },
        barGap: '20%',
      },
      {
        name: 'MAE', type: 'bar', yAxisIndex: 0,
        data: labels.map(name => {
          const v = list.find(r => r.method === name)
          return v && v.mae != null ? +Number(v.mae).toFixed(4) : 0
        }),
        itemStyle: { color: '#67C23A' },
      },
      {
        name: 'Coverage(%)', type: 'bar', yAxisIndex: 1,
        data: labels.map(name => {
          const v = list.find(r => r.method === name)
          return v && v.coverage != null ? +Number(v.coverage).toFixed(1) : 0
        }),
        itemStyle: { color: '#E6A23C' },
      },
    ],
  })
}

onBeforeUnmount(() => {
  stopPolling()
  if (chart) chart.dispose()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 16px; align-items: center; margin-bottom: 20px; }
.chart-box { width: 100%; height: 380px; }
.loading-dot { color: #909399; font-size: 13px; }
</style>

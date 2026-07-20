<template>
  <div class="dashboard-page">
    <!-- ── 页面标题 + 时间范围选择 ── -->
    <div class="page-header">
      <h2>数据看板</h2>
      <el-radio-group v-model="periodDays" size="default" @change="loadAllData">
        <el-radio-button :value="7">近 7 天</el-radio-button>
        <el-radio-button :value="30">近 30 天</el-radio-button>
        <el-radio-button :value="90">近 90 天</el-radio-button>
      </el-radio-group>
    </div>

    <!-- ── 数字统计卡片 ── -->
    <el-row :gutter="16" class="stat-cards">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fdf6ec">
            <el-icon :size="28" color="#e6a23c"><Aim /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">
              {{ formatNumber(stats.total_objects) }}
            </div>
            <div class="stat-label">检测目标</div>
            <div class="stat-growth" :class="growthClass('objects')">
              {{ formatGrowth(stats.growth?.objects) }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ── 图表区域 ── -->
    <el-row :gutter="16" class="chart-row">
      <!-- 每日检测趋势（折线图） -->
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <span>每日检测趋势</span>
          </template>
          <div ref="trendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <!-- 类别分布（饼图） -->
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <span>类别分布</span>
          </template>
          <div ref="classChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ── 生成报告按钮 ── -->
    <div class="report-action">
      <el-button type="primary" size="large" @click="generateReport">
        📝 生成检测报告与防治建议
      </el-button>
    </div>
  </div>
</template>

<script setup>
/**
 * DashboardPage.vue — 数据看板
 *
 * 功能：
 *   - 数字统计卡片（检测目标数 + 环比增长）
 *   - ECharts 折线图：每日检测趋势
 *   - ECharts 饼图：类别分布
 */
import {
  getClassDistribution,
  getStatistics,
  getTrend,
} from "@/api/dashboard";
import { Aim } from "@element-plus/icons-vue";
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

// ── 响应式状态 ──
const periodDays = ref(30);
const stats = ref({
  total_objects: 0,
  growth: {},
});

// ── 图表 DOM 引用 ─
const trendChartRef = ref(null);
const classChartRef = ref(null);

// ── 图表实例（用于销毁） ──
let trendChart = null;
let classChart = null;

const router = useRouter();

// ── 格式化函数 ──
function formatNumber(num) {
  if (!num) return "0";
  if (num >= 10000) return (num / 10000).toFixed(1) + "w";
  if (num >= 1000) return (num / 1000).toFixed(1) + "k";
  return String(num);
}

function formatGrowth(value) {
  if (value === undefined || value === null) return "";
  if (value > 0) return `+${value}%`;
  if (value < 0) return `${value}%`;
  return "持平";
}

function growthClass(key, inverse = false) {
  const val = stats.value.growth?.[key];
  if (val === undefined || val === null || val === 0) return "growth-flat";
  // inverse=true 时，下降是好事（推理耗时越短越好）
  if (inverse) return val < 0 ? "growth-up" : "growth-down";
  return val > 0 ? "growth-up" : "growth-down";
}

// ── 加载所有数据 ──
async function loadAllData() {
  const days = periodDays.value;
  try {
    const [statsRes, trendRes, classRes] = await Promise.all([
      getStatistics(days),
      getTrend(days),
      getClassDistribution(days),
    ]);

    stats.value = statsRes;
    renderTrendChart(trendRes.trend);
    renderClassChart(classRes.distribution);
  } catch (err) {
    console.error("[看板数据加载失败]", err);
  }
}

// ── 渲染折线图：每日检测趋势 ──
function renderTrendChart(trend) {
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value);
  }

  const dates = trend.map((d) => d.date.slice(5)); // "MM-DD"
  const taskCounts = trend.map((d) => d.task_count);
  const objectCounts = trend.map((d) => d.object_count);

  trendChart.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
    },
    legend: {
      data: ["检测任务", "检测目标"],
      bottom: 0,
    },
    grid: {
      left: 50,
      right: 20,
      top: 20,
      bottom: 40,
    },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: { fontSize: 11 },
    },
    yAxis: [
      {
        type: "value",
        name: "任务数",
        axisLabel: { fontSize: 11 },
      },
      {
        type: "value",
        name: "目标数",
        axisLabel: { fontSize: 11 },
      },
    ],
    series: [
      {
        name: "检测任务",
        type: "line",
        data: taskCounts,
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(0,0,0,0.2)" },
            { offset: 1, color: "rgba(0,0,0,0.02)" },
          ]),
        },
        itemStyle: { color: "#1e1e1e" },
      },
      {
        name: "检测目标",
        type: "line",
        yAxisIndex: 1,
        data: objectCounts,
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(103,194,58,0.3)" },
            { offset: 1, color: "rgba(103,194,58,0.02)" },
          ]),
        },
        itemStyle: { color: "#67c23a" },
      },
    ],
  });
}

// ── 渲染饼图：类别分布 ──
function renderClassChart(distribution) {
  if (!classChart) {
    classChart = echarts.init(classChartRef.value);
  }

  classChart.setOption({
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} ({d}%)",
    },
    legend: {
      type: "scroll",
      orient: "horizontal",
      bottom: 0,
    },
    series: [
      {
        type: "pie",
        radius: "60%",
        center: ["50%", "45%"],
        data: distribution,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: "rgba(0,0,0,0.3)",
          },
        },
        label: {
          formatter: "{b}\n{c} ({d}%)",
          fontSize: 12,
        },
      },
    ],
  });
}

// ── 窗口 resize 时自动调整图表 ──
function handleResize() {
  trendChart?.resize();
  classChart?.resize();
}

onMounted(() => {
  loadAllData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  trendChart?.dispose();
  classChart?.dispose();
});

// ── 生成检测报告 ──
function generateReport() {
  router.push({ path: "/chat", query: { report: "1", days: periodDays.value } });
}
</script>

<style lang="scss" scoped>
.dashboard-page {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  h2 {
    margin: 0;
  }
}

/* 统计卡片 */
.stat-cards {
  margin-bottom: 16px;
}

.stat-card {
  :deep(.el-card__body) {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
  }
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;

  .unit {
    font-size: 14px;
    font-weight: 400;
    color: #909399;
    margin-left: 2px;
  }
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

.stat-growth {
  font-size: 12px;
  margin-top: 4px;

  &.growth-up {
    color: #67c23a;
    &::before {
      content: "↑ ";
    }
  }

  &.growth-down {
    color: #f56c6c;
    &::before {
      content: "↓ ";
    }
  }

  &.growth-flat {
    color: #909399;
  }
}

/* 图表区域 */
.chart-row {
  margin-bottom: 16px;
}

.chart-container {
  height: 320px;
  width: 100%;
}

.report-action {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  margin-bottom: 16px;
}
</style>

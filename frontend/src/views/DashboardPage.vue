<template>
  <div class="dashboard-page">
    <!-- ── 页面标题 + 时间范围选择 ── -->
    <div class="page-header">
      <h2>{{ $t('dashboard.title') }}</h2>
      <el-radio-group v-model="periodDays" size="default" @change="loadAllData">
        <el-radio-button :value="7">{{ $t('dashboard.period7') }}</el-radio-button>
        <el-radio-button :value="30">{{ $t('dashboard.period30') }}</el-radio-button>
        <el-radio-button :value="90">{{ $t('dashboard.period90') }}</el-radio-button>
      </el-radio-group>
    </div>

    <!-- ── 数字统计卡片 + 生成报告 ── -->
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
            <div class="stat-label">{{ $t('dashboard.totalObjects') }}</div>
            <div class="stat-growth" :class="growthClass('objects')">
              {{ formatGrowth(stats.growth?.objects) }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card report-card" @click="generateReport">
          <div class="stat-icon" style="background: #ecf5ff">
            <el-icon :size="28" color="#409eff"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="report-title">{{ $t('dashboard.generateReport') }}</div>
            <div class="stat-label">{{ $t('dashboard.reportHint') }}</div>
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
            <span>{{ $t('dashboard.dailyTrend') }}</span>
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
            <span>{{ $t('dashboard.classDist') }}</span>
          </template>
          <div ref="classChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ── 杂草地理分布热力图 ── -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <span>{{ $t('dashboard.geoHeatmap') }}</span>
          </template>
          <div v-if="geoPoints.length > 0" ref="heatmapRef" class="heatmap-container"></div>
          <el-empty v-else :description="$t('dashboard.noGeoData')" />
        </el-card>
      </el-col>
    </el-row>


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
  getGeoDistribution,
  getStatistics,
  getTrend,
} from "@/api/dashboard";
import { Aim, Document } from "@element-plus/icons-vue";
import * as echarts from "echarts";
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

// ── 响应式状态 ──
const periodDays = ref(30);
const stats = ref({
  total_objects: 0,
  growth: {},
});

// ── 图表 DOM 引用 ─
const trendChartRef = ref(null);
const classChartRef = ref(null);
const heatmapRef = ref(null);

// ── 地理分布数据 ──
const geoPoints = ref([]);

// ── 图表实例（用于销毁） ──
let trendChart = null;
let classChart = null;
let amapInstance = null;

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
  return t('dashboard.growthFlat');
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
    const [statsRes, trendRes, classRes, geoRes] = await Promise.all([
      getStatistics(days),
      getTrend(days),
      getClassDistribution(days),
      getGeoDistribution(days).catch(() => ({ points: [] })),
    ]);

    stats.value = statsRes;
    renderTrendChart(trendRes.trend);
    renderClassChart(classRes.distribution);
    geoPoints.value = geoRes.points || [];
    if (geoPoints.value.length > 0) {
      // 等待 DOM 更新后渲染地图
      await nextTick();
      renderHeatmap(geoPoints.value);
    }
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
      data: [t('dashboard.detectionTasks'), t('dashboard.detectionObjects')],
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
        name: t('dashboard.taskCount'),
        axisLabel: { fontSize: 11 },
      },
      {
        type: "value",
        name: t('dashboard.objectCount'),
        axisLabel: { fontSize: 11 },
      },
    ],
    series: [
      {
        name: t('dashboard.detectionTasks'),
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
        name: t('dashboard.detectionObjects'),
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

// ── 渲染高德地图热力图 ──
function renderHeatmap(points) {
  if (!heatmapRef.value || !window.AMap) return;

  if (amapInstance) {
    amapInstance.destroy();
    amapInstance = null;
  }

  const map = new window.AMap.Map(heatmapRef.value, {
    zoom: 5,
    center: [104.5, 35.5], // 中国中心
    mapStyle: "amap://styles/light",
  });
  amapInstance = map;

  // 构建热力图数据
  const heatData = points.map((p) => ({
    lng: p.lng,
    lat: p.lat,
    count: p.count || 1,
  }));

  // 添加标记点 + 信息窗体
  points.forEach((p) => {
    const marker = new window.AMap.Marker({
      position: [p.lng, p.lat],
      title: p.location_name || `${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}`,
    });
    const info = new window.AMap.InfoWindow({
      content: `<div style="padding:4px 8px;font-size:13px">
        <strong>${p.location_name || '未命名位置'}</strong><br/>
        检测目标: ${p.count || 0}<br/>
        主要杂草: ${p.class_name_cn || '-'}
      </div>`,
      offset: new window.AMap.Pixel(0, -28),
    });
    marker.on("click", () => info.open(map, marker.getPosition()));
    map.add(marker);
  });

  // 添加热力图图层（AMap v2.0 使用 AMap.plugin）
  window.AMap.plugin(["AMap.HeatMap"], () => {
    const heatmap = new window.AMap.HeatMap(map, {
      radius: 30,
      opacity: [0, 0.8],
      gradient: {
        0.2: "#0ff",
        0.4: "#0f0",
        0.6: "#ff0",
        0.8: "#f00",
        1.0: "#f0f",
      },
    });
    heatmap.setDataSet({
      data: heatData,
      max: Math.max(...heatData.map((d) => d.count), 5),
    });
  });

  // 自动调整视野以包含所有数据点
  if (points.length > 1) {
    const bounds = new window.AMap.Bounds(
      [Math.min(...points.map((p) => p.lng)), Math.min(...points.map((p) => p.lat))],
      [Math.max(...points.map((p) => p.lng)), Math.max(...points.map((p) => p.lat))]
    );
    map.setBounds(bounds, false, [60, 60, 60, 60]);
  }
}

onMounted(() => {
  loadAllData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  trendChart?.dispose();
  classChart?.dispose();
  amapInstance?.destroy();
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

.heatmap-container {
  height: 450px;
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
}

.report-card {
  cursor: pointer;
  transition: border-color 0.2s;

  &:hover {
    border-color: #409eff;
  }
}

.report-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
}
</style>

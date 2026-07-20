<template>
  <div class="page-container">

    <PageHeader
      title="数据看板"
      subtitle="查看平台检测统计、趋势分析和数据分布。"
    >
      <template #actions>
        <el-radio-group
          v-model="periodDays"
          @change="loadAllData"
        >
          <el-radio-button :label="7">
            近 7 天
          </el-radio-button>

          <el-radio-button :label="30">
            近 30 天
          </el-radio-button>

          <el-radio-button :label="90">
            近 90 天
          </el-radio-button>
        </el-radio-group>
      </template>
    </PageHeader>

    <!-- Statistics -->

    <div class="stats-grid">

      <StatsCard
        title="检测任务"
        :value="stats.total_tasks"
        :growth="stats.growth?.tasks"
        :icon="Document"
      />

      <StatsCard
        title="处理图片"
        :value="formatNumber(stats.total_images)"
        :growth="stats.growth?.images"
        :icon="PictureFilled"
      />

      <StatsCard
        title="检测目标"
        :value="formatNumber(stats.total_objects)"
        :growth="stats.growth?.objects"
        :icon="Aim"
      />

      <StatsCard
        title="平均耗时"
        :value="stats.avg_inference_time"
        unit="ms"
        :growth="stats.growth?.inference_time"
        :inverse="true"
        :icon="Timer"
      />

    </div>

    <!-- Charts -->

    <el-row :gutter="20">

      <el-col :span="16">

        <SectionCard title="每日检测趋势">

          <div
            ref="trendChartRef"
            class="chart-container"
          />

        </SectionCard>

      </el-col>

      <el-col :span="8">

        <SectionCard title="类别分布">

          <div
            ref="classChartRef"
            class="chart-container"
          />

        </SectionCard>

      </el-col>

    </el-row>

    <el-row
      :gutter="20"
      style="margin-top:20px"
    >

      <el-col :span="12">

        <SectionCard title="场景分布">

          <div
            ref="sceneChartRef"
            class="chart-container"
          />

        </SectionCard>

      </el-col>

      <el-col :span="12">

        <SectionCard title="任务类型分布">

          <div
            ref="typeChartRef"
            class="chart-container"
          />

        </SectionCard>

      </el-col>

    </el-row>

  </div>
</template>

<script setup>
/**
 * DashboardPage.vue — 数据看板
 *
 * 功能：
 *   - 数字统计卡片（带环比增长率）
 *   - ECharts 折线图：每日检测趋势
 *   - ECharts 饼图：类别分布
 *   - ECharts 柱状图：场景分布
 *   - ECharts 环形图：任务类型分布
 */
import {
  getClassDistribution,
  getSceneDistribution,
  getStatistics,
  getTrend,
  getTypeDistribution,
} from "@/api/dashboard";

import {
  Aim,
  Document,
  PictureFilled,
  Timer,
} from "@element-plus/icons-vue";

import PageHeader from "@/components/common/PageHeader.vue";
import SectionCard from "@/components/common/SectionCard.vue";
import StatsCard from "@/components/common/StatsCard.vue";

import * as echarts from "echarts";

import {
  onMounted,
  onBeforeUnmount,
  ref,
} from "vue";

// ── 主题色板（平台主题配色） ──
const THEME_COLORS = [
  "#4CAF50",
  "#66BB6A",
  "#81C784",
  "#2E7D32",
  "#A5D6A7",
];

// ── 响应式状态 ──
const periodDays = ref(30);
const stats = ref({
  total_tasks: 0,
  total_images: 0,
  total_objects: 0,
  avg_inference_time: 0,
  growth: {},
});

// ── 图表 DOM 引用 ─
const trendChartRef = ref(null);
const classChartRef = ref(null);
const sceneChartRef = ref(null);
const typeChartRef = ref(null);

// ── 图表实例（用于销毁） ──
let trendChart = null;
let classChart = null;
let sceneChart = null;
let typeChart = null;

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
    // 并行请求所有 API
    const [statsRes, trendRes, classRes, sceneRes, typeRes] = await Promise.all(
      [
        getStatistics(days),
        getTrend(days),
        getClassDistribution(days),
        getSceneDistribution(days),
        getTypeDistribution(days),
      ],
    );

    stats.value = statsRes;
    renderTrendChart(trendRes.trend);
    renderClassChart(classRes.distribution);
    renderSceneChart(sceneRes.distribution);
    renderTypeChart(typeRes.distribution);
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
            { offset: 0, color:"rgba(76,175,80,.25)" },
            { offset: 1, color: "rgba(217,119,6,0.02)" },
          ]),
        },
        itemStyle:{
          color:"#4CAF50"
        }
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
            { offset: 0, color: "rgba(102,187,106,.25)" },
            { offset: 1, color: "rgba(217,119,6,0.02)" },
          ]),
        },
        itemStyle: { color: "#66BB6A" },
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
      orient: "vertical",
      right: 10,
      top: 20,
      bottom: 20,
    },
    color: THEME_COLORS,
    series: [
      {
        type: "pie",
        radius: "65%",
        center: ["35%", "50%"],
        data: distribution,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: "rgba(0,0,0,0.3)",
          },
        },
        label: {
          formatter: "{b}\n{d}%",
          fontSize: 12,
        },
      },
    ],
  });
}

// ── 渲染柱状图：场景分布 ──
function renderSceneChart(distribution) {
  if (!sceneChart) {
    sceneChart = echarts.init(sceneChartRef.value);
  }

  sceneChart.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    grid: {
      left: 80,
      right: 20,
      top: 20,
      bottom: 30,
    },
    xAxis: {
      type: "value",
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: "category",
      data: distribution.map((d) => d.name),
      axisLabel: { fontSize: 12 },
    },
    series: [
      {
        type: "bar",
        data: distribution.map((d) => d.value),
        barWidth: "50%",
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: "#2E7D32" },
            { offset: 1, color: "#81C784" },
          ]),
        },
        label: {
          show: true,
          position: "right",
          fontSize: 12,
        },
      },
    ],
  });
}

// ── 渲染环形图：任务类型分布 ──
function renderTypeChart(distribution) {
  if (!typeChart) {
    typeChart = echarts.init(typeChartRef.value);
  }

  typeChart.setOption({
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c} ({d}%)",
    },
    legend: {
      bottom: 0,
      itemGap: 16,
    },
    color: THEME_COLORS,
    series: [
      {
        type: "pie",
        radius: ["40%", "65%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: false,
        data: distribution,
        label: {
          show: true,
          formatter: "{b}\n{d}%",
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: "bold",
          },
        },
      },
    ],
  });
}

// ── 窗口 resize 时自动调整图表 ──
function handleResize() {
  trendChart?.resize();
  classChart?.resize();
  sceneChart?.resize();
  typeChart?.resize();
}

onMounted(() => {
  loadAllData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  trendChart?.dispose();
  classChart?.dispose();
  sceneChart?.dispose();
  typeChart?.dispose();
});
</script>

<style lang="scss" scoped>

.chart-container {
  height: 320px;
  width: 100%;
}
</style>
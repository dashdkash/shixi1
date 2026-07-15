<template>
  <div class="training-page">
    <div class="page-header">
      <h2>{{ $t("training.title") }}</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>{{ $t("training.createTask") }}
      </el-button>
    </div>

    <el-card class="task-list-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t("training.taskList") }}</span>
          <el-button text @click="fetchTasks">
            <el-icon><Refresh /></el-icon>{{ $t("training.refresh") }}
          </el-button>
        </div>
      </template>

      <el-table
        :data="taskList"
        stripe
        style="width: 100%"
        v-loading="loadingTasks"
      >
        <el-table-column
          prop="task_uuid"
          :label="$t('training.taskId')"
          width="100"
        />
        <el-table-column
          prop="model_name"
          :label="$t('training.model')"
          width="110"
        />
        <el-table-column
          prop="device"
          :label="$t('training.device')"
          width="80"
        />
        <el-table-column :label="$t('training.progress')" width="180">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :status="
                row.status === 'completed'
                  ? 'success'
                  : row.status === 'failed'
                    ? 'exception'
                    : ''
              "
              :stroke-width="16"
            />
          </template>
        </el-table-column>
        <el-table-column :label="$t('training.epoch')" width="100">
          <template #default="{ row }">
            {{ row.current_epoch }}/{{ row.epochs }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('training.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          :label="$t('training.createTime')"
          width="170"
        />
        <el-table-column
          :label="$t('training.action')"
          width="200"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              text
              @click="selectTask(row)"
            >
              {{ $t("training.monitor") }}
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="danger"
              text
              @click="stopTask(row.id)"
            >
              {{ $t("training.stop") }}
            </el-button>
            <el-button
              v-if="row.status === 'completed'"
              size="small"
              text
              @click="downloadModel(row.id)"
            >
              {{ $t("training.download") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="selectedTask" class="monitor-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>
            {{ $t("training.monitor") }} — {{ $t("training.task") }}
            {{ selectedTask.task_uuid }}
            <el-tag
              :type="statusType(selectedTask.status)"
              size="small"
              style="margin-left: 8px"
            >
              {{ statusText(selectedTask.status) }}
            </el-tag>
          </span>
          <div class="monitor-info">
            <span
              >{{ $t("training.model") }}: {{ selectedTask.model_name }}</span
            >
            <span>{{ $t("training.device") }}: {{ selectedTask.device }}</span>
            <span
              >{{ $t("training.epoch") }}: {{ selectedTask.current_epoch }}/{{
                selectedTask.epochs
              }}</span
            >
          </div>
        </div>
      </template>

      <el-row :gutter="16" class="metric-cards">
        <el-col :span="4" v-for="item in metricCards" :key="item.label">
          <el-card shadow="hover" class="metric-item">
            <div class="metric-value">{{ item.value }}</div>
            <div class="metric-label">{{ item.label }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <div ref="lossChartRef" style="height: 350px"></div>
        </el-col>
        <el-col :span="12">
          <div ref="mapChartRef" style="height: 350px"></div>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog
      v-model="showCreateDialog"
      :title="$t('training.createTask')"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="trainForm" label-width="120px">
        <el-form-item :label="$t('training.scene')">
          <el-select
            v-model="trainForm.scene_id"
            :placeholder="$t('training.selectScene')"
          >
            <el-option
              v-for="scene in scenes"
              :key="scene.id"
              :label="scene.display_name || scene.name"
              :value="scene.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('training.baseModel')">
          <el-select v-model="trainForm.model_name">
            <el-option :label="$t('training.yolov11n')" value="yolov11n" />
            <el-option :label="$t('training.yolov11s')" value="yolov11s" />
            <el-option :label="$t('training.yolov11m')" value="yolov11m" />
            <el-option :label="$t('training.yolov11l')" value="yolov11l" />
            <el-option :label="$t('training.yolov11x')" value="yolov11x" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('training.epochs')">
          <el-slider
            v-model="trainForm.epochs"
            :min="10"
            :max="500"
            :step="10"
            show-input
          />
        </el-form-item>

        <el-form-item :label="$t('training.batchSize')">
          <el-input-number
            v-model="trainForm.batch_size"
            :min="1"
            :max="64"
            :step="2"
          />
        </el-form-item>

        <el-form-item :label="$t('training.imgSize')">
          <el-select v-model="trainForm.img_size">
            <el-option :label="416" :value="416" />
            <el-option :label="512" :value="512" />
            <el-option :label="$t('training.default')" :value="640" />
            <el-option :label="768" :value="768" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('training.device')">
          <el-radio-group v-model="trainForm.device">
            <el-radio value="cpu">CPU ({{ $t("training.local") }})</el-radio>
            <el-radio value="0">GPU:0</el-radio>
            <el-radio value="1">GPU:1</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="$t('training.optimizer')">
          <el-select v-model="trainForm.optimizer">
            <el-option :label="$t('training.sgd')" value="SGD" />
            <el-option :label="Adam" value="Adam" />
            <el-option :label="AdamW" value="AdamW" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('training.lr0')">
          <el-input-number
            v-model="trainForm.lr0"
            :min="0.0001"
            :max="0.1"
            :step="0.001"
            :precision="4"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">{{
          $t("training.cancel")
        }}</el-button>
        <el-button type="primary" @click="createTask" :loading="creating">
          {{ $t("training.startTrain") }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import request from "@/utils/request";
import { Plus, Refresh } from "@element-plus/icons-vue";
import * as echarts from "echarts";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n({ useScope: "global" });

const taskList = ref([]);
const loadingTasks = ref(false);
const selectedTask = ref(null);
const showCreateDialog = ref(false);
const creating = ref(false);
const scenes = ref([]);

const lossChartRef = ref(null);
const mapChartRef = ref(null);
let lossChart = null;
let mapChart = null;

let pollTimer = null;

const trainForm = ref({
  scene_id: null,
  model_name: "yolov11n",
  epochs: 50,
  batch_size: 8,
  img_size: 640,
  device: "cpu",
  optimizer: "SGD",
  lr0: 0.01,
});

const metricCards = computed(() => {
  if (!selectedTask.value) return [];
  const m = selectedTask.value.latest_metric;
  if (!m)
    return [
      {
        label: t("training.epoch"),
        value: `${selectedTask.value.current_epoch}/${selectedTask.value.epochs}`,
      },
      {
        label: t("training.progress"),
        value: `${selectedTask.value.progress}%`,
      },
      { label: t("training.boxLoss"), value: "-" },
      { label: t("training.clsLoss"), value: "-" },
      { label: t("training.map50"), value: "-" },
      { label: t("training.map5095"), value: "-" },
    ];
  return [
    {
      label: t("training.epoch"),
      value: `${m.epoch}/${selectedTask.value.epochs}`,
    },
    {
      label: t("training.boxLoss"),
      value: m.box_loss != null ? m.box_loss.toFixed(4) : "-",
    },
    {
      label: t("training.clsLoss"),
      value: m.cls_loss != null ? m.cls_loss.toFixed(4) : "-",
    },
    {
      label: t("training.precision"),
      value: m.precision != null ? (m.precision * 100).toFixed(1) + "%" : "-",
    },
    {
      label: t("training.map50"),
      value: m.map50 != null ? (m.map50 * 100).toFixed(1) + "%" : "-",
    },
    {
      label: t("training.map5095"),
      value: m.map50_95 != null ? (m.map50_95 * 100).toFixed(1) + "%" : "-",
    },
  ];
});

function statusType(status) {
  const map = {
    pending: "info",
    running: "warning",
    completed: "success",
    failed: "danger",
    cancelled: "info",
  };
  return map[status] || "info";
}

function statusText(status) {
  const map = {
    pending: t("training.statusPending"),
    running: t("training.statusRunning"),
    completed: t("training.statusCompleted"),
    failed: t("training.statusFailed"),
    cancelled: t("training.statusCancelled"),
  };
  return map[status] || status;
}

async function fetchTasks() {
  loadingTasks.value = true;
  try {
    const res = await request.get("/training/tasks");
    taskList.value = res.items || [];
  } catch (e) {
    console.error(t("training.fetchError"), e);
  } finally {
    loadingTasks.value = false;
  }
}

async function fetchScenes() {
  try {
    const res = await request.get("/training/scenes");
    scenes.value = res.items || [];
    if (scenes.value.length > 0 && !trainForm.value.scene_id) {
      trainForm.value.scene_id = scenes.value[0].id;
    }
  } catch (e) {
    console.error(t("training.fetchScenesError"), e);
  }
}

async function selectTask(task) {
  selectedTask.value = task;
  await nextTick();
  initCharts();
  fetchMetrics();
  startPolling();
}

function initCharts() {
  if (lossChart) lossChart.dispose();
  if (mapChart) mapChart.dispose();

  if (lossChartRef.value) {
    lossChart = echarts.init(lossChartRef.value);
  }
  if (mapChartRef.value) {
    mapChart = echarts.init(mapChartRef.value);
  }
}

async function fetchMetrics() {
  if (!selectedTask.value) return;
  try {
    const taskId = selectedTask.value.id;
    const res = await request.get(`/training/metrics/${taskId}`);
    const metrics = res.metrics || [];

    const statusRes = await request.get(`/training/status/${taskId}`);
    if (statusRes.task) {
      selectedTask.value = {
        ...selectedTask.value,
        ...statusRes.task,
        latest_metric: statusRes.latest_metric,
      };
    }

    if (metrics.length > 0) {
      updateCharts(metrics);
    }
  } catch (e) {
    console.error(t("training.fetchMetricsError"), e);
  }
}

function updateCharts(metrics) {
  const epochs = metrics.map((m) => m.epoch);

  if (lossChart) {
    lossChart.setOption({
      title: {
        text: t("training.lossCurve"),
        left: "center",
        textStyle: { fontSize: 14 },
      },
      tooltip: { trigger: "axis" },
      legend: { data: ["Box Loss", "Cls Loss", "DFL Loss"], bottom: 0 },
      grid: { left: "10%", right: "5%", top: "15%", bottom: "15%" },
      xAxis: { type: "category", data: epochs, name: "Epoch" },
      yAxis: { type: "value", name: "Loss" },
      series: [
        {
          name: "Box Loss",
          type: "line",
          data: metrics.map((m) => m.box_loss),
          smooth: true,
          lineStyle: { width: 2 },
        },
        {
          name: "Cls Loss",
          type: "line",
          data: metrics.map((m) => m.cls_loss),
          smooth: true,
          lineStyle: { width: 2 },
        },
        {
          name: "DFL Loss",
          type: "line",
          data: metrics.map((m) => m.dfl_loss),
          smooth: true,
          lineStyle: { width: 2 },
        },
      ],
    });
  }

  if (mapChart) {
    mapChart.setOption({
      title: {
        text: t("training.metricCurve"),
        left: "center",
        textStyle: { fontSize: 14 },
      },
      tooltip: { trigger: "axis" },
      legend: {
        data: ["mAP@50", "mAP@50-95", "Precision", "Recall"],
        bottom: 0,
      },
      grid: { left: "10%", right: "5%", top: "15%", bottom: "15%" },
      xAxis: { type: "category", data: epochs, name: "Epoch" },
      yAxis: { type: "value", name: t("training.metricValue"), max: 1 },
      series: [
        {
          name: "mAP@50",
          type: "line",
          data: metrics.map((m) => m.map50),
          smooth: true,
          lineStyle: { width: 2, color: "#409eff" },
          itemStyle: { color: "#409eff" },
        },
        {
          name: "mAP@50-95",
          type: "line",
          data: metrics.map((m) => m.map50_95),
          smooth: true,
          lineStyle: { width: 2, color: "#67c23a" },
          itemStyle: { color: "#67c23a" },
        },
        {
          name: "Precision",
          type: "line",
          data: metrics.map((m) => m.precision),
          smooth: true,
          lineStyle: { width: 2, type: "dashed", color: "#e6a23c" },
          itemStyle: { color: "#e6a23c" },
        },
        {
          name: "Recall",
          type: "line",
          data: metrics.map((m) => m.recall),
          smooth: true,
          lineStyle: { width: 2, type: "dashed", color: "#f56c6c" },
          itemStyle: { color: "#f56c6c" },
        },
      ],
    });
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(() => {
    if (selectedTask.value) {
      fetchMetrics();
    }
  }, 5000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function createTask() {
  if (!trainForm.value.scene_id) {
    ElMessage.warning(t("training.selectSceneFirst"));
    return;
  }

  creating.value = true;
  try {
    const res = await request.post("/training/start", trainForm.value);
    ElMessage.success(`${t("training.createSuccess")} ${res.task_uuid}`);
    showCreateDialog.value = false;
    await fetchTasks();
    if (res.id) {
      const newTask = taskList.value.find((t) => t.id === res.id);
      if (newTask) selectTask(newTask);
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t("training.createFailed"));
  } finally {
    creating.value = false;
  }
}

async function stopTask(taskId) {
  try {
    await ElMessageBox.confirm(
      t("training.confirmStop"),
      t("training.confirm"),
      {
        type: "warning",
      },
    );
    await request.post(`/training/stop/${taskId}`);
    ElMessage.success(t("training.stopSuccess"));
    await fetchTasks();
  } catch (e) {
    if (e !== "cancel") {
      ElMessage.error(t("training.stopFailed"));
    }
  }
}

async function downloadModel(taskId) {
  try {
    const response = await request.get(`/training/download/${taskId}`, {
      responseType: "blob",
    });
    const blob = new Blob([response]);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `model_${taskId}.pt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    ElMessage.success(t("training.downloadSuccess"));
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t("training.downloadFailed"));
  }
}

onMounted(() => {
  fetchTasks();
  fetchScenes();
});

onBeforeUnmount(() => {
  stopPolling();
  if (lossChart) lossChart.dispose();
  if (mapChart) mapChart.dispose();
});
</script>

<style scoped>
.training-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.monitor-info {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #909399;
}

.metric-cards {
  margin-bottom: 8px;
}

.metric-item {
  text-align: center;
  padding: 8px 0;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.task-list-card,
.monitor-card {
  margin-bottom: 20px;
}
</style>

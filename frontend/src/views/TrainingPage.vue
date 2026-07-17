<template>
  <div class="training-page">
    <div class="page-header">
      <h2>{{ $t("training.title") }}</h2>
      <div>
        <el-button text @click="fetchTasks">
          <el-icon><Refresh /></el-icon>{{ $t("training.refresh") }}
        </el-button>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>{{ $t("training.createTask") }}
        </el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="12">
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
                {{ row.current_epoch || 0 }}/{{ row.epochs }}
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
              width="420"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button size="small" type="primary" text @click="selectTask(row)">
                  {{ $t("training.monitor") }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  type="success"
                  text
                  @click="validateModel(row)"
                  :loading="validating && selectedTask?.id === row.id"
                >
                  {{ $t("training.evaluate") }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  type="warning"
                  text
                  @click="exportModel(row)"
                  :loading="exporting && selectedTask?.id === row.id"
                >
                  {{ $t("training.export") }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  type="info"
                  text
                  @click="openPredictDialog(row)"
                >
                  {{ $t("training.validate") }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  type="primary"
                  text
                  @click="openResumeDialog(row)"
                >
                  {{ $t("training.resume") }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  text
                  @click="downloadModel(row)"
                >
                  {{ $t("training.download") }}
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
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="model-list-card" shadow="never">
          <template #header>
            <span>{{ $t("training.modelList") }}</span>
            <el-button type="primary" size="small" @click="fetchModels">
              <el-icon><Refresh /></el-icon>{{ $t("training.refresh") }}
            </el-button>
          </template>
          <el-table
            :data="modelList"
            v-loading="loadingModels"
            style="width: 100%"
            stripe
          >
            <el-table-column prop="id" :label="$t('training.id')" width="60" />
            <el-table-column prop="model_name" :label="$t('training.modelName')" width="150" />
            <el-table-column prop="version" :label="$t('training.version')" width="100" />
            <el-table-column prop="model_type" :label="$t('training.type')" width="100" />
            <el-table-column prop="map50" :label="$t('training.map50')" width="100">
              <template #default="{ row }">
                {{ row.map50 !== null ? (row.map50 * 100).toFixed(1) + '%' : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="file_size" :label="$t('training.size')" width="100">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('training.status')" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_default ? 'success' : 'info'" size="small">
                  {{ row.is_default ? $t("training.default") : $t("training.active") }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="$t('training.createTime')" width="170" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

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
              >{{ $t("training.epoch") }}: {{ selectedTask.current_epoch || 0 }}/{{
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

    <el-card v-if="evalReport" class="eval-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>
            {{ $t("training.evalReport") }}
            <el-tag size="small" style="margin-left: 8px">
              {{ evalReport.split === 'val' ? $t("training.valSet") : $t("training.testSet") }}
            </el-tag>
            <el-tag
              size="small"
              style="margin-left: 8px"
              :type="evalReport.overall?.map50 > 0.5 ? 'success' : 'warning'"
            >
              mAP@50: {{ ((evalReport.overall?.map50 || 0) * 100).toFixed(1) }}%
            </el-tag>
          </span>
          <el-button size="small" @click="evalReport = null">{{ $t("training.close") }}</el-button>
        </div>
      </template>

      <el-row :gutter="16" class="metric-cards">
        <el-col :span="6" v-for="item in evalMetricCards" :key="item.label">
          <el-card shadow="hover" class="metric-item">
            <div class="metric-value" :style="{ color: item.color }">
              {{ item.value }}
            </div>
            <div class="metric-label">{{ item.label }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-table
        :data="perClassData"
        stripe
        style="width: 100%; margin-top: 16px"
        max-height="300"
      >
        <el-table-column prop="class_name" :label="$t('training.className')" width="200" />
        <el-table-column prop="ap50" :label="$t('training.ap50')" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.ap50 < 0.5 ? '#f56c6c' : '#67c23a' }">
              {{ (row.ap50 * 100).toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="ap50_95" :label="$t('training.ap5095')" width="120">
          <template #default="{ row }">
            {{ (row.ap50_95 * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column :label="$t('training.evaluation')">
          <template #default="{ row }">
            <el-tag
              :type="row.ap50 >= 0.7 ? 'success' : row.ap50 >= 0.5 ? 'warning' : 'danger'"
              size="small"
            >
              {{ row.ap50 >= 0.7 ? $t("training.excellent") : row.ap50 >= 0.5 ? $t("training.good") : $t("training.needImprove") }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
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

    <el-dialog
      v-model="showResumeDialog"
      :title="$t('training.resume')"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="resumeForm" label-width="120px">
        <el-form-item :label="$t('training.sourceTask')">
          <el-card shadow="never" class="source-task-info">
            <div>{{ $t("training.taskId") }}: {{ resumeSourceTask?.id }}</div>
            <div>{{ $t("training.model") }}: {{ resumeSourceTask?.model_name }}</div>
            <div>{{ $t("training.completed") }}: {{ resumeSourceTask?.current_epoch || 0 }}/{{ resumeSourceTask?.epochs || 0 }} {{ $t("training.epochs") }}</div>
          </el-card>
        </el-form-item>

        <el-form-item :label="$t('training.newEpochs')">
          <el-slider
            v-model="resumeForm.epochs"
            :min="(resumeSourceTask?.epochs || 100) + 10"
            :max="500"
            :step="10"
            show-input
          />
          <div style="color: #909399; font-size: 12px; margin-top: 4px">
            {{ $t("training.resumeTo") }} {{ resumeForm.epochs }} {{ $t("training.epochs") }}（{{ $t("training.append") }} {{ resumeForm.epochs - (resumeSourceTask?.current_epoch || 0) }} {{ $t("training.epochs") }}）
          </div>
        </el-form-item>

        <el-form-item :label="$t('training.device')">
          <el-radio-group v-model="resumeForm.device">
            <el-radio value="cpu">CPU ({{ $t("training.local") }})</el-radio>
            <el-radio value="0">GPU: 0</el-radio>
            <el-radio value="1">GPU: 1</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="$t('training.batchSize')">
          <el-input-number
            v-model="resumeForm.batch_size"
            :min="1"
            :max="64"
            :step="2"
          />
        </el-form-item>

        <el-form-item :label="$t('training.lr0')">
          <el-input-number
            v-model="resumeForm.lr0"
            :min="0.0001"
            :max="0.1"
            :step="0.001"
            :precision="4"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showResumeDialog = false">{{ $t("training.cancel") }}</el-button>
        <el-button type="primary" @click="resumeTask" :loading="resuming">
          {{ $t("training.startResume") }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPredictDialog" :title="$t('training.predict')" width="900px" :close-on-click-modal="false">
      <el-row :gutter="16">
        <el-col :span="10">
          <el-upload
            class="predict-upload"
            drag
            action=""
            :auto-upload="false"
            :on-change="handlePredictFileChange"
            accept="image/*"
            :limit="1"
            :file-list="predictFileList"
          >
            <el-icon style="font-size: 40px; color: #909399"><UploadFilled /></el-icon>
            <div>{{ $t("training.dragOrClick") }}</div>
            <template #tip>
              <div class="el-upload__tip">{{ $t("training.supportFormats") }}</div>
            </template>
          </el-upload>

          <el-form label-width="80px" style="margin-top: 16px">
            <el-form-item :label="$t('training.confidence')">
              <el-slider v-model="predictConf" :min="0.05" :max="0.95" :step="0.05" show-input />
            </el-form-item>
            <el-form-item :label="$t('training.iou')">
              <el-slider v-model="predictIou" :min="0.1" :max="0.9" :step="0.05" show-input />
            </el-form-item>
          </el-form>

          <el-button
            type="primary"
            style="width: 100%; margin-top: 8px"
            @click="runPredict"
            :loading="predicting"
            :disabled="!predictFile"
          >
            {{ $t("training.startDetect") }}
          </el-button>
        </el-col>

        <el-col :span="14">
          <div v-if="predictResult">
            <img
              :src="`data:image/jpeg;base64,${predictResult.annotated_image}`"
              style="width: 100%; border-radius: 8px; margin-bottom: 12px"
              alt="检测结果"
            />
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item :label="$t('training.objectCount')">
                {{ predictResult.total_objects }}
              </el-descriptions-item>
              <el-descriptions-item :label="$t('training.inferenceTime')">
                {{ predictResult.inference_time }}ms
              </el-descriptions-item>
            </el-descriptions>

            <el-table
              :data="predictResult.detections"
              stripe
              size="small"
              style="margin-top: 8px; max-height: 200px"
            >
              <el-table-column prop="class_name" :label="$t('training.className')" width="120" />
              <el-table-column :label="$t('training.confidence')" width="100">
                <template #default="{ row }">
                  {{ (row.confidence * 100).toFixed(1) }}%
                </template>
              </el-table-column>
              <el-table-column :label="$t('training.position')">
                <template #default="{ row }">
                  [{{ row.bbox.map(v => v.toFixed(0)).join(', ') }}]
                </template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty :description="$t('training.uploadAndDetect')" />
        </el-col>
      </el-row>

      <template #footer>
        <el-button @click="showPredictDialog = false">{{ $t("training.close") }}</el-button>
        <el-button v-if="predictResult" @click="predictResult = null">{{ $t("training.clearResult") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import request from "@/utils/request";
import { Plus, Refresh, UploadFilled } from "@element-plus/icons-vue";
import * as echarts from "echarts";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n({ useScope: "global" });

const taskList = ref([]);
const loadingTasks = ref(false);
const modelList = ref([]);
const loadingModels = ref(false);
const scenes = ref([]);
const selectedTask = ref(null);
const showCreateDialog = ref(false);
const creating = ref(false);

const evalReport = ref(null);
const validating = ref(false);
const exporting = ref(false);

const showPredictDialog = ref(false);
const predicting = ref(false);
const predictFile = ref(null);
const predictFileList = ref([]);
const predictConf = ref(0.25);
const predictIou = ref(0.45);
const predictResult = ref(null);
const predictTaskId = ref(null);

const showResumeDialog = ref(false);
const resuming = ref(false);
const resumeSourceTask = ref(null);
const resumeForm = ref({
  epochs: 200,
  batch_size: 8,
  device: 'cpu',
  lr0: 0.01,
});

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
  device: 'cpu',
  optimizer: 'SGD',
  lr0: 0.01,
});

const metricCards = computed(() => {
  if (!selectedTask.value) return [];
  const m = selectedTask.value.latest_metric;
  if (!m)
    return [
      {
        label: t("training.epoch"),
        value: `${selectedTask.value.current_epoch || 0}/${selectedTask.value.epochs}`,
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

const evalMetricCards = computed(() => {
  if (!evalReport.value) return [];
  const o = evalReport.value.overall;
  if (!o) return [];
  return [
    {
      label: t("training.precision"),
      value: (o.precision * 100).toFixed(1) + '%',
      color: o.precision > 0.7 ? '#67c23a' : '#e6a23c',
    },
    {
      label: t("training.recall"),
      value: (o.recall * 100).toFixed(1) + '%',
      color: o.recall > 0.7 ? '#67c23a' : '#e6a23c',
    },
    {
      label: t("training.map50"),
      value: (o.map50 * 100).toFixed(1) + '%',
      color: o.map50 > 0.5 ? '#67c23a' : '#f56c6c',
    },
    {
      label: t("training.map5095"),
      value: (o.map50_95 * 100).toFixed(1) + '%',
      color: o.map50_95 > 0.3 ? '#67c23a' : '#f56c6c',
    },
  ];
});

const perClassData = computed(() => {
  if (!evalReport.value || !evalReport.value.per_class) return [];
  return Object.entries(evalReport.value.per_class)
    .map(([name, m]) => ({
      class_name: name,
      ap50: m.ap50,
      ap50_95: m.ap50_95,
    }))
    .sort((a, b) => b.ap50 - a.ap50);
});

function statusType(status) {
  const map = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  };
  return map[status] || 'info';
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

function openPredictDialog(task) {
  predictTaskId.value = task.id || task.task?.id;
  predictFile.value = null;
  predictFileList.value = [];
  predictResult.value = null;
  showPredictDialog.value = true;
}

function openResumeDialog(task) {
  resumeSourceTask.value = task;
  resumeForm.value = {
    epochs: (task.epochs || 100) + 100,
    batch_size: task.batch_size || 8,
    device: task.device || 'cpu',
    lr0: task.lr0 || 0.01,
  };
  showResumeDialog.value = true;
}

async function resumeTask() {
  if (!resumeSourceTask.value) return;

  resuming.value = true;
  try {
    const taskId = resumeSourceTask.value.id || resumeSourceTask.value.task?.id;
    if (!taskId) {
      ElMessage.error(t("training.invalidTaskId"));
      return;
    }

    const res = await request.post(`/training/resume/${taskId}`, {
      scene_id: resumeSourceTask.value.scene_id,
      model_name: resumeSourceTask.value.model_name,
      epochs: resumeForm.value.epochs,
      img_size: resumeSourceTask.value.img_size,
      batch_size: resumeForm.value.batch_size,
      device: resumeForm.value.device,
      optimizer: resumeSourceTask.value.optimizer,
      lr0: resumeForm.value.lr0,
    });

    ElMessage.success(res.message || t("training.resumeSuccess"));
    showResumeDialog.value = false;
    await fetchTasks();

    if (res?.id) {
      const newTask = taskList.value.find((t) => t.id === res.id);
      if (newTask) {
        selectTask(newTask);
      }
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t("training.resumeFailed"));
  } finally {
    resuming.value = false;
  }
}

function handlePredictFileChange(file) {
  predictFile.value = file.raw;
  predictFileList.value = [file];
  predictResult.value = null;
}

async function runPredict() {
  if (!predictFile.value || !predictTaskId.value) return;

  predicting.value = true;
  try {
    const formData = new FormData();
    formData.append('file', predictFile.value);
    formData.append('task_id', predictTaskId.value);
    formData.append('conf', predictConf.value);
    formData.append('iou', predictIou.value);

    const res = await request.post('/training/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    predictResult.value = res;
    ElMessage.success(`${t("training.detectComplete")}: ${res.total_objects} ${t("training.objects")}`);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t("training.detectFailed"));
  } finally {
    predicting.value = false;
  }
}

async function fetchTasks() {
  loadingTasks.value = true;
  try {
    const res = await request.get("/training/tasks");
    taskList.value = res.data?.items || [];
  } catch (e) {
    console.error(t("training.fetchError"), e);
  } finally {
    loadingTasks.value = false;
  }
}

async function fetchModels() {
  loadingModels.value = true;
  try {
    const res = await request.get("/training/models");
    modelList.value = res.data?.items || [];
  } catch (e) {
    console.error(t("training.fetchModelsError"), e);
  } finally {
    loadingModels.value = false;
  }
}

async function fetchScenes() {
  try {
    const res = await request.get("/training/scenes");
    scenes.value = res.data?.items || [];
    if (scenes.value.length > 0 && !trainForm.value.scene_id) {
      trainForm.value.scene_id = scenes.value[0].id;
    }
  } catch (e) {
    console.error(t("training.fetchScenesError"), e);
  }
}

function formatFileSize(bytes) {
  if (!bytes) return '-';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function selectTask(task) {
  selectedTask.value = task;
  evalReport.value = null;
  await nextTick();
  initCharts();
  await fetchMetrics();
  startPolling();
}

function initCharts() {
  if (lossChart) {
    lossChart.dispose();
    lossChart = null;
  }
  if (mapChart) {
    mapChart.dispose();
    mapChart = null;
  }

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
    const taskId = selectedTask.value.id || selectedTask.value.task?.id;
    const res = await request.get(`/training/metrics/${taskId}`);
    const metrics = res.data?.metrics || [];

    const statusRes = await request.get(`/training/status/${taskId}`);
    if (statusRes.data) {
      selectedTask.value = {
        ...selectedTask.value,
        ...statusRes.data,
        task: statusRes.data.task || selectedTask.value.task,
        latest_metric: statusRes.data.latest_metric || selectedTask.value.latest_metric,
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
      tooltip: { trigger: 'axis' },
      legend: { data: ['Box Loss', 'Cls Loss', 'DFL Loss'], bottom: 0 },
      grid: { left: '10%', right: '5%', top: '15%', bottom: '18%' },
      xAxis: { type: 'category', data: epochs, name: 'Epoch' },
      yAxis: { type: 'value', name: t("training.loss") },
      series: [
        {
          name: 'Box Loss',
          type: 'line',
          data: metrics.map((m) => m.box_loss),
          smooth: true,
          lineStyle: { width: 2 },
        },
        {
          name: 'Cls Loss',
          type: 'line',
          data: metrics.map((m) => m.cls_loss),
          smooth: true,
          lineStyle: { width: 2 },
        },
        {
          name: 'DFL Loss',
          type: 'line',
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
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['mAP@50', 'mAP@50-95', 'Precision', 'Recall'],
        bottom: 0,
      },
      grid: { left: "10%", right: "5%", top: "15%", bottom: "15%" },
      xAxis: { type: "category", data: epochs, name: "Epoch" },
      yAxis: { type: "value", name: t("training.metricValue"), max: 1 },
      series: [
        {
          name: 'mAP@50',
          type: 'line',
          data: metrics.map((m) => m.map50),
          smooth: true,
          lineStyle: { width: 2, color: '#409eff' },
          itemStyle: { color: '#409eff' },
        },
        {
          name: 'mAP@50-95',
          type: 'line',
          data: metrics.map((m) => m.map50_95),
          smooth: true,
          lineStyle: { width: 2, color: '#67c23a' },
          itemStyle: { color: '#67c23a' },
        },
        {
          name: 'Precision',
          type: 'line',
          data: metrics.map((m) => m.precision),
          smooth: true,
          lineStyle: { width: 2, type: 'dashed', color: '#e6a23c' },
          itemStyle: { color: '#e6a23c' },
        },
        {
          name: 'Recall',
          type: 'line',
          data: metrics.map((m) => m.recall),
          smooth: true,
          lineStyle: { width: 2, type: 'dashed', color: '#f56c6c' },
          itemStyle: { color: '#f56c6c' },
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
    ElMessage.success(`${t("training.createSuccess")} ${res.data?.task_uuid}`);
    showCreateDialog.value = false;
    await fetchTasks();
    await fetchModels();
    if (res.data?.id) {
      const newTask = taskList.value.find((t) => t.id === res.data.id);
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

async function validateModel(task) {
  if (!task) return;
  const taskId = task.id || task.task?.id;
  if (!taskId) {
    ElMessage.error(t("training.invalidTaskId"));
    return;
  }

  validating.value = true;
  try {
    const res = await request.post(`/training/validate/${taskId}`, {
      split: 'val',
      conf: 0.001,
      iou: 0.6,
    });
    evalReport.value = res.data;
    ElMessage.success(`${t("training.evalComplete")} mAP@50=${((res.data?.overall?.map50 || 0) * 100).toFixed(1)}%`);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t("training.evalFailed"));
  } finally {
    validating.value = false;
  }
}

async function exportModel(task) {
  if (!task) return;
  const taskId = task.id || task.task?.id;
  if (!taskId) {
    ElMessage.error(t("training.invalidTaskId"));
    return;
  }

  exporting.value = true;
  try {
    const res = await request.post(`/training/export/${taskId}`, {
      version: '',
      description: `${t("training.exportFrom")} ${task.task_uuid}`,
      set_default: true,
      upload_minio: false,
    });
    ElMessage.success(res.message || t("training.exportSuccess"));
    await fetchModels();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t("training.exportFailed"));
  } finally {
    exporting.value = false;
  }
}

async function downloadModel(task) {
  if (!task) return;
  const taskId = task.id || task.task?.id;
  if (!taskId) {
    ElMessage.error(t("training.invalidTaskId"));
    return;
  }

  try {
    const response = await request.get(`/training/download/${taskId}`, {
      responseType: "blob",
    });
    const blob = new Blob([response]);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `best_${task.task_uuid}.pt`;
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
  fetchScenes();
  fetchTasks();
  fetchModels();
});

onBeforeUnmount(() => {
  stopPolling();
  if (lossChart) {
    lossChart.dispose();
    lossChart = null;
  }
  if (mapChart) {
    mapChart.dispose();
    mapChart = null;
  }
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
  width: 100%;
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
.model-list-card,
.monitor-card,
.eval-card {
  margin-bottom: 20px;
}

.predict-upload {
  width: 100%;
}

.predict-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 20px;
}

:deep(.weak-row) {
  background-color: #fef0f0 !important;
}
:deep(.weak-row td) {
  color: #f56c6c !important;
}
</style>
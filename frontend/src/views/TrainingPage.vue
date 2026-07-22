<template>
  <div class="training-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>{{ $t('training.title') }}</h2>
      <div>
        <el-button type="primary" @click="fetchTasks">
          <el-icon><Refresh /></el-icon>
          {{ $t('training.refresh') }}
        </el-button>
        <el-button type="success" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          {{ $t('training.createTask') }}
        </el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="12">
        <!-- 训练任务列表 -->
        <el-card class="task-list-card" shadow="never">
          <template #header>
            <span>{{ $t('training.taskList') }}</span>
          </template>
          <el-table
            :data="taskList"
            v-loading="loadingTasks"
            style="width: 100%"
            stripe
          >
            <el-table-column prop="id" :label="$t('training.colId')" width="60" />
            <el-table-column prop="model_name" :label="$t('training.colModel')" width="110" />
            <el-table-column prop="device" :label="$t('training.colDevice')" width="80" />
            <el-table-column :label="$t('training.colProgress')" width="180">
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
            <el-table-column :label="$t('training.colEpoch')" width="100">
              <template #default="{ row }">
                {{ row.current_epoch || 0 }}/{{ row.epochs }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('training.colStatus')" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">
                  {{ statusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="$t('training.colCreatedAt')" width="170" />
            <el-table-column :label="$t('training.colAction')" width="420" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" text @click="selectTask(row)">
                  {{ $t('training.btnMonitor') }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  type="success"
                  text
                  @click="validateModel(row)"
                  :loading="validating && selectedTask?.id === row.id"
                >
                  {{ $t('training.btnEvaluate') }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  type="warning"
                  text
                  @click="exportModel(row)"
                  :loading="exporting && selectedTask?.id === row.id"
                >
                  {{ $t('training.btnExport') }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  type="info"
                  text
                  @click="openPredictDialog(row)"
                >
                  {{ $t('training.btnValidate') }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  type="primary"
                  text
                  @click="openResumeDialog(row)"
                >
                  {{ $t('training.btnResume') }}
                </el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  size="small"
                  text
                  @click="downloadModel(row)"
                >
                  {{ $t('training.btnDownload') }}
                </el-button>
                <el-button
                  v-if="row.status === 'running'"
                  size="small"
                  type="danger"
                  text
                  @click="stopTask(row.id)"
                >
                  {{ $t('training.btnStop') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="model-list-card" shadow="never">
          <template #header>
            <span>{{ $t('training.modelList') }}</span>
            <el-button type="primary" size="small" @click="fetchModels">
              <el-icon><Refresh /></el-icon>
              {{ $t('training.refresh') }}
            </el-button>
          </template>
          <el-table
            :data="modelList"
            v-loading="loadingModels"
            style="width: 100%"
            stripe
          >
            <el-table-column prop="id" :label="$t('training.colId')" width="60" />
            <el-table-column prop="model_name" :label="$t('training.colModelName')" width="150" />
            <el-table-column prop="version" :label="$t('training.colVersion')" width="100" />
            <el-table-column prop="model_type" :label="$t('training.colType')" width="100" />
            <el-table-column prop="map50" label="mAP@50" width="100">
              <template #default="{ row }">
                {{ row.map50 !== null ? (row.map50 * 100).toFixed(1) + '%' : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="file_size" :label="$t('training.colSize')" width="100">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column :label="$t('training.colStatus')" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_default ? 'success' : 'info'" size="small">
                  {{ row.is_default ? $t('training.modelDefault') : $t('training.modelActive') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="$t('training.colCreatedAt')" width="170" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 训练监控面板 -->
    <el-card v-if="selectedTask" class="monitor-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>
            {{ $t('training.monitorTitle') }} - {{ $t('training.monitorTask') }} {{ selectedTask.task_uuid }}
            <el-tag
              :type="statusType(selectedTask.status)"
              size="small"
              style="margin-left: 8px"
            >
              {{ statusText(selectedTask.status) }}
            </el-tag>
          </span>
          <div class="monitor-info">
            <span>{{ $t('training.monitorModel') }}: {{ selectedTask.model_name }}</span>
            <span>{{ $t('training.monitorDevice') }}: {{ selectedTask.device }}</span>
            <span>Epoch: {{ selectedTask.current_epoch || 0 }}</span>
          </div>
        </div>
      </template>

      <!-- 最新指标卡片 -->
      <el-row :gutter="16" class="metric-cards">
        <el-col :span="4" v-for="item in metricCards" :key="item.label">
          <el-card shadow="hover" class="metric-item">
            <div class="metric-value">{{ item.value }}</div>
            <div class="metric-label">{{ item.label }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 训练曲线图表 -->
      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <div ref="lossChartRef" style="height: 350px"></div>
        </el-col>
        <el-col :span="12">
          <div ref="mapChartRef" style="height: 350px"></div>
        </el-col>
      </el-row>
    </el-card>

    <!-- ========== 新增：评估报告面板 ========== -->
    <el-card v-if="evalReport" class="eval-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>
            {{ $t('training.evalReport') }}
            <el-tag size="small" style="margin-left: 8px">
              {{ evalReport.split === 'val' ? $t('training.evalValSet') : $t('training.evalTestSet') }}
            </el-tag>
            <el-tag
              size="small"
              style="margin-left: 8px"
              :type="evalReport.overall?.map50 > 0.5 ? 'success' : 'warning'"
            >
              mAP@50: {{ ((evalReport.overall?.map50 || 0) * 100).toFixed(1) }}%
            </el-tag>
          </span>
          <el-button size="small" @click="evalReport = null">{{ $t('training.evalClose') }}</el-button>
        </div>
      </template>

      <!-- 整体指标卡片 -->
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

      <!-- 每类 AP 表格 -->
      <el-table
        :data="perClassData"
        stripe
        style="width: 100%; margin-top: 16px"
        max-height="300"
      >
        <el-table-column prop="class_name" :label="$t('training.colClass')" width="200" />
        <el-table-column prop="ap50" label="AP@50" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.ap50 < 0.5 ? '#f56c6c' : '#67c23a' }">
              {{ (row.ap50 * 100).toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="ap50_95" label="AP@50-95" width="120">
          <template #default="{ row }">
            {{ (row.ap50_95 * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column :label="$t('training.evalRating')">
          <template #default="{ row }">
            <el-tag
              :type="row.ap50 >= 0.7 ? 'success' : row.ap50 >= 0.5 ? 'warning' : 'danger'"
              size="small"
            >
              {{ row.ap50 >= 0.7 ? $t('training.evalExcellent') : row.ap50 >= 0.5 ? $t('training.evalGood') : $t('training.evalImprove') }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建训练任务对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="$t('training.createDialogTitle')"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="trainForm" label-width="120px">
        <el-form-item :label="$t('training.labelScene')">
          <el-select v-model="trainForm.scene_id" :placeholder="$t('training.selectScene')">
            <el-option
              v-for="scene in sceneList"
              :key="scene.id"
              :label="scene.display_name"
              :value="scene.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('training.labelBaseModel')">
          <el-select v-model="trainForm.model_name">
            <el-option :label="$t('training.modelNano')" value="yolov11n" />
            <el-option :label="$t('training.modelSmall')" value="yolov11s" />
            <el-option :label="$t('training.modelMedium')" value="yolov11m" />
            <el-option :label="$t('training.modelLarge')" value="yolov11l" />
            <el-option :label="$t('training.modelXlarge')" value="yolov11x" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('training.labelEpochs')">
          <el-slider
            v-model="trainForm.epochs"
            :min="10"
            :max="500"
            :step="10"
            show-input
          />
        </el-form-item>

        <el-form-item :label="$t('training.labelBatchSize')">
          <el-input-number
            v-model="trainForm.batch_size"
            :min="1"
            :max="64"
            :step="2"
          />
        </el-form-item>

        <el-form-item :label="$t('training.labelImgSize')">
          <el-select v-model="trainForm.img_size">
            <el-option :label="$t('training.imgSize416')" :value="416" />
            <el-option :label="$t('training.imgSize512')" :value="512" />
            <el-option :label="$t('training.imgSizeDefault')" :value="640" />
            <el-option :label="$t('training.imgSize768')" :value="768" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('training.labelDevice')">
          <el-radio-group v-model="trainForm.device">
            <el-radio value="cpu">{{ $t('training.deviceCpu') }}</el-radio>
            <el-radio value="0">GPU: 0</el-radio>
            <el-radio value="1">GPU: 1</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="$t('training.labelOptimizer')">
          <el-select v-model="trainForm.optimizer">
            <el-option :label="$t('training.optimizerSgd')" value="SGD" />
            <el-option label="Adam" value="Adam" />
            <el-option label="AdamW" value="AdamW" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('training.labelLr')">
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
        <el-button @click="showCreateDialog = false">{{ $t('training.cancel') }}</el-button>
        <el-button type="primary" @click="createTask" :loading="creating">
          {{ $t('training.startTraining') }}
        </el-button>
      </template>
    </el-dialog>
    <!-- 续训对话框 -->
    <el-dialog
      v-model="showResumeDialog"
      :title="$t('training.resumeDialogTitle')"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="resumeForm" label-width="120px">
        <el-form-item :label="$t('training.labelSourceTask')">
          <el-card shadow="never" class="source-task-info">
            <div>{{ $t('training.sourceTaskId') }}: {{ resumeSourceTask?.id }}</div>
            <div>{{ $t('training.sourceTaskModel') }}: {{ resumeSourceTask?.model_name }}</div>
            <div>{{ $t('training.sourceTaskDone') }}: {{ resumeSourceTask?.current_epoch || 0 }}/{{ resumeSourceTask?.epochs || 0 }} {{ $t('training.sourceTaskRounds') }}</div>
          </el-card>
        </el-form-item>

        <el-form-item :label="$t('training.labelNewEpochs')">
          <el-slider
            v-model="resumeForm.epochs"
            :min="(resumeSourceTask?.epochs || 100) + 10"
            :max="500"
            :step="10"
            show-input
          />
          <div style="color: #909399; font-size: 12px; margin-top: 4px">
            {{ $t('training.resumeHint', { total: resumeForm.epochs, extra: resumeForm.epochs - (resumeSourceTask?.current_epoch || 0) }) }}
          </div>
        </el-form-item>

        <el-form-item :label="$t('training.labelDevice')">
          <el-radio-group v-model="resumeForm.device">
            <el-radio value="cpu">{{ $t('training.deviceCpu') }}</el-radio>
            <el-radio value="0">GPU: 0</el-radio>
            <el-radio value="1">GPU: 1</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="$t('training.labelBatchSize')">
          <el-input-number
            v-model="resumeForm.batch_size"
            :min="1"
            :max="64"
            :step="2"
          />
        </el-form-item>

        <el-form-item :label="$t('training.labelLr')">
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
        <el-button @click="showResumeDialog = false">{{ $t('training.cancel') }}</el-button>
        <el-button type="primary" @click="resumeTask" :loading="resuming">
          {{ $t('training.startResume') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试图验证对话框 -->
    <el-dialog v-model="showPredictDialog" :title="$t('training.predictDialogTitle')" width="900px" :close-on-click-modal="false">
      <el-row :gutter="16">
        <!-- 左侧：上传 + 配置 -->
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
            <div>{{ $t('training.uploadHint') }} <em>{{ $t('training.uploadClick') }}</em></div>
            <template #tip>
              <div class="el-upload__tip">{{ $t('training.uploadTip') }}</div>
            </template>
          </el-upload>

          <el-form label-width="80px" style="margin-top: 16px">
            <el-form-item :label="$t('camera.confidence')">
              <el-slider v-model="predictConf" :min="0.05" :max="0.95" :step="0.05" show-input />
            </el-form-item>
            <el-form-item :label="$t('training.labelIou')">
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
            {{ $t('training.startDetection') }}
          </el-button>
        </el-col>

        <!-- 右侧：检测结果 -->
        <el-col :span="14">
          <div v-if="predictResult">
            <img
              :src="`data:image/jpeg;base64,${predictResult.annotated_image}`"
              style="width: 100%; border-radius: 8px; margin-bottom: 12px"
              :alt="$t('training.predictAlt')"
            />
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item :label="$t('training.detectedObjects')">
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
              <el-table-column prop="class_name" :label="$t('training.colClass')" width="120" />
              <el-table-column :label="$t('training.colConfidence')" width="100">
                <template #default="{ row }">
                  {{ (row.confidence * 100).toFixed(1) }}%
                </template>
              </el-table-column>
              <el-table-column :label="$t('training.colPosition')">
                <template #default="{ row }">
                  [{{ row.bbox.map(v => v.toFixed(0)).join(', ') }}]
                </template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else :description="$t('training.predictUploadImage')" />
        </el-col>
      </el-row>

      <template #footer>
        <el-button @click="showPredictDialog = false">{{ $t('training.evalClose') }}</el-button>
        <el-button v-if="predictResult" @click="predictResult = null">{{ $t('training.predictClear') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import request from '@/utils/request'
import { Plus, Refresh, UploadFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// ========== 状态变量 ==========
const taskList = ref([])
const loadingTasks = ref(false)
const modelList = ref([])
const loadingModels = ref(false)
const sceneList = ref([])
const selectedTask = ref(null)
const showCreateDialog = ref(false)
const creating = ref(false)

// ========== 评估相关状态 ==========
const evalReport = ref(null)
const validating = ref(false)

// ========== 导出相关状态 ==========
const exporting = ref(false)

// ========== 测试验证相关状态 ==========
const showPredictDialog = ref(false)
const predicting = ref(false)
const predictFile = ref(null)
const predictFileList = ref([])
const predictConf = ref(0.25)
const predictIou = ref(0.45)
const predictResult = ref(null)
const predictTaskId = ref(null)

// ========== 续训相关状态 ==========
const showResumeDialog = ref(false)
const resuming = ref(false)
const resumeSourceTask = ref(null)
const resumeForm = ref({
  epochs: 200,
  batch_size: 8,
  device: 'cpu',
  lr0: 0.01,
})

// 图表引用
const lossChartRef = ref(null)
const mapChartRef = ref(null)
let lossChart = null
let mapChart = null

// 轮询定时器
let pollTimer = null

// ========== 训练表单 ==========
const trainForm = ref({
  scene_id: null,
  model_name: 'yolov11n',
  epochs: 50,
  batch_size: 8,
  img_size: 640,
  device: 'cpu',
  optimizer: 'SGD',
  lr0: 0.01,
})

// ========== 计算属性: 最新指标卡片 ==========
const metricCards = computed(() => {
  if (!selectedTask.value) return []

  const m = selectedTask.value.latest_metric
  if (!m) {
    return [
      { label: 'Epoch', value: '-' },
      { label: 'Box Loss', value: '-' },
      { label: 'Cls Loss', value: '-' },
      { label: 'mAP@50', value: '-' },
      { label: 'mAP@50-95', value: '-' },
    ]
  }

  const totalEpochs = selectedTask.value.task?.epochs || 100
  return [
    { label: 'Epoch', value: `${m.epoch}/${totalEpochs}` },
    { label: 'Box Loss', value: m.box_loss !== null ? m.box_loss.toFixed(4) : '-' },
    { label: 'Cls Loss', value: m.cls_loss !== null ? m.cls_loss.toFixed(4) : '-' },
    {
      label: 'mAP@50',
      value: m.map50 !== null ? (m.map50 * 100).toFixed(1) + '%' : '-',
    },
    {
      label: 'mAP@50-95',
      value: m.map50_95 !== null ? (m.map50_95 * 100).toFixed(1) + '%' : '-',
    },
  ]
})

// ========== 计算属性: 评估指标卡片 ==========
const evalMetricCards = computed(() => {
  if (!evalReport.value) return []
  const o = evalReport.value.overall
  if (!o) return []
  return [
    {
      label: 'Precision',
      value: (o.precision * 100).toFixed(1) + '%',
      color: o.precision > 0.7 ? '#67c23a' : '#e6a23c',
    },
    {
      label: 'Recall',
      value: (o.recall * 100).toFixed(1) + '%',
      color: o.recall > 0.7 ? '#67c23a' : '#e6a23c',
    },
    {
      label: 'mAP@50',
      value: (o.map50 * 100).toFixed(1) + '%',
      color: o.map50 > 0.5 ? '#67c23a' : '#f56c6c',
    },
    {
      label: 'mAP@50-95',
      value: (o.map50_95 * 100).toFixed(1) + '%',
      color: o.map50_95 > 0.3 ? '#67c23a' : '#f56c6c',
    },
  ]
})

// ========== 计算属性: 每类 AP 表格数据 ==========
const perClassData = computed(() => {
  if (!evalReport.value || !evalReport.value.per_class) return []
  return Object.entries(evalReport.value.per_class)
    .map(([name, m]) => ({
      class_name: name,
      ap50: m.ap50,
      ap50_95: m.ap50_95,
    }))
    .sort((a, b) => b.ap50 - a.ap50)
})

// ========== 状态映射 ==========
function statusType(status) {
  const map = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

function statusText(status) {
  const map = {
    pending: t('training.statusPending'),
    running: t('training.statusRunning'),
    completed: t('training.statusCompleted'),
    failed: t('training.statusFailed'),
    cancelled: t('training.statusCancelled'),
  }
  return map[status] || status
}

// ========== 打开测试验证对话框 ==========
function openPredictDialog(task) {
  predictTaskId.value = task.id || task.task?.id
  predictFile.value = null
  predictFileList.value = []
  predictResult.value = null
  showPredictDialog.value = true
}

// ========== 打开续训对话框 ==========
function openResumeDialog(task) {
  resumeSourceTask.value = task
  resumeForm.value = {
    epochs: (task.epochs || 100) + 100,
    batch_size: task.batch_size || 8,
    device: task.device || 'cpu',
    lr0: task.lr0 || 0.01,
  }
  showResumeDialog.value = true
}

// ========== 执行续训 ==========
async function resumeTask() {
  if (!resumeSourceTask.value) return

  resuming.value = true
  try {
    const taskId = resumeSourceTask.value.id || resumeSourceTask.value.task?.id
    if (!taskId) {
      ElMessage.error(t('training.msgInvalidId'))
      return
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
    })

    ElMessage.success(res.message || t('training.msgResumeDone'))
    showResumeDialog.value = false
    await fetchTasks()

    if (res?.id) {
      const newTask = taskList.value.find((t) => t.id === res.id)
      if (newTask) {
        selectTask(newTask)
      }
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('training.msgResumeFail'))
  } finally {
    resuming.value = false
  }
}

// ========== 文件选择处理 ==========
function handlePredictFileChange(file) {
  predictFile.value = file.raw
  predictFileList.value = [file]
  predictResult.value = null
}

// ========== 运行预测 ==========
async function runPredict() {
  if (!predictFile.value || !predictTaskId.value) return

  predicting.value = true
  try {
    const formData = new FormData()
    formData.append('file', predictFile.value)
    formData.append('task_id', predictTaskId.value)
    formData.append('conf', predictConf.value)
    formData.append('iou', predictIou.value)

    const res = await request.post('/training/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    predictResult.value = res
    ElMessage.success(`${t('training.msgDetectDone')}: ${t('training.detectedObjects')} ${res.total_objects}`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('training.msgDetectFail'))
  } finally {
    predicting.value = false
  }
}

// ========== 获取任务列表 ==========
async function fetchTasks() {
  loadingTasks.value = true
  try {
    const res = await request.get('/training/tasks')
    taskList.value = res?.items || []
  } catch (e) {
    console.error('获取任务列表失败', e)
  } finally {
    loadingTasks.value = false
  }
}

// ========== 获取模型版本列表 ==========
async function fetchModels() {
  loadingModels.value = true
  try {
    const res = await request.get('/training/models')
    modelList.value = res?.items || []
  } catch (e) {
    console.error('获取模型列表失败', e)
  } finally {
    loadingModels.value = false
  }
}

// ========== 获取场景列表 ==========
async function fetchScenes() {
  try {
    const res = await request.get('/training/scenes')
    sceneList.value = res?.items || []
    if (sceneList.value.length > 0 && !trainForm.value.scene_id) {
      trainForm.value.scene_id = sceneList.value[0].id
    }
  } catch (e) {
    console.error('获取场景列表失败', e)
  }
}

// ========== 格式化文件大小 ==========
function formatFileSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// ========== 选择任务并开始监控 ==========
async function selectTask(task) {
  selectedTask.value = task
  // 关闭旧的评估报告
  evalReport.value = null
  await nextTick()
  initCharts()
  await fetchMetrics()
  startPolling()
}

// ========== 初始化 ECharts 图表 ==========
function initCharts() {
  if (lossChart) {
    lossChart.dispose()
    lossChart = null
  }
  if (mapChart) {
    mapChart.dispose()
    mapChart = null
  }

  if (lossChartRef.value) {
    lossChart = echarts.init(lossChartRef.value)
  }
  if (mapChartRef.value) {
    mapChart = echarts.init(mapChartRef.value)
  }
}

// ========== 获取训练指标并更新图表 ==========
async function fetchMetrics() {
  if (!selectedTask.value) return

  try {
    const taskId = selectedTask.value.id || selectedTask.value.task?.id
    if (!taskId) return

    // 获取最新状态
    const statusRes = await request.get(`/training/status/${taskId}`)
    if (statusRes) {
      selectedTask.value = {
        ...selectedTask.value,
        ...statusRes,
        task: statusRes.task || selectedTask.value.task,
        latest_metric: statusRes.latest_metric || selectedTask.value.latest_metric,
      }

      // 任务已结束，停止指标轮询（任务列表继续刷新）
      const status = statusRes.task?.status || selectedTask.value.status
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        if (pollTimer) {
          clearInterval(pollTimer)
          pollTimer = null
        }
      }
    }

    // 获取所有指标
    const metricsRes = await request.get(`/training/metrics/${taskId}`)
    const metrics = metricsRes?.metrics || []

    if (metrics.length > 0) {
      updateCharts(metrics)
    }
  } catch (e) {
    console.error('获取训练指标失败', e)
  }
}

// ========== 更新图表 ==========
function updateCharts(metrics) {
  const epochs = metrics.map((m) => m.epoch)

  if (lossChart) {
    lossChart.setOption({
      title: {
        text: t('training.chartLoss'),
        left: 'center',
        textStyle: { fontSize: 14 },
      },
      tooltip: { trigger: 'axis' },
      legend: { data: ['Box Loss', 'Cls Loss', 'DFL Loss'], bottom: 0 },
      grid: { left: '10%', right: '5%', top: '15%', bottom: '18%' },
      xAxis: { type: 'category', data: epochs, name: 'Epoch' },
      yAxis: { type: 'value', name: 'Loss' },
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
    })
  }

  if (mapChart) {
    mapChart.setOption({
      title: {
        text: t('training.chartMetric'),
        left: 'center',
        textStyle: { fontSize: 14 },
      },
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['mAP@50', 'mAP@50-95', 'Precision', 'Recall'],
        bottom: 0,
      },
      grid: { left: '10%', right: '5%', top: '15%', bottom: '18%' },
      xAxis: { type: 'category', data: epochs, name: 'Epoch' },
      yAxis: { type: 'value', name: t('training.yAxisMetric'), max: 1 },
      series: [
        {
          name: 'mAP@50',
          type: 'line',
          data: metrics.map((m) => m.map50),
          smooth: true,
          lineStyle: { width: 2, color: '#1e1e1e' },
          itemStyle: { color: '#1e1e1e' },
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
    })
  }
}

// ========== 轮询监控 ==========
let taskListTimer = null

function startPolling() {
  stopPolling()
  // 每 3 秒刷新选中任务的指标和状态
  pollTimer = setInterval(() => {
    if (selectedTask.value) {
      fetchMetrics()
    }
  }, 3000)
  // 每 5 秒刷新任务列表（更新进度条）
  taskListTimer = setInterval(() => {
    fetchTasks()
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (taskListTimer) {
    clearInterval(taskListTimer)
    taskListTimer = null
  }
}

// ========== 创建训练任务 ==========
async function createTask() {
  creating.value = true
  try {
    const res = await request.post('/training/start', trainForm.value)
    ElMessage.success(`${t('training.msgTaskCreated')}: ${res?.task_uuid || ''}`)
    showCreateDialog.value = false
    await fetchTasks()
    await fetchModels()

    if (res?.id) {
      const newTask = taskList.value.find((t) => t.id === res.id)
      if (newTask) {
        selectTask(newTask)
      }
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('training.msgCreateFail'))
  } finally {
    creating.value = false
  }
}

// ========== 停止训练任务 ==========
async function stopTask(taskId) {
  try {
    await ElMessageBox.confirm(t('training.msgStopConfirm'), t('training.msgStopTitle'), {
      type: 'warning',
    })
    await request.post(`/training/stop/${taskId}`)
    ElMessage.success(t('training.msgStopped'))
    await fetchTasks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(t('training.msgStopFail'))
    }
  }
}

// ========== 评估模型 ==========
async function validateModel(task) {
  if (!task) return
  const taskId = task.id || task.task?.id
  if (!taskId) {
    ElMessage.error(t('training.msgInvalidId'))
    return
  }

  validating.value = true
  try {
    const res = await request.post(`/training/validate/${taskId}`, {
      split: 'val',
      conf: 0.001,
      iou: 0.6,
    })
    evalReport.value = res
    ElMessage.success(`${t('training.msgEvalDone')}: mAP@50=${((res.overall?.map50 || 0) * 100).toFixed(1)}%`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('training.msgEvalFail'))
  } finally {
    validating.value = false
  }
}

// ========== 导出模型 ==========
async function exportModel(task) {
  if (!task) return
  const taskId = task.id || task.task?.id
  if (!taskId) {
    ElMessage.error(t('training.msgInvalidId'))
    return
  }

  exporting.value = true
  try {
    const res = await request.post(`/training/export/${taskId}`, {
      version: '',
      description: `从任务 ${task.task_uuid} 导出`,
      set_default: true,
      upload_minio: false,
    })
    ElMessage.success(res.message || t('training.msgExportDone'))
    // 刷新模型列表
    await fetchModels()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('training.msgExportFail'))
  } finally {
    exporting.value = false
  }
}

// ========== 下载模型 ==========
async function downloadModel(task) {
  if (!task) return
  const taskId = task.id || task.task?.id
  if (!taskId) {
    ElMessage.error(t('training.msgInvalidId'))
    return
  }

  try {
    const token = localStorage.getItem('rsod_token') || ''
    const response = await fetch(
      `/api/training/download/${taskId}`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    if (!response.ok) throw new Error('下载失败')
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `best_${task.task_uuid}.pt`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success(t('training.msgDownloadStart'))
  } catch (e) {
    ElMessage.error(t('training.msgDownloadFail'))
  }
}

// ========== 生命周期 ==========
onMounted(async () => {
  await fetchScenes()
  await fetchTasks()
  await fetchModels()

  // 自动选中正在运行的任务
  const runningTask = taskList.value.find(t => t.status === 'running' || t.status === 'pending')
  if (runningTask) {
    selectTask(runningTask)
  } else {
    // 没有运行中的任务，也启动任务列表定时刷新
    startTaskListPolling()
  }
})

function startTaskListPolling() {
  if (taskListTimer) return
  taskListTimer = setInterval(() => {
    fetchTasks()
  }, 5000)
}

onBeforeUnmount(() => {
  stopPolling()
  if (lossChart) {
    lossChart.dispose()
    lossChart = null
  }
  if (mapChart) {
    mapChart.dispose()
    mapChart = null
  }
})
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
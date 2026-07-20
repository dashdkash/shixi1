<template>
  <div class="page-container">

    <PageHeader
      title="智能检测"
      subtitle="上传图片、视频或开启摄像头进行杂草检测。"
    />

    <el-tabs
      v-model="activeTab"
      class="detection-tabs"
    >

      <!-- ========================================= -->
      <!-- Upload Detection -->
      <!-- ========================================= -->

      <el-tab-pane
        label="图片 / 视频检测"
        name="upload"
      >

        <SectionCard>

          <!-- Upload -->

          <el-upload
            v-if="!result && !uploading"
            class="upload-area"
            drag
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileChange"
            accept="image/*,video/mp4,video/avi,video/quicktime,video/x-msvideo"
          >

            <el-icon class="upload-icon">
              <UploadFilled />
            </el-icon>

            <div class="upload-text">
              上传图片或视频进行检测
            </div>

            <div class="upload-hint">
              支持 JPG、PNG、BMP、WebP、MP4、AVI、MOV
            </div>

          </el-upload>

          <!-- Loading -->

          <div
            v-else-if="uploading"
            class="loading-area"
          >

            <el-icon
              class="is-loading"
              :size="40"
            >
              <Loading />
            </el-icon>

            <p>正在检测中，请稍候...</p>

          </div>

          <!-- Result -->

          <template v-else>

            <div class="result-toolbar">

              <el-button @click="resetUpload">
                重新检测
              </el-button>

            </div>

            <video
              v-if="isVideoResult && annotatedVideoSrc"
              :src="annotatedVideoSrc"
              controls
              class="result-video"
            />

            <img
              v-else-if="annotatedImageSrc"
              :src="annotatedImageSrc"
              class="result-image"
            />

            <DetectionResultCard
              :result="result"
              :loading="false"
            />

          </template>

        </SectionCard>

      </el-tab-pane>

      <!-- ========================================= -->
      <!-- Camera -->
      <!-- ========================================= -->

      <el-tab-pane
        label="摄像头实时检测"
        name="camera"
      >

        <div class="camera-layout">

          <!-- Left -->

          <SectionCard>

            <template #header>
              实时画面
            </template>

            <template #extra>

              <el-tag
                :type="statusTagType"
              >
                {{ statusText }}
              </el-tag>

            </template>

            <div class="video-wrapper">

              <video
                ref="videoRef"
                autoplay
                muted
                playsinline
                style="display:none"
              />

              <canvas
                ref="canvasRef"
                class="preview-canvas"
                :width="canvasWidth"
                :height="canvasHeight"
              />

              <EmptyState
                v-if="!isRunning"
                title="摄像头未启动"
                description="点击下方按钮开始实时检测。"
              />

            </div>

            <div
              v-if="isRunning"
              class="video-stats"
            >

              <el-tag type="success">
                FPS {{ currentFps }}
              </el-tag>

              <el-tag>
                帧 {{ frameCount }}
              </el-tag>

              <el-tag>
                {{ inferenceTime }} ms
              </el-tag>

            </div>

          </SectionCard>

          <!-- Right -->

          <div class="camera-side">

            <div class="stats-grid">

              <StatsCard
                title="目标数"
                :value="objectCount"
                :icon="Aim"
              />

              <StatsCard
                title="FPS"
                :value="currentFps"
                :icon="VideoCamera"
              />

              <StatsCard
                title="推理耗时"
                :value="inferenceTime"
                unit="ms"
                :icon="Timer"
                :inverse="true"
              />

              <StatsCard
                title="处理帧"
                :value="frameCount"
                :icon="DataLine"
              />

            </div>

            <SectionCard title="检测目标">

              <template #extra>

                <el-tag>
                  {{ currentDetections.length }}
                </el-tag>

              </template>

              <EmptyState
                v-if="currentDetections.length === 0"
                title="暂无检测目标"
              />

              <div
                v-else
                class="detection-list"
              >

                <div
                  v-for="(det,index) in currentDetections"
                  :key="index"
                  class="detection-item"
                >

                  <div class="det-info">

                    <span class="det-class">
                      {{ det.class_name }}
                    </span>

                    <el-progress
                      :percentage="Math.round(det.confidence*100)"
                      :stroke-width="6"
                    />

                  </div>

                  <div class="det-bbox">

                    {{ det.bbox.map(v=>Math.round(v)).join(", ") }}

                  </div>

                </div>

              </div>

            </SectionCard>

            <SectionCard
              v-if="Object.keys(classDistribution).length"
              title="类别分布"
            >

              <div class="distribution-list">

                <div
                  v-for="(count,name) in classDistribution"
                  :key="name"
                  class="distribution-item"
                >

                  <span>{{ name }}</span>

                  <el-tag
                    size="small"
                    type="success"
                  >
                    {{ count }}
                  </el-tag>

                </div>

              </div>

            </SectionCard>

          </div>

        </div>

        <div class="control-bar">

          <el-button
            v-if="!isRunning"
            type="primary"
            :loading="isConnecting"
            @click="startCamera"
          >
            开启摄像头
          </el-button>

          <el-button
            v-else
            type="danger"
            @click="stopCamera"
          >
            停止检测
          </el-button>

          <el-divider direction="vertical"/>

          <span>推理模式</span>

          <el-radio-group
            v-model="detectMode"
            :disabled="isRunning"
          >

            <el-radio-button label="cpu">
              CPU
            </el-radio-button>

            <el-radio-button label="gpu">
              GPU
            </el-radio-button>

          </el-radio-group>

          <el-divider direction="vertical"/>

          <span>置信度</span>

          <el-slider
            v-model="confThreshold"
            :min="0.1"
            :max="0.9"
            :step="0.05"
            :disabled="isRunning"
            show-input
            style="width:180px"
          />

        </div>

      </el-tab-pane>

    </el-tabs>

  </div>
</template>

<script setup>
/**
 * DetectionPage.vue — 检测工作台
 *
 * Tab 1：图片/视频上传检测（单图、批量、视频）
 * Tab 2：摄像头实时检测
 */
import { detectSingle, detectVideo } from "@/api/detection";

import DetectionResultCard from "@/components/DetectionResultCard.vue";

import EmptyState from "@/components/common/EmptyState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import SectionCard from "@/components/common/SectionCard.vue";
import StatsCard from "@/components/common/StatsCard.vue";

import { createCameraWs } from "@/utils/cameraWs";

import {
  Aim,
  DataLine,
  Loading,
  Timer,
  UploadFilled,
  VideoCamera,
} from "@element-plus/icons-vue";

import { ElMessage } from "element-plus";

import {
  computed,
  onBeforeUnmount,
  ref,
} from "vue";

// ════════════════════════════════════════════════════════════
// Tab 切换
// ════════════════════════════════════════════════════════════
const activeTab = ref("upload");

// ════════════════════════════════════════════════════════════
// Tab 1：上传检测
// ════════════════════════════════════════════════════════════
const uploading = ref(false);
const result = ref(null);
const annotatedImageSrc = ref("");
const annotatedVideoSrc = ref("");
const isVideoResult = ref(false);

function isVideoFile(file) {
  return file.name.match(/\.(mp4|avi|mov|mkv|wmv|flv)$/i);
}

async function handleFileChange(file) {
  const raw = file.raw;
  if (!raw) return;

  // 文件大小限制 50MB
  if (raw.size > 50 * 1024 * 1024) {
    ElMessage.error("文件大小不能超过 50MB");
    return;
  }

  uploading.value = true;
  result.value = null;
  annotatedImageSrc.value = "";
  annotatedVideoSrc.value = "";

  try {
    if (isVideoFile(file)) {
      // 视频检测
      isVideoResult.value = true;
      const formData = new FormData();
      formData.append("file", raw);
      formData.append("conf", 0.25);

      const res = await detectVideo(formData);
      result.value = res;
      if (res.annotated_video_url) {
        annotatedVideoSrc.value = res.annotated_video_url;
      }
    } else {
      // 图片检测
      isVideoResult.value = false;
      const formData = new FormData();
      formData.append("file", raw);
      formData.append("conf", 0.25);

      const res = await detectSingle(formData);
      result.value = res;
      if (res.annotated_image_url) {
        annotatedImageSrc.value = res.annotated_image_url;
      } else if (res.annotated_image) {
        annotatedImageSrc.value = `data:image/jpeg;base64,${res.annotated_image}`;
      }
    }
  } catch (err) {
    console.error("[检测失败]", err);
    ElMessage.error(err.message || "检测失败");
  } finally {
    uploading.value = false;
  }
}

function resetUpload() {
  result.value = null;
  annotatedImageSrc.value = "";
  annotatedVideoSrc.value = "";
  isVideoResult.value = false;
}

// ════════════════════════════════════════════════════════════
// Tab 2：摄像头检测
// ════════════════════════════════════════════════════════════
const videoRef = ref(null);
const canvasRef = ref(null);

const isRunning = ref(false);
const isConnecting = ref(false);

const detectMode = ref("cpu");
const confThreshold = ref(0.25);

const currentFps = ref(0);
const frameCount = ref(0);
const inferenceTime = ref(0);
const objectCount = ref(0);
const currentDetections = ref([]);

const canvasWidth = ref(640);
const canvasHeight = ref(480);

let cameraWs = null;
let mediaStream = null;

const statusText = computed(() => {
  if (isConnecting.value) return "连接中...";
  if (isRunning.value) return "运行中";
  return "未启动";
});

const statusTagType = computed(() => {
  if (isConnecting.value) return "warning";
  if (isRunning.value) return "success";
  return "info";
});

const classDistribution = computed(() => {
  const dist = {};
  for (const det of currentDetections.value) {
    dist[det.class_name] = (dist[det.class_name] || 0) + 1;
  }
  return dist;
});

async function startCamera() {
  try {
    isConnecting.value = true;

    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: "user",
      },
      audio: false,
    });

    videoRef.value.srcObject = mediaStream;
    await videoRef.value.play();

    canvasWidth.value = videoRef.value.videoWidth || 640;
    canvasHeight.value = videoRef.value.videoHeight || 480;

    createCameraWsInstance();
    cameraWs.connect();

    isRunning.value = true;
    ElMessage.success("摄像头已开启");
  } catch (err) {
    console.error("[摄像头开启失败]", err);
    ElMessage.error(`摄像头开启失败: ${err.message}`);
    isConnecting.value = false;
  }
}

function createCameraWsInstance() {
  cameraWs = createCameraWs({
    mode: detectMode.value,
    conf: confThreshold.value,
    onResult: handleDetectionResult,
    onConfigOk: handleConfigOk,
    onError: handleWsError,
    onClose: handleWsClose,
  });
}

function handleDetectionResult(data) {
  renderAnnotatedFrame(data.annotatedFrame);
  currentFps.value = data.fps;
  frameCount.value = data.frameCount;
  inferenceTime.value = data.inferenceTime;
  objectCount.value = data.objectCount;
  currentDetections.value = data.detections;
}

function handleConfigOk() {
  requestAnimationFrame(sendSingleFrame);
}

function handleWsError(msg) {
  ElMessage.error(msg);
}

function handleWsClose() {
  isConnecting.value = false;
}

function sendSingleFrame() {
  if (!cameraWs || !cameraWs.isConnected) return;
  if (!videoRef.value || videoRef.value.readyState < 2) return;

  const targetSize = detectMode.value === "cpu" ? 416 : 640;
  const tempCanvas = document.createElement("canvas");
  tempCanvas.width = targetSize;
  tempCanvas.height = targetSize;
  const ctx = tempCanvas.getContext("2d");

  const vw = videoRef.value.videoWidth;
  const vh = videoRef.value.videoHeight;
  const scale = Math.min(targetSize / vw, targetSize / vh);
  const x = (targetSize - vw * scale) / 2;
  const y = (targetSize - vh * scale) / 2;
  ctx.drawImage(videoRef.value, x, y, vw * scale, vh * scale);

  const dataUrl = tempCanvas.toDataURL("image/jpeg", 0.6);
  const base64Data = dataUrl.split(",")[1];

  cameraWs.sendFrame(base64Data);
}

function renderAnnotatedFrame(annotatedBase64) {
  if (!canvasRef.value) return;

  const img = new Image();
  img.onload = () => {
    const ctx = canvasRef.value.getContext("2d");
    canvasRef.value.width = img.width;
    canvasRef.value.height = img.height;
    ctx.drawImage(img, 0, 0);

    requestAnimationFrame(sendSingleFrame);
  };
  img.src = `data:image/jpeg;base64,${annotatedBase64}`;
}

function stopCamera() {
  if (cameraWs) {
    cameraWs.close();
    cameraWs = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  isRunning.value = false;
  isConnecting.value = false;
  currentFps.value = 0;
  inferenceTime.value = 0;
  objectCount.value = 0;
  currentDetections.value = [];

  if (canvasRef.value) {
    const ctx = canvasRef.value.getContext("2d");
    ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height);
  }

  ElMessage.info("摄像头已停止");
}

onBeforeUnmount(() => {
  stopCamera();
});
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;

.detection-tabs {
  :deep(.el-tabs__content) {
    padding: $spacing-lg;
  }
}

/* ===========================
   Upload
=========================== */

.upload-area {
  max-width: 900px;
  margin: 0 auto;

  :deep(.el-upload-dragger) {
    padding: 64px 24px;
    border-radius: $border-radius-lg;
    border: 2px dashed $border-color;
    background: $background-secondary;
    transition: all .25s ease;

    &:hover {
      border-color: $primary-color;
      background: rgba($primary-color,.04);
    }
  }
}

.upload-icon {
  font-size: 52px;
  color: $primary-color;
  margin-bottom: $spacing-md;
}

.upload-text {
  font-size: 20px;
  font-weight: 600;
}

.upload-hint {
  margin-top: $spacing-sm;
  color: $text-secondary;
}

.loading-area {
  padding: 80px;
  text-align: center;
}

.result-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: $spacing-md;
}

.result-image,
.result-video {
  width: 100%;
  max-height: 520px;
  object-fit: contain;
  border-radius: $border-radius-lg;
  margin-bottom: $spacing-lg;
}

/* ===========================
   Camera
=========================== */

.camera-layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: $spacing-lg;
}

.camera-side {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

.video-wrapper {
  position: relative;
  border-radius: $border-radius-lg;
  overflow: hidden;
  background: #000;
  min-height: 420px;

  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-canvas {
  width: 100%;
  display: block;
}

.video-stats {
  margin-top: $spacing-md;
  display: flex;
  gap: $spacing-sm;
}

.control-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-md;
  margin-top: $spacing-xl;
}

.control-label {
  color: $text-secondary;
  white-space: nowrap;
}

/* ===========================
   Detection List
=========================== */

.detection-list {
  max-height: 320px;
  overflow-y: auto;
}

.detection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-md 0;
  border-bottom: 1px solid $border-color;

  &:last-child {
    border-bottom: none;
  }
}

.det-info {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.det-class {
  min-width: 90px;
  font-weight: 600;
}

.det-bbox {
  font-family: monospace;
  font-size: 12px;
  color: $text-secondary;
}

/* ===========================
   Distribution
=========================== */

.distribution-list {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-sm;
}

.distribution-item {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs $spacing-sm;
  border-radius: $border-radius-md;
  background: $background-secondary;
}

/* ===========================
   Responsive
=========================== */

@media (max-width: 1200px) {
  .camera-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .control-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .video-stats {
    flex-wrap: wrap;
  }
}
</style>
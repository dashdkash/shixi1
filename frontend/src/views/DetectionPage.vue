<template>
  <div class="detection-page">
    <el-tabs v-model="activeTab" type="border-card" class="detection-tabs">
      <!-- ══════════════════════════════════════════════════
           Tab 1：图片 / 视频上传检测
           ══════════════════════════════════════════════════ -->
      <el-tab-pane label="图片/视频检测" name="upload">
        <div class="upload-panel">
          <!-- 上传区域 -->
          <el-upload
            v-if="!result"
            class="upload-area"
            drag
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileChange"
            accept="image/*,video/mp4,video/avi,video/quicktime,video/x-msvideo"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">上传图片或视频进行检测</div>
            <div class="upload-hint">
              支持 JPG、PNG、BMP、WebP、MP4、AVI、MOV 格式，可批量上传
            </div>
          </el-upload>

          <!-- 检测结果 -->
          <div v-if="result" class="result-area">
            <div class="result-header">
              <h3>检测结果</h3>
              <el-button @click="resetUpload">重新检测</el-button>
            </div>

            <!-- 视频结果 -->
            <div v-if="isVideoResult" class="video-result">
              <video
                v-if="annotatedVideoSrc"
                :src="annotatedVideoSrc"
                controls
                class="result-video"
              />
              <DetectionResultCard
                v-if="result"
                :result="result"
                :loading="false"
              />
            </div>

            <!-- 图片结果 -->
            <div v-else class="image-result">
              <img
                v-if="annotatedImageSrc"
                :src="annotatedImageSrc"
                class="result-image"
              />
              <DetectionResultCard
                v-if="result"
                :result="result"
                :loading="false"
              />
            </div>
          </div>

          <!-- 加载中 -->
          <div v-if="uploading" class="loading-area">
            <el-icon class="is-loading" :size="40"><Loading /></el-icon>
            <p>正在检测中，请稍候...</p>
          </div>
        </div>
      </el-tab-pane>

      <!-- ═══════════════════════════════════════════════════
           Tab 2：摄像头实时检测
           ═══════════════════════════════════════════════════ -->
      <el-tab-pane label="摄像头实时检测" name="camera">
        <div class="camera-panel">
          <div class="page-header">
            <h2>摄像头实时检测</h2>
            <el-tag :type="statusTagType" size="large">
              {{ statusText }}
            </el-tag>
          </div>

          <div class="main-content">
            <div class="preview-panel">
              <div class="video-wrapper">
                <video
                  ref="videoRef"
                  autoplay
                  playsinline
                  muted
                  style="display: none"
                ></video>

                <canvas
                  ref="canvasRef"
                  class="preview-canvas"
                  :width="canvasWidth"
                  :height="canvasHeight"
                ></canvas>

                <div v-if="!isRunning" class="placeholder">
                  <p>点击下方按钮开启摄像头</p>
                </div>
              </div>

              <div v-if="isRunning" class="video-stats">
                <el-tag type="success">FPS: {{ currentFps }}</el-tag>
                <el-tag type="info">帧: {{ frameCount }}</el-tag>
                <el-tag type="info">推理: {{ inferenceTime }}ms</el-tag>
              </div>
            </div>

            <div class="result-panel">
              <el-card class="stats-card" shadow="never">
                <template #header>
                  <span>实时检测统计</span>
                </template>

                <div class="stats-grid">
                  <div class="stat-item">
                    <div class="stat-value">{{ objectCount }}</div>
                    <div class="stat-label">当前目标数</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-value">{{ currentFps }}</div>
                    <div class="stat-label">实时 FPS</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-value">{{ inferenceTime }}</div>
                    <div class="stat-label">推理耗时(ms)</div>
                  </div>
                  <div class="stat-item">
                    <div class="stat-value">{{ frameCount }}</div>
                    <div class="stat-label">已处理帧</div>
                  </div>
                </div>
              </el-card>

              <el-card class="detections-card" shadow="never">
                <template #header>
                  <div class="card-header">
                    <span>当前帧目标列表</span>
                    <el-tag size="small"
                      >{{ currentDetections.length }} 个目标</el-tag
                    >
                  </div>
                </template>

                <div v-if="currentDetections.length === 0" class="empty-state">
                  暂无检测目标
                </div>

                <div v-else class="detection-list">
                  <div
                    v-for="(det, index) in currentDetections"
                    :key="index"
                    class="detection-item"
                  >
                    <div class="det-info">
                      <span class="det-class">{{ det.class_name }}</span>
                      <el-progress
                        :percentage="Math.round(det.confidence * 100)"
                        :stroke-width="6"
                        :show-text="true"
                        style="width: 120px"
                      />
                    </div>
                    <div class="det-bbox">
                      [{{ det.bbox.map((v) => Math.round(v)).join(", ") }}]
                    </div>
                  </div>
                </div>
              </el-card>

              <el-card
                v-if="Object.keys(classDistribution).length > 0"
                class="distribution-card"
                shadow="never"
              >
                <template #header>
                  <span>类别分布</span>
                </template>
                <div class="distribution-list">
                  <div
                    v-for="(count, className) in classDistribution"
                    :key="className"
                    class="distribution-item"
                  >
                    <span class="class-name">{{ className }}</span>
                    <el-tag size="small" type="primary">{{ count }}</el-tag>
                  </div>
                </div>
              </el-card>
            </div>
          </div>

          <div class="control-bar">
            <el-button
              v-if="!isRunning"
              type="primary"
              size="large"
              @click="startCamera"
              :loading="isConnecting"
            >
              开启摄像头
            </el-button>
            <el-button v-else type="danger" size="large" @click="stopCamera">
              停止检测
            </el-button>

            <el-divider direction="vertical" />

            <span class="control-label">推理模式：</span>
            <el-radio-group v-model="detectMode" :disabled="isRunning">
              <el-radio-button label="cpu">CPU 节能</el-radio-button>
              <el-radio-button label="gpu">GPU 加速</el-radio-button>
            </el-radio-group>

            <el-divider direction="vertical" />

            <span class="control-label">置信度：</span>
            <el-slider
              v-model="confThreshold"
              :min="0.1"
              :max="0.9"
              :step="0.05"
              :disabled="isRunning"
              style="width: 150px"
              show-input
            />
          </div>
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
import { createCameraWs } from "@/utils/cameraWs";
import { Loading, UploadFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onBeforeUnmount, ref } from "vue";

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
.detection-page {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100%;
}

.detection-tabs {
  :deep(.el-tabs__content) {
    padding: 20px;
  }
}

/* ═══════════════════════════════════════════════════════════
   Tab 1：上传检测
   ════════════════════════════════════════════════════════════ */
.upload-panel {
  max-width: 900px;
  margin: 0 auto;
}

.upload-area {
  :deep(.el-upload-dragger) {
    padding: 60px 20px;
    border: 2px dashed #dcdfe6;
    border-radius: 12px;
    background: #fafafa;
    transition: border-color 0.3s;

    &:hover {
      border-color: #409eff;
    }
  }
}

.upload-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 12px;
}

.upload-text {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 13px;
  color: #909399;
}

.result-area {
  .result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    h3 {
      margin: 0;
    }
  }
}

.result-video {
  width: 100%;
  max-height: 500px;
  border-radius: 8px;
  margin-bottom: 16px;
  background: #000;
}

.result-image {
  max-width: 100%;
  max-height: 500px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.loading-area {
  text-align: center;
  padding: 60px 20px;
  color: #909399;

  p {
    margin-top: 16px;
    font-size: 16px;
  }
}

/* ════════════════════════════════════════════════════════════
   Tab 2：摄像头检测
   ════════════════════════════════════════════════════════════ */
.camera-panel {
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    h2 {
      margin: 0;
    }
  }

  .main-content {
    display: flex;
    gap: 20px;
    overflow: hidden;
  }

  .preview-panel {
    flex: 3;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .video-wrapper {
    position: relative;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
    min-height: 400px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .preview-canvas {
    width: 100%;
    height: auto;
    display: block;
  }

  .placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #999;
    font-size: 16px;
  }

  .video-stats {
    display: flex;
    gap: 8px;
  }

  .result-panel {
    flex: 2;
    display: flex;
    flex-direction: column;
    gap: 12px;
    overflow-y: auto;
    max-height: 600px;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .stat-item {
    text-align: center;
    padding: 12px;
    background: #f9f9f9;
    border-radius: 8px;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #409eff;
  }

  .stat-label {
    font-size: 12px;
    color: #999;
    margin-top: 4px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .empty-state {
    text-align: center;
    color: #999;
    padding: 20px;
  }

  .detection-list {
    max-height: 300px;
    overflow-y: auto;
  }

  .detection-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;

    &:last-child {
      border-bottom: none;
    }
  }

  .det-info {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .det-class {
    font-weight: 600;
    min-width: 80px;
  }

  .det-bbox {
    font-size: 12px;
    color: #999;
    font-family: monospace;
  }

  .distribution-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .distribution-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    background: #f5f5f5;
    border-radius: 4px;
  }

  .class-name {
    font-weight: 500;
  }

  .control-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 0;
    border-top: 1px solid #e0e0e0;
    margin-top: 16px;
  }

  .control-label {
    font-size: 14px;
    color: #666;
    white-space: nowrap;
  }
}
</style>

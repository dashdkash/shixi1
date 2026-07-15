<template>
  <div class="camera-detection">
    <div class="camera-container">
      <video
        ref="videoElement"
        class="camera-video"
        autoplay
        playsinline
        muted
        @loadedmetadata="onVideoLoaded"
        @click="togglePlay"
      ></video>
      <canvas
        ref="canvasElement"
        class="camera-canvas"
        style="display: none"
      ></canvas>
      <img
        v-if="annotatedFrame"
        :src="annotatedFrame"
        class="annotated-overlay"
      />

      <div
        v-if="!stream && !isRunning && !isConnecting"
        class="camera-placeholder"
      >
        <el-icon class="placeholder-icon"><VideoCamera /></el-icon>
        <p>{{ t("camera.noCamera") }}</p>
      </div>

      <div v-if="stream && !isRunning && !isConnecting" class="camera-ready">
        <p>{{ t("camera.ready") }}</p>
      </div>

      <div v-if="isConnecting" class="camera-connecting">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <p>{{ t("camera.connecting") }}</p>
      </div>

      <div class="camera-controls">
        <el-button
          type="primary"
          :loading="isConnecting"
          @click="startDetection"
          :disabled="isRunning || isConnecting"
        >
          <el-icon><VideoPlay /></el-icon>
          {{ t("camera.start") }}
        </el-button>
        <el-button
          type="danger"
          @click="stopDetection"
          :disabled="!isRunning && !isConnecting"
        >
          <el-icon><VideoPause /></el-icon>
          {{ t("camera.stop") }}
        </el-button>
      </div>

      <div v-if="isRunning" class="camera-stats">
        <div class="stat-item">
          <span class="stat-label">{{ t("camera.fps") }}</span>
          <span class="stat-value">{{ fps.toFixed(1) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ t("camera.objects") }}</span>
          <span class="stat-value">{{ objectCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ t("camera.inference") }}</span>
          <span class="stat-value">{{ inferenceTime.toFixed(2) }}ms</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ t("camera.frame") }}</span>
          <span class="stat-value">{{ frameCount }}</span>
        </div>
      </div>
    </div>

    <div class="config-panel">
      <h3>{{ t("camera.config") }}</h3>

      <el-form :model="config" label-width="100px">
        <el-form-item :label="$t('camera.mode')">
          <el-select v-model="config.mode" placeholder="选择模式">
            <el-option label="CPU" value="cpu" />
            <el-option label="GPU" value="gpu" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('camera.confidence')">
          <el-slider
            v-model="config.conf"
            :min="0.1"
            :max="0.9"
            :step="0.05"
            show-input
          />
        </el-form-item>

        <el-form-item :label="$t('camera.iou')">
          <el-slider
            v-model="config.iou"
            :min="0.1"
            :max="0.9"
            :step="0.05"
            show-input
          />
        </el-form-item>
      </el-form>
    </div>

    <div v-if="detections.length > 0" class="detections-panel">
      <h3>{{ t("camera.detections") }} ({{ detections.length }})</h3>
      <div class="detections-list">
        <div
          v-for="(det, index) in detections"
          :key="index"
          class="detection-item"
        >
          <span class="detection-class">{{ det.class_name }}</span>
          <span class="detection-conf"
            >{{ (det.confidence * 100).toFixed(1) }}%</span
          >
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="error-panel">
      <el-alert
        type="error"
        :message="errorMessage"
        show-icon
        :closable="false"
      />
    </div>
  </div>
</template>

<script setup>
import {
  Loading,
  VideoCamera,
  VideoPause,
  VideoPlay,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { onUnmounted, reactive, ref } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n({ useScope: "global" });

const videoElement = ref(null);
const canvasElement = ref(null);
const annotatedFrame = ref("");

const isRunning = ref(false);
const isConnecting = ref(false);
const errorMessage = ref("");
const stream = ref(null);

const fps = ref(0);
const objectCount = ref(0);
const inferenceTime = ref(0);
const frameCount = ref(0);
const detections = ref([]);

let websocket = null;
let sendInterval = null;

const config = reactive({
  mode: "cpu",
  conf: 0.25,
  iou: 0.45,
});

const getWebSocketUrl = () => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/detection/camera`;
};

const onVideoLoaded = () => {
  if (videoElement.value) {
    videoElement.value.play();
  }
};

const togglePlay = () => {
  if (videoElement.value) {
    if (videoElement.value.paused) {
      videoElement.value.play();
    } else {
      videoElement.value.pause();
    }
  }
};

const startDetection = async () => {
  errorMessage.value = "";
  isConnecting.value = true;

  try {
    const mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "environment",
        width: { ideal: 640 },
        height: { ideal: 480 },
      },
      audio: false,
    });

    stream.value = mediaStream;

    if (videoElement.value) {
      videoElement.value.srcObject = mediaStream;
    }

    websocket = new WebSocket(getWebSocketUrl());

    websocket.onopen = () => {
      websocket.send(
        JSON.stringify({
          type: "config",
          mode: config.mode,
          conf: config.conf,
          iou: config.iou,
        }),
      );
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "config_ok") {
          isRunning.value = true;
          isConnecting.value = false;
          ElMessage.success(data.message);
          startFrameSending();
        } else if (data.type === "result") {
          if (data.annotated_frame) {
            annotatedFrame.value = `data:image/jpeg;base64,${data.annotated_frame}`;
          }
          if (data.detections) {
            detections.value = data.detections;
          }
          if (data.object_count !== undefined) {
            objectCount.value = data.object_count;
          }
          if (data.inference_time !== undefined) {
            inferenceTime.value = data.inference_time;
          }
          if (data.fps !== undefined) {
            fps.value = data.fps;
          }
          if (data.frame_count !== undefined) {
            frameCount.value = data.frame_count;
          }
        } else if (data.type === "error") {
          errorMessage.value = data.message;
        }
      } catch (e) {
        console.error("WebSocket message parse error:", e);
      }
    };

    websocket.onerror = (error) => {
      isConnecting.value = false;
      errorMessage.value = t("camera.connectionError");
      console.error("WebSocket error:", error);
    };

    websocket.onclose = () => {
      if (isRunning.value) {
        stopDetection();
      }
    };
  } catch (err) {
    isConnecting.value = false;
    errorMessage.value = t("camera.cameraError");
    console.error("Camera access error:", err);
  }
};

const startFrameSending = () => {
  sendInterval = setInterval(() => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
    if (!videoElement.value || !canvasElement.value) return;

    const video = videoElement.value;
    const canvas = canvasElement.value;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const base64 = canvas.toDataURL("image/jpeg", 0.7).split(",")[1];

    websocket.send(JSON.stringify({ type: "frame", data: base64 }));
  }, 100);
};

const stopDetection = () => {
  isRunning.value = false;
  annotatedFrame.value = "";
  detections.value = [];

  if (sendInterval) {
    clearInterval(sendInterval);
    sendInterval = null;
  }

  if (websocket) {
    try {
      websocket.send(JSON.stringify({ type: "close" }));
    } catch (e) {}
    websocket.close();
    websocket = null;
  }

  if (stream.value) {
    stream.value.getTracks().forEach((track) => track.stop());
    stream.value = null;
  }

  if (videoElement.value) {
    videoElement.value.srcObject = null;
  }

  ElMessage.info(t("camera.stopped"));
};

onUnmounted(() => {
  stopDetection();
});
</script>

<style lang="scss" scoped>
.camera-detection {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.camera-container {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: #000;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 100%;
  aspect-ratio: 4/3;
}

.camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.annotated-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
}

.camera-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #1a1a1a;
  color: #909399;

  .placeholder-icon {
    font-size: 48px;
    margin-bottom: 12px;
    opacity: 0.5;
  }

  p {
    font-size: 14px;
  }
}

.camera-ready {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  color: #fff;

  p {
    font-size: 16px;
    background: rgba(0, 0, 0, 0.6);
    padding: 10px 20px;
    border-radius: 8px;
  }
}

.camera-connecting {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  z-index: 50;

  .loading-icon {
    font-size: 32px;
    margin-bottom: 12px;
    animation: spin 1s linear infinite;
  }

  p {
    font-size: 16px;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.camera-controls {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 12px;
  z-index: 100;
  background: rgba(0, 0, 0, 0.6);
  padding: 10px 20px;
  border-radius: 8px;

  :deep(.el-button) {
    padding: 8px 16px;
    font-size: 14px;
  }
}

.camera-stats {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 16px;
  background: rgba(0, 0, 0, 0.6);
  padding: 8px 16px;
  border-radius: 8px;
  z-index: 100;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;

  .stat-label {
    font-size: 10px;
    color: #909399;
  }

  .stat-value {
    font-size: 14px;
    font-weight: 600;
    color: #fff;
  }
}

.config-panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }
}

.detections-panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 12px;
  }
}

.detections-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detection-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(64, 158, 255, 0.1);
  border-radius: 20px;

  .detection-class {
    font-size: 13px;
    color: #409eff;
    font-weight: 500;
  }

  .detection-conf {
    font-size: 12px;
    color: #909399;
  }
}

.error-panel {
  margin-top: 16px;
}
</style>

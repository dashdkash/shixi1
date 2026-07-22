<template>
  <div class="detection-container">
    <el-tabs v-model="activeTab" type="card">
      <!-- ── Tab 1: 文件检测（图片+视频） ── -->
      <el-tab-pane :label="$t('detection.fileTab')" name="file">
    <div
      class="upload-area"
      :class="{ 'is-dragover': isDragover }"
      @dragover.prevent="handleDragOver"
      @dragleave="handleDragLeave"
      @drop.prevent="handleDrop"
      @paste="handlePaste"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        multiple
        accept="image/*,.zip,video/mp4,video/avi,video/quicktime,video/x-msvideo"
        class="file-input"
        @change="handleFileSelect"
      />

      <div class="upload-content">
        <el-icon class="upload-icon">
          <Upload />
        </el-icon>
        <h3>{{ $t("detection.uploadTitle") }}</h3>
        <p>{{ $t("detection.uploadHint") }}</p>
        <p class="upload-tip">{{ $t("detection.uploadTip") }}</p>
      </div>
    </div>

    <div v-if="pendingFiles.length > 0" class="pending-list">
      <h3>{{ $t("detection.pendingTitle") }} ({{ pendingFiles.length }})</h3>
      <div class="file-grid">
        <div
          v-for="(file, index) in pendingFiles"
          :key="index"
          class="file-item"
        >
          <img :src="file.preview" :alt="file.name" class="file-thumb" />
          <div class="file-info">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
          </div>
          <el-button type="text" class="remove-btn" @click="removeFile(index)">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <div class="action-bar">
        <el-button
          type="primary"
          :loading="isProcessing"
          @click="startDetection"
          :disabled="pendingFiles.length === 0 || isProcessing"
        >
          <el-icon><Search /></el-icon>
          {{ $t("detection.startDetection") }}
        </el-button>
        <el-button type="default" @click="clearAllFiles">
          {{ $t("detection.clearAll") }}
        </el-button>
      </div>
    </div>

    <div v-if="detectionResults.length > 0" class="results-section">
      <h3>{{ $t("detection.resultsTitle") }}</h3>

      <div class="results-summary">
        <div class="summary-item">
          <span class="summary-label">{{ $t("detection.totalImages") }}</span>
          <span class="summary-value">{{ summary.total }}</span>
        </div>
        <div class="summary-item success">
          <span class="summary-label">{{ $t("detection.successCount") }}</span>
          <span class="summary-value">{{ summary.success }}</span>
        </div>
        <div class="summary-item error">
          <span class="summary-label">{{ $t("detection.failedCount") }}</span>
          <span class="summary-value">{{ summary.failed }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">{{ $t("detection.totalObjects") }}</span>
          <span class="summary-value">{{ summary.objects }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">{{ $t("detection.totalTime") }}</span>
          <span class="summary-value">{{ summary.time }}ms</span>
        </div>
      </div>

      <div class="results-grid">
        <div
          v-for="(result, index) in detectionResults"
          :key="index"
          class="result-card"
          :class="{ success: result.success, failed: !result.success }"
        >
          <div class="result-header">
            <span class="result-filename">{{ result.filename }}</span>
            <el-tag :type="result.success ? 'success' : 'danger'">
              {{
                result.success
                  ? $t("detection.success")
                  : $t("detection.failed")
              }}
            </el-tag>
          </div>

          <div v-if="result.success" class="result-content">
            <img
              v-if="result.annotated_image_base64"
              :src="'data:image/jpeg;base64,' + result.annotated_image_base64"
              class="annotated-image"
            />
            <div class="result-stats">
              <span
                >{{ $t("detection.inferenceTime") }}:
                {{ result.inference_time?.toFixed(2) || 0 }}ms</span
              >
              <span
                >{{ $t("detection.objectsFound") }}:
                {{ result.objects?.length || 0 }}</span
              >
            </div>

            <div v-if="result.objects?.length > 0" class="objects-list">
              <div
                v-for="(obj, objIndex) in result.objects"
                :key="objIndex"
                class="object-item"
              >
                <span class="object-class">{{ obj.class_name_cn }}</span>
                <span class="object-conf"
                  >{{ (obj.confidence * 100).toFixed(1) }}%</span
                >
              </div>
            </div>
          </div>

          <div v-else class="result-error">
            {{ result.error }}
          </div>
        </div>
      </div>
    </div>

      <!-- ── 视频检测区域 ── -->
      <div v-if="videoResult" class="video-result-section">
        <h3>视频检测结果</h3>
        <div class="video-player-wrapper">
          <video
            v-if="videoResult.videoUrl"
            :src="videoResult.videoUrl"
            controls
            class="video-player"
          ></video>
          <div class="video-stats">
            <span>总帧数: {{ videoResult.total_frames }}</span>
            <span>处理帧数: {{ videoResult.processed_frames }}</span>
            <span>检测目标数: {{ videoResult.total_objects }}</span>
            <span>耗时: {{ videoResult.total_inference_time }}ms</span>
          </div>
          <div v-if="videoResult.class_counts" class="video-class-counts">
            <el-tag
              v-for="(count, cls) in videoResult.class_counts"
              :key="cls"
              type="info"
              class="class-tag"
            >
              {{ cls }}: {{ count }}
            </el-tag>
          </div>
          <!-- 视频下载链接 -->
          <div v-if="videoResult.videoUrl" class="video-download-link">
            <div class="download-label">标注视频（带检测框）：</div>
            <a :href="videoResult.videoUrl" target="_blank" class="download-link">
              ▶ 点击下载/在线观看（有效期 7 天）
            </a>
          </div>
        </div>
      </div>
      <div v-if="videoProgress > 0 && videoProgress < 100" class="video-progress">
        <el-progress :percentage="videoProgress" :stroke-width="12" />
        <p>{{ videoMessage }}</p>
      </div>
      </el-tab-pane>

      <!-- ── Tab 2: 摄像头检测 ── -->
      <el-tab-pane :label="$t('detection.cameraTab')" name="camera">
        <CameraDetection />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { detectBatch, detectVideo, detectZip, getVideoStatus } from "@/api/detection";
import CameraDetection from "@/components/CameraDetection.vue";
import request from "@/utils/request";
import { Close, Search, Upload } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const { t } = useI18n({ useScope: "global" });
const activeTab = ref(route.query.tab === "camera" ? "camera" : "file");

// 监听路由 query 变化（从聊天页跳转摄像头 Tab）
watch(
  () => route.query.tab,
  (tab) => {
    if (tab === "camera" || tab === "file") {
      activeTab.value = tab;
    }
  },
);
const fileInput = ref(null);
const isDragover = ref(false);
const isProcessing = ref(false);
const pendingFiles = ref([]);
const detectionResults = ref([]);

// ── 视频检测状态 ──
const videoResult = ref(null);
const videoProgress = ref(0);
const videoMessage = ref("");


const summary = computed(() => {
  const total = detectionResults.value.length;
  const success = detectionResults.value.filter((r) => r.success).length;
  const failed = total - success;
  const objects = detectionResults.value.reduce(
    (sum, r) => sum + (r.success ? r.objects?.length || 0 : 0),
    0,
  );
  const time = detectionResults.value.reduce(
    (sum, r) => sum + (r.success ? r.inference_time || 0 : 0),
    0,
  );

  return { total, success, failed, objects, time: time.toFixed(2) };
});

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
};

const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  addFiles(files);
  event.target.value = "";
};

const handleDragOver = () => {
  isDragover.value = true;
};

const handleDragLeave = () => {
  isDragover.value = false;
};

const handleDrop = (event) => {
  isDragover.value = false;
  const files = Array.from(event.dataTransfer.files);
  addFiles(files);
};

const handlePaste = async (event) => {
  const items = event.clipboardData?.items;
  if (!items) return;

  const files = [];
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) {
        files.push(file);
      }
    }
  }

  if (files.length > 0) {
    addFiles(files);
    ElMessage.success(`${files.length} ${t("detection.imagesPasted")}`);
  }
};

const addFiles = (files) => {
  const imageFiles = files.filter((f) => f.type.startsWith("image/"));
  const zipFiles = files.filter(
    (f) =>
      f.type === "application/zip" ||
      f.type === "application/x-zip-compressed" ||
      f.name.toLowerCase().endsWith(".zip"),
  );
  const videoFiles = files.filter(
    (f) =>
      f.type.startsWith("video/") ||
      [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"].some((ext) =>
        f.name.toLowerCase().endsWith(ext),
      ),
  );

  imageFiles.forEach((file) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      pendingFiles.value.push({
        name: file.name,
        size: file.size,
        file: file,
        preview: e.target?.result,
      });
    };
    reader.readAsDataURL(file);
  });

  zipFiles.forEach((file) => {
    pendingFiles.value.push({
      name: file.name,
      size: file.size,
      file: file,
      isZip: true,
      preview: null,
    });
  });

  videoFiles.forEach((file) => {
    pendingFiles.value.push({
      name: file.name,
      size: file.size,
      file: file,
      isVideo: true,
      preview: null,
    });
  });

  const total = imageFiles.length + zipFiles.length + videoFiles.length;
  if (total > 0) {
    ElMessage.success(`${total} ${t("detection.filesAdded")}`);
  }

  const nonValidFiles = files.filter(
    (f) =>
      !f.type.startsWith("image/") &&
      f.type !== "application/zip" &&
      f.type !== "application/x-zip-compressed" &&
      !f.name.toLowerCase().endsWith(".zip") &&
      !f.type.startsWith("video/") &&
      ![".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"].some((ext) =>
        f.name.toLowerCase().endsWith(ext),
      ),
  );
  if (nonValidFiles.length > 0) {
    ElMessage.warning(
      `${nonValidFiles.length} ${t("detection.invalidFiles")}`,
    );
  }
};

const removeFile = (index) => {
  pendingFiles.value.splice(index, 1);
};

const clearAllFiles = () => {
  pendingFiles.value = [];
};

const startDetection = async () => {
  if (pendingFiles.value.length === 0) return;

  isProcessing.value = true;

  try {
    // ── 检查是否有视频文件 ──
    const videoFiles = pendingFiles.value.filter((f) => f.isVideo);
    const nonVideoFiles = pendingFiles.value.filter((f) => !f.isVideo);

    // ── 处理视频文件 ──
    for (const vf of videoFiles) {
      const formData = new FormData();
      formData.append("file", vf.file);
      try {
        const res = await detectVideo(formData);
        if (res.task_id) {
          ElMessage.info(`视频 "${vf.name}" 已上传，正在检测中...`);
          await pollVideoResult(res.task_id);
        }
      } catch (err) {
        ElMessage.error(`视频检测失败: ${err.response?.data?.detail || err.message}`);
      }
    }

    // ── 处理图片/ZIP文件（原有逻辑） ──
    if (nonVideoFiles.length > 0) {
      const formData = new FormData();
      const hasZip = nonVideoFiles.some((f) => f.isZip);

      if (hasZip && nonVideoFiles.length === 1) {
        formData.append("file", nonVideoFiles[0].file);
        const response = await detectZip(formData);
        detectionResults.value = buildResultsFromBatch(response);
      } else {
        nonVideoFiles.forEach((item) => {
          formData.append("files", item.file);
        });
        const response = await detectBatch(formData);
        detectionResults.value = buildResultsFromBatch(response);
      }
    }

    pendingFiles.value = [];
    ElMessage.success(t("detection.detectionComplete"));
  } catch (error) {
    ElMessage.error(t("detection.detectionFailed"));
  } finally {
    isProcessing.value = false;
  }
};

/**
 * 轮询视频检测结果（每2秒轮询，最多5分钟）
 */
const pollVideoResult = async (taskId) => {
  const maxAttempts = 150;
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    try {
      const res = await getVideoStatus(taskId);
      videoProgress.value = res.progress || 0;
      videoMessage.value = res.message || "";

      if (res.status === "completed") {
        const result = res.result || res;
        videoResult.value = {
          videoUrl: result.annotated_video_url
            ? proxyVideoUrl(result.annotated_video_url)
            : null,
          total_frames: result.total_frames || 0,
          processed_frames: result.processed_frames || 0,
          total_objects: result.total_objects || 0,
          total_inference_time: result.total_inference_time || 0,
          class_counts: result.class_counts || {},
        };
        videoProgress.value = 100;
        ElMessage.success("视频检测完成！");
        return;
      } else if (res.status === "failed") {
        ElMessage.error(`视频检测失败: ${res.message || "未知错误"}`);
        videoProgress.value = 0;
        return;
      }
    } catch (err) {
      console.error("轮询视频状态失败:", err);
    }
  }
  ElMessage.warning("视频检测超时，请稍后在历史记录中查看结果");
};

/**
 * 将 MinIO 视频 URL 转换为后端代理路径
 */
const proxyVideoUrl = (minioUrl) => {
  if (!minioUrl) return "";
  try {
    const url = new URL(minioUrl);
    const pathParts = url.pathname.split("/").filter(Boolean);
    if (pathParts.length > 1) {
      const subPath = pathParts.slice(1).join("/");
      return `/api/detection/video-proxy/${subPath}`;
    }
    return minioUrl;
  } catch {
    return minioUrl;
  }
};

/**
 * 将后端批量检测响应转换为前端结果卡片格式
 */
const buildResultsFromBatch = (response) => {
  if (!response || response.error) {
    return [
      {
        filename: "检测失败",
        success: false,
        error: response?.error || "检测失败",
        objects: [],
        inference_time: 0,
        width: 0,
        height: 0,
      },
    ];
  }

  // 按 image_path 分组 detections
  const detsByImage = {};
  for (const det of response.detections || []) {
    const key = det.image_path || "unknown";
    if (!detsByImage[key]) detsByImage[key] = [];
    detsByImage[key].push(det);
  }

  const annotatedImages = response.annotated_images || [];

  if (annotatedImages.length > 0) {
    return annotatedImages.map((img) => {
      const key = img.image_path || "unknown";
      const imageDets = detsByImage[key] || [];
      const objects = imageDets.map((d) => ({
        class_name: d.class_name,
        class_name_cn: d.class_name_cn || d.class_name,
        class_id: d.class_id,
        confidence: d.confidence,
        bbox: d.bbox,
      }));
      const inferenceTime = imageDets[0]?.inference_time || 0;
      return {
        filename: key,
        success: true,
        annotated_image_base64: img.annotated_image_base64,
        objects,
        inference_time: inferenceTime,
      };
    });
  }

  // 回退：只有 detections 时，按图片分组生成结果
  return Object.entries(detsByImage).map(([imgPath, dets]) => ({
    filename: imgPath,
    success: true,
    annotated_image_base64: null,
    objects: dets.map((d) => ({
      class_name: d.class_name,
      class_name_cn: d.class_name_cn || d.class_name,
      class_id: d.class_id,
      confidence: d.confidence,
      bbox: d.bbox,
    })),
    inference_time: dets[0]?.inference_time || 0,
  }));
};
</script>

<style lang="scss" scoped>
.detection-container {
  max-width: 1200px;
  margin: 0 auto;
}

.upload-area {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #f5f7fa;

  &:hover {
    border-color: #1e1e1e;
    background: rgba(0, 0, 0, 0.04);
  }

  &.is-dragover {
    border-color: #1e1e1e;
    background: rgba(0, 0, 0, 0.06);
    transform: scale(1.02);
  }
}

.file-input {
  display: none;
}

.upload-content {
  .upload-icon {
    font-size: 48px;
    color: #1e1e1e;
    margin-bottom: 16px;
  }

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: #909399;
    margin: 0;
  }

  .upload-tip {
    font-size: 12px;
    color: #c0c4cc;
    margin-top: 8px;
  }
}

.pending-list {
  margin-top: 24px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }
}

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.file-item {
  position: relative;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;

  .file-thumb {
    width: 100%;
    height: 120px;
    object-fit: cover;
  }

  &.zip-file .file-thumb {
    background: #f5f7fa;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
  }

  .file-info {
    padding: 8px;

    .file-name {
      display: block;
      font-size: 12px;
      color: #303133;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file-size {
      font-size: 11px;
      color: #c0c4cc;
    }
  }

  .remove-btn {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 24px;
    height: 24px;
    padding: 0;
    background: rgba(0, 0, 0, 0.5);
    color: #fff;
    border-radius: 50%;

    &:hover {
      background: #f56c6c;
    }
  }
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.results-section {
  margin-top: 24px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }
}

.results-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  flex-direction: column;

  .summary-label {
    font-size: 12px;
    color: #c0c4cc;
  }

  .summary-value {
    font-size: 20px;
    font-weight: 700;
    color: #303133;
  }

  &.success .summary-value {
    color: #67c23a;
  }

  &.error .summary-value {
    color: #f56c6c;
  }
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.result-card {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);

  &.success {
    border-left: 4px solid #67c23a;
  }

  &.failed {
    border-left: 4px solid #f56c6c;
  }
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;

  .result-filename {
    font-size: 13px;
    font-weight: 500;
    color: #303133;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
  }
}

.result-content {
  padding: 12px;

  .annotated-image {
    width: 100%;
    max-height: 280px;
    object-fit: contain;
    border-radius: 8px;
    margin-bottom: 12px;
    background: #f5f7fa;
  }

  .result-image-container {
    margin-bottom: 12px;
    border-radius: 4px;
    overflow: hidden;
    cursor: pointer;

    .result-image {
      width: 100%;
      max-height: 200px;
      object-fit: contain;
      transition: opacity 0.2s;

      &:hover {
        opacity: 0.8;
      }
    }
  }

  .result-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 12px;

    span {
      font-size: 12px;
      color: #909399;
      background: #f5f7fa;
      padding: 4px 8px;
      border-radius: 4px;
    }
  }
}

.objects-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.object-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;

  .object-class {
    font-size: 12px;
    color: #1e1e1e;
    font-weight: 500;
  }

  .object-conf {
    font-size: 11px;
    color: #909399;
  }
}

.result-error {
  padding: 12px;
  font-size: 13px;
  color: #f56c6c;
}

/* ── 视频检测结果样式 ── */
.video-result-section {
  margin-top: 24px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }
}

.video-player-wrapper {
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.video-player {
  width: 100%;
  max-height: 500px;
  display: block;
}

.video-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px 16px;
  background: #f5f7fa;

  span {
    font-size: 13px;
    color: #606266;
  }
}

.video-class-counts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;

  .class-tag {
    font-size: 12px;
  }
}

.video-progress {
  margin-top: 16px;
  text-align: center;

  p {
    font-size: 13px;
    color: #909399;
    margin-top: 8px;
  }
}
</style>

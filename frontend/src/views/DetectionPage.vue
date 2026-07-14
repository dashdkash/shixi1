<template>
  <div class="detection-container">
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
        accept="image/*,.zip"
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
        <div class="result-stats">
          <span
            >{{ $t("detection.imageSize") }}: {{ result.width }} ×
            {{ result.height }}</span
          >
          <span
            >{{ $t("detection.inferenceTime") }}:
            {{ result.inference_time }}ms</span
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
  </div>
</template>

<script setup>
import request from "@/utils/request";
import { Close, Search, Upload } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, ref } from "vue";

const fileInput = ref(null);
const isDragover = ref(false);
const isProcessing = ref(false);
const pendingFiles = ref([]);
const detectionResults = ref([]);


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
    ElMessage.success(`${files.length} ${$t("detection.imagesPasted")}`);
  }
};

const addFiles = (files) => {
  const imageFiles = files.filter((f) => f.type.startsWith("image/"));

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

  if (imageFiles.length > 0) {
    ElMessage.success(`${imageFiles.length} ${$t("detection.filesAdded")}`);
  }

  const nonImageFiles = files.filter((f) => !f.type.startsWith("image/"));
  if (nonImageFiles.length > 0) {
    ElMessage.warning(
      `${nonImageFiles.length} ${$t("detection.invalidFiles")}`,
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
    const formData = new FormData();
    const hasZip = pendingFiles.value.some((f) => f.isZip);

    if (hasZip && pendingFiles.value.length === 1) {
      formData.append("file", pendingFiles.value[0].file);
      const response = await request.post("/api/detection/zip", formData, {
        timeout: 180000,
      });
      if (response.annotated_images) {
        detectionResults.value = response.annotated_images.map((img) => ({
          filename: img.image_path,
          success: true,
          annotated_image_base64: img.annotated_image_base64,
          objects: [],
          inference_time: 0,
          width: 0,
          height: 0,
        }));
      } else {
        detectionResults.value = [
          {
            filename: pendingFiles.value[0].name,
            success: true,
            annotated_image_base64: response.annotated_image_base64,
            objects: [],
            inference_time: response.inference_time || 0,
            width: 0,
            height: 0,
          },
        ];
      }
    } else {
      pendingFiles.value.forEach((item) => {
        formData.append("files", item.file);
      });
      const response = await request.post("/api/detection/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      detectionResults.value = response.results;
    }

    pendingFiles.value = [];
    ElMessage.success($t("detection.detectionComplete"));
  } catch (error) {
    ElMessage.error($t("detection.detectionFailed"));
  } finally {
    isProcessing.value = false;
  }
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
    border-color: #409eff;
    background: rgba(64, 158, 255, 0.08);
  }

  &.is-dragover {
    border-color: #409eff;
    background: rgba(64, 158, 255, 0.12);
    transform: scale(1.02);
  }
}

.file-input {
  display: none;
}

.upload-content {
  .upload-icon {
    font-size: 48px;
    color: #409eff;
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
  background: rgba(64, 158, 255, 0.1);
  border-radius: 4px;

  .object-class {
    font-size: 12px;
    color: #409eff;
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
</style>

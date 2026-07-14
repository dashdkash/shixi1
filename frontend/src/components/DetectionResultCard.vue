<template>
  <div class="detection-result-card">
    <div class="card-header">
      <el-icon><DataAnalysis /></el-icon>
      <span>检测结果</span>
      <el-tag size="small" type="success">
        {{ result.total_objects ?? 0 }} 个目标
      </el-tag>
    </div>

    <div class="card-body">
      <!-- 单图模式：标注图 -->
      <div class="result-image" v-if="annotatedImageSrc && !isBatch">
        <img
          :src="annotatedImageSrc"
          alt="检测标注图"
          @click="showFullImage = true"
        />
      </div>

      <!-- 批量模式：多图展示 -->
      <div class="result-images-grid" v-if="isBatch && batchImages.length > 0">
        <div
          v-for="(img, index) in batchImages"
          :key="index"
          class="grid-image"
          @click="previewImage(img)"
        >
          <img :src="img.src" :alt="img.name" />
          <span class="image-name">{{ img.name }}</span>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="result-stats">
        <div class="stat-item">
          <span class="stat-label">推理耗时</span>
          <span class="stat-value">{{ result.inference_time || result.total_inference_time || 0 }}ms</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">检测目标</span>
          <span class="stat-value">{{ result.total_objects ?? 0 }} 个</span>
        </div>
        <div class="stat-item" v-if="isBatch">
          <span class="stat-label">图片数量</span>
          <span class="stat-value">{{ result.total_images ?? batchImages.length }} 张</span>
        </div>

        <!-- 类别统计表格 -->
        <el-table
          v-if="classCountsArray.length > 0"
          :data="classCountsArray"
          size="small"
          style="margin-top: 12px"
        >
          <el-table-column prop="className" label="类别" />
          <el-table-column prop="count" label="数量" width="80" />
        </el-table>
      </div>
    </div>

    <!-- 全屏图片预览 -->
    <el-dialog v-model="showFullImage" title="检测标注图" width="80%">
      <img
        v-if="previewSrc"
        :src="previewSrc"
        style="width: 100%"
        alt="检测标注图"
      />
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * DetectionResultCard — 检测结果卡片组件
 *
 * 在对话消息中展示检测结果，包含：
 *   - 标注图预览（单图/批量多图，点击可放大）
 *   - 目标总数和推理耗时
 *   - 各类别数量统计表格
 */
import { DataAnalysis } from "@element-plus/icons-vue";
import { computed, ref } from "vue";

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
});

const showFullImage = ref(false);
const previewSrc = ref(null);

/** 判断是否为批量检测结果 */
const isBatch = computed(() => {
  return Array.isArray(props.result.annotated_images) && props.result.annotated_images.length > 0;
});

/** 单图模式：标注图 URL（优先使用 MinIO URL，否则用 base64） */
const annotatedImageSrc = computed(() => {
  if (props.result.annotated_image_url) {
    return props.result.annotated_image_url;
  }
  if (props.result.annotated_image_base64) {
    return `data:image/jpeg;base64,${props.result.annotated_image_base64}`;
  }
  return null;
});

/** 批量模式：标注图列表 */
const batchImages = computed(() => {
  if (!isBatch.value) return [];
  return props.result.annotated_images.map((img) => ({
    name: img.image_path || "image",
    src: `data:image/jpeg;base64,${img.annotated_image_base64}`,
  }));
});

/** 点击预览图片 */
function previewImage(img) {
  previewSrc.value = img.src;
  showFullImage.value = true;
}

/** 类别统计转为数组（用于 el-table） */
const classCountsArray = computed(() => {
  const counts = props.result.class_counts || {};
  return Object.entries(counts).map(([className, count]) => ({
    className,
    count,
  }));
});
</script>

<style lang="scss" scoped>
.detection-result-card {
  margin-top: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e0e0e0;
  font-weight: 600;
  font-size: 14px;
}

.card-body {
  display: flex;
  gap: 16px;
  padding: 12px;
}

.result-image {
  flex: 1;
  min-width: 0;

  img {
    width: 100%;
    max-height: 300px;
    object-fit: contain;
    border-radius: 4px;
    cursor: pointer;
    transition: opacity 0.2s;

    &:hover {
      opacity: 0.8;
    }
  }
}

.result-images-grid {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;

  .grid-image {
    text-align: center;
    cursor: pointer;

    img {
      width: 100%;
      height: 100px;
      object-fit: cover;
      border-radius: 4px;
      border: 1px solid #e0e0e0;
      transition: opacity 0.2s;

      &:hover {
        opacity: 0.8;
      }
    }

    .image-name {
      display: block;
      font-size: 11px;
      color: #909399;
      margin-top: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.result-stats {
  flex: 0 0 180px;

  .stat-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 13px;
  }

  .stat-label {
    color: #909399;
  }

  .stat-value {
    font-weight: 600;
    color: #303133;
  }
}
</style>
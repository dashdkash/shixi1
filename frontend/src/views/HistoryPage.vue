<template>
  <div class="history-page">
    <!-- 检测记录列表 -->
    <div class="page-header">
      <h2>检测记录</h2>
    </div>

    <div class="history-list">
      <div v-if="detectionList.length === 0" class="empty-state">
        <el-icon class="empty-icon"><Search /></el-icon>
        <p>{{ $t("history.empty") }}</p>
      </div>

      <div v-else class="record-grid">
        <div
          v-for="record in detectionList"
          :key="record.id"
          class="record-card"
          @click="showDetectionDetail(record)"
        >
          <!-- 预览图 -->
          <div class="record-preview">
            <img
              v-if="record.first_result_id"
              :src="`/api/history/image-proxy/${record.first_result_id}?thumb=true`"
              alt="检测预览图"
              loading="lazy"
              @error="handleImgError"
            />
            <div v-else class="preview-placeholder">
              <el-icon :size="32"><Picture /></el-icon>
            </div>
          </div>

          <div class="record-header">
            <span class="record-id"
              >{{ $t("history.id") }}: {{ record.id }}</span
            >
            <el-tag :type="getStatusType(record.status)" size="small">
              {{ getStatusText(record.status) }}
            </el-tag>
          </div>
          <div class="record-body">
            <div class="record-info">
              <span
                >{{ $t("history.totalImages") }}:
                {{ record.total_images }}</span
              >
              <span
                >{{ $t("history.totalObjects") }}:
                {{ record.total_objects }}</span
              >
              <span
                >{{ $t("history.inferenceTime") }}:
                {{ formatInferenceTime(record.total_inference_time) }}ms</span
              >
            </div>
            <!-- 检测物体标签 -->
            <div
              v-if="record.top_classes && record.top_classes.length"
              class="record-classes"
            >
              <el-tag
                v-for="cls in record.top_classes"
                :key="cls"
                size="small"
                type="success"
                class="class-tag"
              >
                {{ cls }}
              </el-tag>
            </div>
          </div>
          <div class="record-footer">
            <span class="record-time">{{
              formatTime(record.created_at)
            }}</span>
            <el-button type="text" class="view-btn">
              {{ $t("history.viewDetail") }}
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <el-pagination
        v-if="detectionTotal > detectionPageSize"
        class="pagination"
        :current-page="detectionPage"
        :page-size="detectionPageSize"
        :total="detectionTotal"
        @current-change="fetchDetectionHistory"
        layout="total, prev, pager, next"
      />
    </div>

    <!-- 检测详情弹窗 -->
    <el-dialog
      v-model="showDetectionDialog"
      :title="$t('history.detection.detail')"
      width="800px"
      :close-on-click-modal="false"
    >
      <div v-if="currentDetection" class="detection-detail">
        <div class="detail-header">
          <div class="detail-info">
            <span class="detail-id"
              >{{ $t("history.id") }}: {{ currentDetection.id }}</span
            >
            <span class="detail-status">
              <el-tag :type="getStatusType(currentDetection.status)">
                {{ getStatusText(currentDetection.status) }}
              </el-tag>
            </span>
          </div>
          <div class="detail-time">
            {{ formatTime(currentDetection.created_at) }}
          </div>
        </div>

        <div class="detail-summary">
          <div class="summary-item">
            <span class="summary-label">{{ $t("history.totalImages") }}</span>
            <span class="summary-value">{{
              currentDetection.total_images
            }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ $t("history.totalObjects") }}</span>
            <span class="summary-value">{{
              currentDetection.total_objects
            }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">{{ $t("history.inferenceTime") }}</span>
            <span class="summary-value"
              >{{ formatInferenceTime(currentDetection.total_inference_time) }}ms</span
            >
          </div>
        </div>

        <div
          v-if="currentDetection.images && currentDetection.images.length > 0"
          class="detail-images"
        >
          <h4>{{ $t("history.images") }}</h4>
          <div class="images-list">
            <div
            v-for="(image, idx) in currentDetection.images"
            :key="idx"
            class="image-item"
          >
            <!-- 检测标注图 -->
            <div class="image-preview">
              <img
                v-if="image.result_id"
                :src="`/api/history/image-proxy/${image.result_id}`"
                :alt="`检测结果图 ${idx + 1}`"
                loading="lazy"
                @error="handleImgError"
              />
              <div v-else class="preview-placeholder-sm">
                <el-icon :size="24"><Picture /></el-icon>
              </div>
            </div>
            <div class="image-info">
              <span>{{ $t("history.image") }} {{ idx + 1 }}</span>
              <span>{{ formatInferenceTime(image.inference_time) }}ms</span>
            </div>
            <div
              v-if="image.objects && image.objects.length > 0"
              class="objects-list"
            >
              <div
                v-for="(obj, objIdx) in image.objects"
                :key="objIdx"
                class="object-tag"
              >
                {{ obj.class_name_cn || obj.class_name }} ({{
                  (obj.confidence * 100).toFixed(1)
                }}%)
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import request from "@/utils/request";
import {
  ArrowRight,
  Picture,
  Search,
} from "@element-plus/icons-vue";
import { onMounted, ref } from "vue";

const detectionList = ref([]);
const detectionPage = ref(1);
const detectionPageSize = ref(10);
const detectionTotal = ref(0);

const showDetectionDialog = ref(false);
const currentDetection = ref(null);

const formatTime = (timeStr) => {
  if (!timeStr) return "";
  const date = new Date(timeStr);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getStatusType = (status) => {
  const map = {
    pending: "info",
    processing: "warning",
    completed: "success",
    failed: "danger",
  };
  return map[status] || "info";
};

const getStatusText = (status) => {
  const map = {
    pending: "等待中",
    processing: "处理中",
    completed: "已完成",
    failed: "失败",
  };
  return map[status] || status;
};

const formatInferenceTime = (val) => {
  if (val == null) return "—";
  return Number(val).toFixed(2);
};

const handleImgError = (e) => {
  e.target.style.display = "none";
};

const fetchDetectionHistory = async (page = 1) => {
  try {
    const res = await request.get("/history/detection", {
      params: { page, page_size: detectionPageSize.value },
    });
    detectionList.value = res.data || [];
    detectionTotal.value = res.total || 0;
    detectionPage.value = page;
  } catch (e) {
    console.error("获取检测历史失败", e);
  }
};

const showDetectionDetail = async (record) => {
  try {
    const res = await request.get(`/history/detection/${record.id}`);
    currentDetection.value = res;
    showDetectionDialog.value = true;
  } catch (e) {
    console.error("获取检测详情失败", e);
  }
};

onMounted(() => {
  fetchDetectionHistory();
});
</script>

<style lang="scss" scoped>
.history-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #1e1e1e;
  }
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #909399;

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    color: #c0c4cc;
  }

  p {
    margin: 0;
    font-size: 14px;
  }
}

.record-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.record-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 0;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;

  &:hover {
    border-color: #1e1e1e;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  }
}

.record-preview {
  width: 100%;
  height: 140px;
  background: #f5f7fa;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .preview-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #c0c4cc;
  }
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px 0;
  margin-bottom: 8px;

  .record-id {
    font-size: 13px;
    color: #606266;
  }
}

.record-body {
  margin-bottom: 12px;
  padding: 0 16px;
}

.record-info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;

  span {
    font-size: 12px;
    color: #909399;
    background: #f5f7fa;
    padding: 4px 8px;
    border-radius: 4px;
  }
}

.record-classes {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;

  .class-tag {
    font-size: 11px;
  }
}

.record-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;

  .record-time {
    font-size: 12px;
    color: #c0c4cc;
  }

  .view-btn {
    font-size: 12px;
    padding: 0;
    color: #1e1e1e;
  }
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.chat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    border-color: #1e1e1e;
    background: #f5f5f5;
  }
}

.chat-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #1e1e1e;
}

.chat-content {
  flex: 1;
  min-width: 0;

  .chat-title {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chat-meta {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: #909399;
  }
}

.chat-arrow {
  color: #c0c4cc;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.detection-detail {
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 16px;
    border-bottom: 1px solid #f0f0f0;
    margin-bottom: 16px;

    .detail-info {
      display: flex;
      gap: 12px;

      .detail-id {
        font-size: 14px;
        font-weight: 500;
        color: #303133;
      }
    }

    .detail-time {
      font-size: 12px;
      color: #909399;
    }
  }

  .detail-summary {
    display: flex;
    gap: 24px;
    padding: 16px;
    background: #fafafa;
    border-radius: 8px;
    margin-bottom: 20px;
  }

  .summary-item {
    display: flex;
    flex-direction: column;

    .summary-label {
      font-size: 12px;
      color: #909399;
      margin-bottom: 4px;
    }

    .summary-value {
      font-size: 20px;
      font-weight: 700;
      color: #303133;
    }
  }

  .detail-images {
    h4 {
      font-size: 14px;
      font-weight: 500;
      color: #303133;
      margin-bottom: 12px;
    }

    .images-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .image-item {
      padding: 12px;
      background: #f5f7fa;
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      gap: 8px;

      .image-preview {
        width: 100%;
        max-height: 300px;
        overflow: hidden;
        border-radius: 6px;
        background: #e8e8e8;
        display: flex;
        align-items: center;
        justify-content: center;

        img {
          width: 100%;
          max-height: 300px;
          object-fit: contain;
          display: block;
        }

        .preview-placeholder-sm {
          padding: 20px;
          color: #c0c4cc;
        }
      }

      .image-info {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 12px;
        color: #606266;
      }

      .objects-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .object-tag {
        padding: 4px 8px;
        background: #fff;
        border-radius: 4px;
        font-size: 12px;
        color: #1e1e1e;
        border: 1px solid #e4e7ed;
      }
    }
  }
}

.chat-detail {
  .chat-messages {
    max-height: 500px;
    overflow-y: auto;
    padding-right: 8px;
  }

  .message-item {
    display: flex;
    margin-bottom: 16px;

    &.user {
      flex-direction: row-reverse;

      .message-content {
        background: #1e1e1e;
        color: #fff;
        border-radius: 8px 8px 0 8px;
      }

      .message-avatar {
        background: #1e1e1e;
        color: #fff;
      }
    }

    &.assistant {
      .message-content {
        background: #f0f0f0;
        color: #303133;
        border-radius: 8px 8px 8px 0;
      }

      .message-avatar {
        background: #67c23a;
        color: #fff;
      }
    }
  }

  .message-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin: 0 8px;
    font-size: 16px;
  }

  .message-content {
    max-width: 70%;
    padding: 10px 14px;
    font-size: 14px;
    line-height: 1.6;

    .message-text {
      white-space: pre-wrap;
      word-break: break-word;
    }

    .message-time {
      font-size: 11px;
      opacity: 0.7;
      margin-top: 4px;
    }

    .detection-result-link {
      margin-top: 8px;
      padding: 8px;
      background: #fff;
      border: 1px solid #e4e7ed;
      border-radius: 8px;

      .result-preview {
        width: 100%;
        max-height: 200px;
        overflow: hidden;
        border-radius: 6px;
        margin-bottom: 8px;

        img {
          width: 100%;
          height: auto;
          display: block;
          object-fit: contain;
          max-height: 200px;
        }
      }
    }
  }
}
</style>

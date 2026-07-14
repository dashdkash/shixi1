<template>
  <div class="history-page">
    <!-- 标签页切换 -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane :label="$t('history.detection.title')" name="detection">
        <!-- 检测历史列表 -->
        <div class="history-list">
          <div class="list-header">
            <span>{{ $t("history.detection.title") }}</span>
          </div>

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
                    {{ record.total_inference_time }}ms</span
                  >
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
      </el-tab-pane>

      <el-tab-pane :label="$t('history.chat.title')" name="chat">
        <!-- 对话历史列表 -->
        <div class="history-list">
          <div class="list-header">
            <span>{{ $t("history.chat.title") }}</span>
          </div>

          <div v-if="chatList.length === 0" class="empty-state">
            <el-icon class="empty-icon"><ChatDotRound /></el-icon>
            <p>{{ $t("history.empty") }}</p>
          </div>

          <div v-else class="record-list">
            <div
              v-for="session in chatList"
              :key="session.id"
              class="chat-card"
              @click="showChatDetail(session)"
            >
              <div class="chat-icon">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              <div class="chat-content">
                <div class="chat-title">{{ session.title }}</div>
                <div class="chat-meta">
                  <span
                    >{{ session.message_count }}
                    {{ $t("history.messages") }}</span
                  >
                  <span>{{
                    formatTime(session.last_message_at || session.created_at)
                  }}</span>
                </div>
              </div>
              <div class="chat-arrow">
                <el-icon><ArrowRight /></el-icon>
              </div>
            </div>
          </div>

          <el-pagination
            v-if="chatTotal > chatPageSize"
            class="pagination"
            :current-page="chatPage"
            :page-size="chatPageSize"
            :total="chatTotal"
            @current-change="fetchChatHistory"
            layout="total, prev, pager, next"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

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
              >{{ currentDetection.total_inference_time }}ms</span
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
              <div class="image-info">
                <span>{{ $t("history.image") }} {{ idx + 1 }}</span>
                <span>{{ image.inference_time }}ms</span>
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
                  {{ obj.class_name_cn }} ({{
                    (obj.confidence * 100).toFixed(1)
                  }}%)
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 对话详情弹窗 -->
    <el-dialog
      v-model="showChatDialog"
      :title="currentChat?.title || $t('history.chat.detail')"
      width="700px"
      :close-on-click-modal="false"
    >
      <div v-if="currentChat" class="chat-detail">
        <div class="chat-messages">
          <div
            v-for="msg in currentChat.messages"
            :key="msg.id"
            :class="['message-item', msg.role]"
          >
            <div class="message-avatar">
              <el-icon v-if="msg.role === 'user'"><User /></el-icon>
              <el-icon v-else><ChatLineRound /></el-icon>
            </div>
            <div class="message-content">
              <div class="message-text">{{ msg.content }}</div>
              <div class="message-time">{{ formatTime(msg.created_at) }}</div>
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
  ChatDotRound,
  ChatLineRound,
  Search,
  User,
} from "@element-plus/icons-vue";
import { onMounted, ref } from "vue";

const activeTab = ref("detection");

const detectionList = ref([]);
const detectionPage = ref(1);
const detectionPageSize = ref(10);
const detectionTotal = ref(0);

const chatList = ref([]);
const chatPage = ref(1);
const chatPageSize = ref(10);
const chatTotal = ref(0);

const showDetectionDialog = ref(false);
const currentDetection = ref(null);

const showChatDialog = ref(false);
const currentChat = ref(null);

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

const fetchChatHistory = async (page = 1) => {
  try {
    const res = await request.get("/history/chat", {
      params: { page, page_size: chatPageSize.value },
    });
    chatList.value = res.data || [];
    chatTotal.value = res.total || 0;
    chatPage.value = page;
  } catch (e) {
    console.error("获取对话历史失败", e);
  }
};

const handleTabChange = (tab) => {
  if (tab === "detection") {
    fetchDetectionHistory();
  } else {
    fetchChatHistory();
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

const showChatDetail = async (session) => {
  try {
    const res = await request.get(`/history/chat/${session.id}`);
    currentChat.value = res;
    showChatDialog.value = true;
  } catch (e) {
    console.error("获取对话详情失败", e);
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
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    border-color: #409eff;
    box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
  }
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;

  .record-id {
    font-size: 13px;
    color: #606266;
  }
}

.record-body {
  margin-bottom: 12px;
}

.record-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;

  span {
    font-size: 12px;
    color: #909399;
    background: #f5f7fa;
    padding: 4px 8px;
    border-radius: 4px;
  }
}

.record-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;

  .record-time {
    font-size: 12px;
    color: #c0c4cc;
  }

  .view-btn {
    font-size: 12px;
    padding: 0;
    color: #409eff;
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
    border-color: #409eff;
    background: #f5faff;
  }
}

.chat-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #f0f9ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #409eff;
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
        color: #409eff;
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
        background: #409eff;
        color: #fff;
        border-radius: 8px 8px 0 8px;
      }

      .message-avatar {
        background: #409eff;
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
  }
}
</style>

<template>
  <div class="chat-page">
    <!-- ── 消息列表区域 ── -->
    <div class="message-list" ref="messageListRef">
      <div
        v-for="(msg, index) in agentStore.messages"
        :key="index"
        :class="['message-item', `message-${msg.role}`]"
      >
        <div v-if="msg.role === 'user'" class="message-content-wrapper">
          <el-avatar
            :size="36"
            :src="userStore.avatar || undefined"
            class="message-avatar"
          >
            {{ userStore.username?.charAt(0)?.toUpperCase() }}
          </el-avatar>
          <div class="message-bubble user-bubble">
            <div class="message-content">{{ msg.content }}</div>
            <div v-if="msg.image" class="message-attachment">
              <img :src="msg.imagePreview" alt="附件图片" />
            </div>
            <div
              v-if="msg.images && msg.images.length"
              class="message-attachments-grid"
            >
              <img
                v-for="(src, i) in msg.images"
                :key="i"
                :src="src"
                alt="附件图片"
              />
            </div>
            <div v-if="msg.videoUrl" class="message-video-attachment">
              <video
                :src="msg.videoUrl"
                controls
                preload="metadata"
                class="message-video"
              ></video>
            </div>
          </div>
        </div>

        <div
          v-else-if="msg.role === 'assistant'"
          class="message-content-wrapper"
        >
          <el-avatar
            :size="36"
            class="message-avatar assistant-avatar"
            src="/logo.svg"
          ></el-avatar>
          <div class="message-bubble assistant-bubble">
            <div
              class="message-content markdown-body"
              v-html="renderMarkdown(msg.content)"
            ></div>
            <div v-if="msg.loading && !msg.content" class="typing-indicator">
              <span></span><span></span><span></span>
            </div>

            <DetectionResultCard
              v-if="msg.detectionResult"
              :result="msg.detectionResult"
            />
          </div>
        </div>

        <!-- 工具调用提示 -->
        <div v-if="msg.toolCall" class="tool-call-info">
          <el-tag size="small" type="info">
            {{ t("chat.toolCall", { tool: msg.toolCall.tool }) }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- ── 快捷操作栏 ── -->
    <div class="quick-actions">
      <el-button
        @click="handleQuickDetect('single')"
        :disabled="agentStore.isLoading"
      >
        {{ t("chat.quickActions.single") }}
      </el-button>
      <el-button
        @click="handleQuickDetect('batch')"
        :disabled="agentStore.isLoading"
      >
        {{ t("chat.quickActions.batch") }}
      </el-button>
      <el-button
        @click="handleQuickDetect('video')"
        :disabled="agentStore.isLoading"
      >
        {{ t("chat.quickActions.video") }}
      </el-button>
      <el-button
        @click="handleQuickDetect('camera')"
        :disabled="agentStore.isLoading"
      >
        {{ t("chat.quickActions.camera") }}
      </el-button>
    </div>

    <!-- ── 输入区域 ── -->
    <div class="input-area">
      <!-- 附件按钮 -->
      <el-button
        class="attach-btn"
        @click="triggerFileInput"
        :disabled="agentStore.isLoading"
        circle
      >
        📎
      </el-button>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*,.zip,video/mp4,video/avi,video/quicktime,.mp4,.avi,.mov,.mkv,.wmv,.flv"
        style="display: none"
        @change="handleFileSelect"
      />

      <!-- 文本输入框 -->
      <el-input
        v-model="inputText"
        :placeholder="t('chat.inputPlaceholder')"
        @keyup.enter="sendMessage"
        :disabled="agentStore.isLoading"
      />

      <!-- 发送/停止按钮 -->
      <el-button
        v-if="!agentStore.isLoading"
        type="primary"
        @click="sendMessage"
        :disabled="!inputText.trim() && !selectedFile"
      >
        {{ t("chat.send") }}
      </el-button>
      <el-button v-else type="danger" @click="handleStop">{{
        t("chat.stop")
      }}</el-button>
    </div>
  </div>
</template>

<script setup>
/**
 * ChatPage.vue — 智能对话界面
 *
 * 功能：
 *   - 消息气泡（用户/AI 区分）
 *   - 文件附件上传（图片/ZIP 拖拽或选择）
 *   - SSE 流式渲染 AI 回复
 *   - 检测结果卡片展示
 *   - 快捷操作栏（单图/批量/视频/摄像头）
 *   - 中断当前对话
 */
import {
  detectBatch,
  detectSingle,
  detectVideo,
  detectZip,
  getVideoStatus,
} from "@/api/detection";
import DetectionResultCard from "@/components/DetectionResultCard.vue";
import { useAgentStore } from "@/stores/agent";
import { useStatsStore } from "@/stores/stats";
import { useUserStore } from "@/stores/user";
import { renderMarkdown } from "@/utils/markdown";
import request from "@/utils/request";
import { streamChat } from "@/utils/stream";
import { ElMessage } from "element-plus";
import {
  computed,
  getCurrentInstance,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from "vue";
import { useRouter } from "vue-router";

// ── Store ──
const agentStore = useAgentStore();
const userStore = useUserStore();
const statsStore = useStatsStore();
const router = useRouter();

// ── i18n ──
const { proxy } = getCurrentInstance();
const t = proxy.$t.bind(proxy);

// ── 响应式状态 ──
const inputText = ref("");
const selectedFile = ref(null);
const messageListRef = ref(null);
const fileInputRef = ref(null);
const shouldAutoScroll = ref(true);

// ── 计算属性 ──
const canSend = computed(() => {
  return inputText.value.trim() || selectedFile.value;
});

// ── 方法 ──

/** 判断是否为视频文件 */
function isVideoFile(file) {
  if (!file) return false;
  const videoSuffixes = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"];
  const suffix = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
  return videoSuffixes.includes(suffix) || file.type.startsWith("video/");
}

/** 发送消息 */
async function sendMessage() {
  if (!canSend.value) return;

  const message = inputText.value.trim();
  // ── 关键：在清空之前保存文件引用 ──
  const fileToSend = selectedFile.value;
  const isVideo = isVideoFile(fileToSend);
  const imagePreview =
    fileToSend && !isVideo ? URL.createObjectURL(fileToSend) : null;
  const videoPreview =
    fileToSend && isVideo ? URL.createObjectURL(fileToSend) : null;

  // 添加用户消息到列表
  agentStore.addMessage({
    role: "user",
    content: message,
    image: fileToSend && !isVideo ? fileToSend.name : null,
    imagePreview,
    videoUrl: videoPreview,
  });

  // 清空输入
  inputText.value = "";
  selectedFile.value = null;

  // 添加 AI 加载占位
  agentStore.addMessage({
    role: "assistant",
    content: "",
    loading: true,
  });

  // 滚动到底部
  scrollToBottom();

  // ── 如果有附件文件，先上传到服务端获取真实路径 ─
  let serverImagePath = null;
  let serverVideoPath = null;
  if (fileToSend) {
    try {
      const formData = new FormData();
      formData.append("file", fileToSend);
      // 不设置 Content-Type，让 axios 自动添加 boundary
      const uploadResult = await request.post("/chat/upload", formData);
      if (isVideo) {
        serverVideoPath = uploadResult.video_path;
      } else {
        serverImagePath = uploadResult.image_path;
      }
    } catch (err) {
      console.error("[文件上传失败]", err.response?.data || err.message || err);
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `文件上传失败：${err.response?.data?.detail || err.message || "未知错误"}，请重试`;
      lastMsg.loading = false;
      lastMsg.error = true;
      return;
    }
  }

  // 发起 SSE 流式请求
  const requestBody = {
    message,
    ...(serverImagePath ? { image_path: serverImagePath } : {}),
    ...(serverVideoPath ? { video_path: serverVideoPath } : {}),
    // 传递当前会话 ID，为空则后端自动创建新会话
    ...(agentStore.currentSessionId
      ? { session_id: agentStore.currentSessionId }
      : {}),
  };

  let fullContent = "";

  const stop = streamChat("/api/chat/stream", requestBody, {
    onMessage: (data) => {
      // 调试日志：查看收到的所有 SSE 事件
      console.log(
        "[SSE事件]",
        data.type,
        data.type === "tool_result" ? data : "",
      );

      if (data.type === "session_id") {
        // 后端返回当前会话 ID，保存到 store
        agentStore.currentSessionId = data.session_id;
        console.log("[会话ID]", data.session_id);
      } else if (data.type === "text_chunk") {
        fullContent += data.content;
        agentStore.updateLastAssistantMessage(fullContent);
        scrollToBottom();
      } else if (data.type === "tool_call") {
        // 工具调用中，更新最后一条 AI 消息的工具信息
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.toolCall = { tool: data.tool, input: data.input };
      } else if (data.type === "tool_result") {
        // 工具调用返回结果
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        console.log(
          "[工具结果] tool:",
          data.tool,
          "result长度:",
          data.result?.length,
        );
        try {
          const result = JSON.parse(data.result);
          console.log(
            "[工具结果解析]",
            "total_objects:",
            result.total_objects,
            "detections:",
            result.detections?.length,
            "key_frames:",
            result.key_frames?.length,
            "annotated_video_url:",
            result.annotated_video_url,
          );
          if (result.detections || result.key_frames) {
            // 有检测结果，设置到消息中
            lastMsg.detectionResult = result;
            lastMsg.loading = false;
            console.log("[检测结果卡片已设置]", lastMsg.detectionResult);
          }
        } catch (e) {
          console.warn(
            "[工具结果解析失败]",
            e.message,
            "原始数据:",
            data.result?.substring(0, 200),
          );
          // 非检测结果 JSON，作为普通文本
          lastMsg.content += `\n[工具结果: ${data.result?.substring(0, 100)}...]`;
        }
        scrollToBottom();
      } else if (data.type === "error") {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = data.content;
        lastMsg.loading = false;
        lastMsg.error = true;
      }
    },
    onDone: () => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      if (lastMsg.loading) {
        lastMsg.loading = false;
      }
      agentStore.setLoading(false);
    },
    onError: (err) => {
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `抱歉，处理出错了：${err.message}`;
      lastMsg.loading = false;
      lastMsg.error = true;
      agentStore.setLoading(false);
      ElMessage.error("对话请求失败，请重试");
    },
  });

  // 保存 中断函数到 store
  agentStore.abortController = stop;
}

/** 停止生成 */
function handleStop() {
  agentStore.abort();
  const lastMsg = agentStore.messages[agentStore.messages.length - 1];
  if (lastMsg.loading) {
    lastMsg.loading = false;
    lastMsg.content += "\n[已停止生成]";
  }
}

/** 触发文件选择框 */
function triggerFileInput() {
  fileInputRef.value?.click();
}

/** 文件选择回调 */
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
    // 临时保存文件路径（后续上传用）
    file._tempPath = URL.createObjectURL(file);
    ElMessage.info(`${file.name} 已选择`);
  }
}

/** 滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

/** 处理滚动事件 */
function handleScroll() {
  if (!messageListRef.value) return;
  const { scrollTop, scrollHeight, clientHeight } = messageListRef.value;
  const distanceToBottom = scrollHeight - scrollTop - clientHeight;
  shouldAutoScroll.value = distanceToBottom < 100;
}

/**
 * 快捷单图检测流程：
 * 1. 用户点击"📷 单图检测"按钮
 * 2. 弹出文件选择框
 * 3. 选择图片后，调用 detectSingle API
 * 4. 将结果以"用户消息 + AI 结果卡片"的形式插入对话
 */
async function handleQuickDetect(type) {
  if (type === "single") {
    // 创建隐藏的文件选择器
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      // 添加用户消息（显示文件名）
      agentStore.addMessage({
        role: "user",
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file),
      });

      // 添加加载占位
      agentStore.addMessage({
        role: "assistant",
        content: "正在检测中...",
        loading: true,
      });

      // 构造 FormData 并调用 API
      const formData = new FormData();
      formData.append("file", file);

      try {
        const result = await detectSingle(formData);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `检测完成！发现 ${result.total_objects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        statsStore.fetchStats();
      } catch (err) {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = "检测失败，请重试";
        lastMsg.loading = false;
      }
    };
    input.click();
  } else if (type === "batch") {
    // 批量检测（支持多选 + ZIP）
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*,.zip";
    input.multiple = true;
    input.onchange = async (e) => {
      const files = Array.from(e.target.files);
      if (!files.length) return;

      const isZip = files.some((f) => f.name.endsWith(".zip"));
      const formData = new FormData();

      if (isZip && files.length === 1) {
        // 单个 ZIP 文件
        formData.append("file", files[0]);
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ZIP: ${files[0].name}`,
        });
      } else {
        // 多张图片
        files.forEach((f) => formData.append("files", f));
        const imagePreviews = files.map((f) => URL.createObjectURL(f));
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ${files.length} 张图片`,
          images: imagePreviews,
        });
      }

      agentStore.addMessage({
        role: "assistant",
        content: t("chat.batchDetecting"),
        loading: true,
      });

      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData);
        const result = await apiCall;
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];

        // 检查是否有错误
        if (result.error) {
          lastMsg.content = t("chat.batchFailed", { error: result.error });
          lastMsg.loading = false;
          lastMsg.error = true;
          return;
        }

        const totalObjects = result.total_objects ?? 0;
        lastMsg.content = t("chat.batchComplete", { count: totalObjects });
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        statsStore.fetchStats();
        console.log("[批量检测结果]", result);
      } catch (err) {
        console.error("[批量检测异常]", err);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = t("chat.batchFailed", { error: err.message || err });
        lastMsg.loading = false;
        lastMsg.error = true;
      }
    };
    input.click();
  } else if (type === "video") {
    handleVideoDetect();
  } else if (type === "camera") {
    router.push("/detection?tab=camera");
  }
}

async function handleVideoDetect() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "video/mp4,video/avi,video/quicktime,video/x-msvideo";
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      ElMessage.warning("视频文件不能超过 50MB");
      return;
    }

    const videoUrl = URL.createObjectURL(file);

    agentStore.addMessage({
      role: "user",
      content: `[视频检测] ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB)`,
      videoUrl,
    });

    agentStore.addMessage({
      role: "assistant",
      content: "正在上传视频...",
      loading: true,
    });

    const formData = new FormData();
    formData.append("file", file);

    try {
      const uploadResult = await detectVideo(formData);
      const taskId = uploadResult.task_id;

      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = "视频已上传，正在处理中...";

      await pollVideoProgress(taskId);
    } catch (err) {
      console.error("[视频检测失败]", err);
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `视频检测失败：${err.message || err}`;
      lastMsg.loading = false;
      lastMsg.error = true;
    }
  };
  input.click();
}

async function pollVideoProgress(taskId) {
  let pollCount = 0;
  const maxPolls = 60;
  const pollInterval = 2000;

  return new Promise((resolve) => {
    const pollTimer = setInterval(async () => {
      pollCount++;
      try {
        const statusResult = await getVideoStatus(taskId);

        if (statusResult.status === "completed") {
          clearInterval(pollTimer);
          const lastMsg = agentStore.messages[agentStore.messages.length - 1];

          const totalObjects = statusResult.total_objects || 0;
          const classCounts = statusResult.class_counts || {};
          const processedFrames = statusResult.processed_frames || 0;

          let resultText = `视频检测完成！\n\n`;
          resultText += `- 处理帧数：${processedFrames} 帧\n`;
          resultText += `- 检测目标：${totalObjects} 个\n`;

          if (Object.keys(classCounts).length > 0) {
            resultText += `- 类别统计：\n`;
            for (const [className, count] of Object.entries(classCounts)) {
              resultText += `  • ${className}: ${count} 个\n`;
            }
          }

          lastMsg.content = resultText;
          lastMsg.loading = false;
          lastMsg.detectionResult = {
            type: "video",
            total_objects: totalObjects,
            class_counts: classCounts,
            total_inference_time: statusResult.total_inference_time || 0,
            annotated_video_url: statusResult.annotated_video_url,
            duration_seconds: statusResult.duration_seconds,
            fps: statusResult.fps,
            processed_frames: processedFrames,
            key_frames: statusResult.key_frames,
          };
          statsStore.fetchStats();
          resolve();
        } else if (statusResult.status === "failed") {
          clearInterval(pollTimer);
          const lastMsg = agentStore.messages[agentStore.messages.length - 1];
          lastMsg.content = `视频检测失败：${statusResult.message || "未知错误"}`;
          lastMsg.loading = false;
          lastMsg.error = true;
          resolve();
        } else {
          const lastMsg = agentStore.messages[agentStore.messages.length - 1];
          lastMsg.content = `视频检测中... (进度: ${statusResult.progress || 0}%)`;
        }
      } catch (pollErr) {
        console.error("[视频检测轮询失败]", pollErr);
        if (pollCount >= maxPolls) {
          clearInterval(pollTimer);
          const lastMsg = agentStore.messages[agentStore.messages.length - 1];
          lastMsg.content = "视频检测超时，请稍后通过历史记录查看结果";
          lastMsg.loading = false;
          resolve();
        }
      }

      if (pollCount >= maxPolls) {
        clearInterval(pollTimer);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = "视频检测轮询已结束，请通过历史记录查看结果";
        lastMsg.loading = false;
        resolve();
      }
    }, pollInterval);
  });
}

function updateWelcomeMessage() {
  if (agentStore.messages.length === 0) {
    agentStore.addMessage({
      role: "assistant",
      content: t("chat.welcome"),
    });
  } else if (
    agentStore.messages[0].role === "assistant" &&
    !agentStore.messages[0].loading
  ) {
    agentStore.messages[0].content = t("chat.welcome");
  }
}

onMounted(() => {
  updateWelcomeMessage();
  if (messageListRef.value) {
    messageListRef.value.addEventListener("scroll", handleScroll);
  }
});

onUnmounted(() => {
  if (messageListRef.value) {
    messageListRef.value.removeEventListener("scroll", handleScroll);
  }
});

watch(
  () => agentStore.messages.length,
  () => {
    if (shouldAutoScroll.value) {
      scrollToBottom();
    }
  },
);
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: linear-gradient(180deg, #f0f9ff 0%, #f5f7fa 100%);
}

/* ── 消息列表 ── */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

.message-item {
  display: flex;
  margin-bottom: 14px;

  &.message-user {
    justify-content: flex-end;

    .message-content-wrapper {
      flex-direction: row-reverse;

      .message-bubble {
        border-bottom-right-radius: 4px;
        border-bottom-left-radius: 16px;
      }
    }
  }

  &.message-assistant {
    justify-content: flex-start;

    .message-content-wrapper {
      flex-direction: row;

      .message-bubble {
        border-bottom-left-radius: 4px;
        border-bottom-right-radius: 16px;
      }
    }
  }
}

.message-content-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 80%;
}

.message-avatar {
  flex-shrink: 0;
  border: 2px solid #e4e7ed;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);

  &.assistant-avatar {
    background: #fff;
    border-color: #67c23a;
  }
}

.message-bubble {
  flex: 1;
  padding: 10px 14px;
  border-radius: 16px;
  line-height: 1.6;
  word-break: break-word;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.user-bubble {
  background: linear-gradient(135deg, #5b8def 0%, #409eff 100%);
  color: #fff;
  box-shadow: 0 2px 10px rgba(64, 158, 255, 0.3);
}

.assistant-bubble {
  background: #fff;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.message-content {
  white-space: pre-wrap;
  font-size: 14px;
}

.markdown-body {
  h1,
  h2,
  h3 {
    margin-top: 8px;
    margin-bottom: 4px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;
  }
  th,
  td {
    border: 1px solid #dcdfe6;
    padding: 4px 8px;
  }
  code {
    background: #f5f7fa;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 10px 0;

  span {
    width: 6px;
    height: 6px;
    background: #c0c4cc;
    border-radius: 50%;
    animation: typing 1.2s infinite;
  }

  span:nth-child(2) {
    animation-delay: 0.2s;
  }
  span:nth-child(3) {
    animation-delay: 0.4s;
  }
}

.quick-actions {
  display: flex;
  gap: 8px;
  padding: 10px 20px;
  border-top: 1px solid #e4e7ed;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);

  .el-button {
    border-radius: 20px;
    font-size: 13px;
    padding: 6px 16px;
  }
}

.input-area {
  display: flex;
  gap: 10px;
  padding: 12px 20px;
  border-top: 1px solid #e4e7ed;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(10px);

  .el-input {
    flex: 1;

    :deep(.el-input__wrapper) {
      border-radius: 24px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }
  }

  .el-button {
    border-radius: 24px;
    padding: 0 24px;
  }
}

.message-attachment {
  margin-top: 8px;

  img {
    max-width: 180px;
    border-radius: 8px;
    border: 2px solid rgba(255, 255, 255, 0.4);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}

.message-attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
  gap: 6px;
  margin-top: 8px;

  img {
    width: 100%;
    height: 70px;
    object-fit: cover;
    border-radius: 6px;
    border: 2px solid rgba(255, 255, 255, 0.4);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
  }
}

.message-video-attachment {
  margin-top: 8px;

  .message-video {
    max-width: 280px;
    border-radius: 8px;
    border: 2px solid rgba(255, 255, 255, 0.4);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}

.tool-call-info {
  margin-top: 8px;
  padding: 6px 10px;
  background: #f0f9ff;
  border-radius: 6px;
  font-size: 12px;
  color: #409eff;
  border: 1px solid #e3f2fd;
}

.attach-btn {
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s;

  &:hover {
    background: #f0f9ff;
    border-color: #409eff;
    transform: scale(1.05);
  }
}

@keyframes typing {
  0%,
  60%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-4px);
  }
}
</style>

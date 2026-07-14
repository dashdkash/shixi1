<template>
  <div class="chat-page">
<<<<<<< HEAD
=======
    <!-- ── 消息列表区域 ── -->
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
    <div class="message-list" ref="messageListRef">
      <div
        v-for="(msg, index) in agentStore.messages"
        :key="index"
        :class="['message-item', `message-${msg.role}`]"
      >
<<<<<<< HEAD
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
          </div>
        </div>

        <div
          v-else-if="msg.role === 'assistant'"
          class="message-content-wrapper"
        >
          <el-avatar :size="36" class="message-avatar assistant-avatar">
            <span>🌿</span>
          </el-avatar>
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

=======
        <!-- 用户消息 -->
        <div v-if="msg.role === 'user'" class="message-bubble user-bubble">
          <div class="message-content">{{ msg.content }}</div>
          <!-- 单张图片附件 -->
          <div v-if="msg.image" class="message-attachment">
            <img :src="msg.imagePreview" alt="附件图片" />
          </div>
          <!-- 多图附件（批量检测） -->
          <div v-if="msg.images && msg.images.length" class="message-attachments-grid">
            <img v-for="(src, i) in msg.images" :key="i" :src="src" alt="附件图片" />
          </div>
        </div>

        <!-- AI 消息 -->
        <div
          v-else-if="msg.role === 'assistant'"
          class="message-bubble assistant-bubble"
        >
          <div v-if="msg.loading" class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
          <div
            v-else
            class="message-content markdown-body"
            v-html="renderMarkdown(msg.content)"
          ></div>

          <!-- 检测结果卡片 -->
          <DetectionResultCard
            v-if="msg.detectionResult"
            :result="msg.detectionResult"
          />
        </div>

        <!-- 工具调用提示 -->
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
        <div v-if="msg.toolCall" class="tool-call-info">
          <el-tag size="small" type="info">
            🔧 调用工具: {{ msg.toolCall.tool }}
          </el-tag>
        </div>
      </div>
    </div>

<<<<<<< HEAD
=======
    <!-- ── 快捷操作栏 ── -->
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
    <div class="quick-actions">
      <el-button
        @click="handleQuickDetect('single')"
        :disabled="agentStore.isLoading"
      >
        📷 单图检测
      </el-button>
      <el-button
        @click="handleQuickDetect('batch')"
        :disabled="agentStore.isLoading"
      >
        📁 批量/ZIP
      </el-button>
      <el-button disabled>🎬 视频</el-button>
      <el-button disabled>📹 摄像头</el-button>
    </div>

<<<<<<< HEAD
    <div class="input-area">
=======
    <!-- ── 输入区域 ── -->
    <div class="input-area">
      <!-- 附件按钮 -->
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
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
        accept="image/*,.zip"
        style="display: none"
        @change="handleFileSelect"
      />

<<<<<<< HEAD
=======
      <!-- 文本输入框 -->
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
      <el-input
        v-model="inputText"
        placeholder="输入消息，或拖拽图片/ZIP 到这里..."
        @keyup.enter="sendMessage"
        :disabled="agentStore.isLoading"
      />

<<<<<<< HEAD
=======
      <!-- 发送/停止按钮 -->
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
      <el-button
        v-if="!agentStore.isLoading"
        type="primary"
        @click="sendMessage"
        :disabled="!inputText.trim() && !selectedFile"
      >
        发送
      </el-button>
      <el-button v-else type="danger" @click="handleStop"> 停止 </el-button>
    </div>
  </div>
</template>

<script setup>
<<<<<<< HEAD
import { detectBatch, detectSingle, detectZip } from "@/api/detection";
import DetectionResultCard from "@/components/DetectionResultCard.vue";
import { useAgentStore } from "@/stores/agent";
import { useUserStore } from "@/stores/user";
=======
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
import { detectBatch, detectSingle, detectZip } from "@/api/detection";
import DetectionResultCard from "@/components/DetectionResultCard.vue";
import { useAgentStore } from "@/stores/agent";
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
import { renderMarkdown } from "@/utils/markdown";
import request from "@/utils/request";
import { streamChat } from "@/utils/stream";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, ref } from "vue";

<<<<<<< HEAD
const agentStore = useAgentStore();
const userStore = useUserStore();

=======
// ── Store ──
const agentStore = useAgentStore();

// ── 响应式状态 ──
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
const inputText = ref("");
const selectedFile = ref(null);
const messageListRef = ref(null);
const fileInputRef = ref(null);

<<<<<<< HEAD
=======
// ── 计算属性 ──
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
const canSend = computed(() => {
  return inputText.value.trim() || selectedFile.value;
});

<<<<<<< HEAD
=======
// ── 方法 ──

/** 发送消息 */
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
async function sendMessage() {
  if (!canSend.value) return;

  const message = inputText.value.trim();
<<<<<<< HEAD
  const fileToSend = selectedFile.value;
  const imagePreview = fileToSend ? URL.createObjectURL(fileToSend) : null;

=======
  // ── 关键：在清空之前保存文件引用 ──
  const fileToSend = selectedFile.value;
  const imagePreview = fileToSend ? URL.createObjectURL(fileToSend) : null;

  // 添加用户消息到列表
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
  agentStore.addMessage({
    role: "user",
    content: message,
    image: fileToSend ? fileToSend.name : null,
    imagePreview,
  });

<<<<<<< HEAD
  inputText.value = "";
  selectedFile.value = null;

=======
  // 清空输入
  inputText.value = "";
  selectedFile.value = null;

  // 添加 AI 加载占位
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
  agentStore.addMessage({
    role: "assistant",
    content: "",
    loading: true,
  });

<<<<<<< HEAD
  scrollToBottom();

=======
  // 滚动到底部
  scrollToBottom();

  // ── 如果有附件图片，先上传到服务端获取真实路径 ──
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
  let serverImagePath = null;
  if (fileToSend) {
    try {
      const formData = new FormData();
      formData.append("file", fileToSend);
<<<<<<< HEAD
=======
      // 不设置 Content-Type，让 axios 自动添加 boundary
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
      const uploadResult = await request.post("/chat/upload", formData);
      serverImagePath = uploadResult.image_path;
    } catch (err) {
      console.error("[图片上传失败]", err.response?.data || err.message || err);
      const lastMsg = agentStore.messages[agentStore.messages.length - 1];
      lastMsg.content = `图片上传失败：${err.response?.data?.detail || err.message || "未知错误"}，请重试`;
      lastMsg.loading = false;
      lastMsg.error = true;
      return;
    }
  }

<<<<<<< HEAD
  const requestBody = {
    message,
    ...(serverImagePath ? { image_path: serverImagePath } : {}),
=======
  // 发起 SSE 流式请求
  const requestBody = {
    message,
    ...(serverImagePath ? { image_path: serverImagePath } : {}),
    // 传递当前会话 ID，为空则后端自动创建新会话
    ...(agentStore.currentSessionId ? { session_id: agentStore.currentSessionId } : {}),
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
  };

  let fullContent = "";

  const stop = streamChat("/api/chat/stream", requestBody, {
    onMessage: (data) => {
<<<<<<< HEAD
      console.log(
        "[SSE事件]",
        data.type,
        data.type === "tool_result" ? data : "",
      );

      if (data.type === "text_chunk") {
=======
      // 调试日志：查看收到的所有 SSE 事件
      console.log("[SSE事件]", data.type, data.type === "tool_result" ? data : "");

      if (data.type === "session_id") {
        // 后端返回当前会话 ID，保存到 store
        agentStore.currentSessionId = data.session_id;
        console.log("[会话ID]", data.session_id);
      } else if (data.type === "text_chunk") {
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
        fullContent += data.content;
        agentStore.updateLastAssistantMessage(fullContent);
        scrollToBottom();
      } else if (data.type === "tool_call") {
<<<<<<< HEAD
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.toolCall = { tool: data.tool, input: data.input };
      } else if (data.type === "tool_result") {
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
          );
          if (result.detections) {
=======
        // 工具调用中，更新最后一条 AI 消息的工具信息
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.toolCall = { tool: data.tool, input: data.input };
      } else if (data.type === "tool_result") {
        // 工具调用返回结果
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        console.log("[工具结果] tool:", data.tool, "result长度:", data.result?.length);
        try {
          const result = JSON.parse(data.result);
          console.log("[工具结果解析]", "total_objects:", result.total_objects, "detections:", result.detections?.length);
          if (result.detections) {
            // 有检测结果，设置到消息中
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
            lastMsg.detectionResult = result;
            lastMsg.loading = false;
            console.log("[检测结果卡片已设置]", lastMsg.detectionResult);
          }
        } catch (e) {
<<<<<<< HEAD
          console.warn(
            "[工具结果解析失败]",
            e.message,
            "原始数据:",
            data.result?.substring(0, 200),
          );
=======
          console.warn("[工具结果解析失败]", e.message, "原始数据:", data.result?.substring(0, 200));
          // 非检测结果 JSON，作为普通文本
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
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

<<<<<<< HEAD
  agentStore.abortController = stop;
}

=======
  // 保存 中断函数到 store
  agentStore.abortController = stop;
}

/** 停止生成 */
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
function handleStop() {
  agentStore.abort();
  const lastMsg = agentStore.messages[agentStore.messages.length - 1];
  if (lastMsg.loading) {
    lastMsg.loading = false;
    lastMsg.content += "\n[已停止生成]";
  }
}

<<<<<<< HEAD
=======
/** 触发文件选择框 */
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
function triggerFileInput() {
  fileInputRef.value?.click();
}

<<<<<<< HEAD
=======
/** 文件选择回调 */
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
<<<<<<< HEAD
=======
    // 临时保存文件路径（后续上传用）
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
    file._tempPath = URL.createObjectURL(file);
    ElMessage.info(`${file.name} 已选择`);
  }
}

<<<<<<< HEAD
=======
/** 滚动到底部 */
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

<<<<<<< HEAD
async function handleQuickDetect(type) {
  if (type === "single") {
=======
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
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

<<<<<<< HEAD
=======
      // 添加用户消息（显示文件名）
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
      agentStore.addMessage({
        role: "user",
        content: `[快捷检测] ${file.name}`,
        image: file.name,
        imagePreview: URL.createObjectURL(file),
      });

<<<<<<< HEAD
=======
      // 添加加载占位
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
      agentStore.addMessage({
        role: "assistant",
        content: "正在检测中...",
        loading: true,
      });

<<<<<<< HEAD
=======
      // 构造 FormData 并调用 API
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
      const formData = new FormData();
      formData.append("file", file);

      try {
        const result = await detectSingle(formData);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `检测完成！发现 ${result.total_objects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
      } catch (err) {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = "检测失败，请重试";
        lastMsg.loading = false;
      }
    };
    input.click();
  } else if (type === "batch") {
<<<<<<< HEAD
=======
    // 批量检测（支持多选 + ZIP）
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
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
<<<<<<< HEAD
=======
        // 单个 ZIP 文件
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
        formData.append("file", files[0]);
        agentStore.addMessage({
          role: "user",
          content: `[快捷检测] ZIP: ${files[0].name}`,
        });
      } else {
<<<<<<< HEAD
=======
        // 多张图片
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
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
        content: "正在批量检测中...",
        loading: true,
      });

      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData);
        const result = await apiCall;
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];

<<<<<<< HEAD
=======
        // 检查是否有错误
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
        if (result.error) {
          lastMsg.content = `批量检测失败：${result.error}`;
          lastMsg.loading = false;
          lastMsg.error = true;
          return;
        }

        const totalObjects = result.total_objects ?? 0;
        lastMsg.content = `批量检测完成！共 ${totalObjects} 个目标。`;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        console.log("[批量检测结果]", result);
      } catch (err) {
        console.error("[批量检测异常]", err);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `批量检测失败：${err.message || err}`;
        lastMsg.loading = false;
        lastMsg.error = true;
      }
    };
    input.click();
  }
}

onMounted(() => {
<<<<<<< HEAD
=======
  // 页面加载时显示欢迎消息
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
  if (agentStore.messages.length === 0) {
    agentStore.addMessage({
      role: "assistant",
      content:
<<<<<<< HEAD
        "🌿 你好！我是杂草识别智能助手。\n\n我可以帮你：\n- 📷 识别图片中的杂草种类和数量\n- 📊 提供杂草分布统计分析\n- 💡 给出专业的除草建议\n\n上传一张农田或草坪的照片，我来帮你分析！",
=======
        "你好！我是 RSOD 目标检测智能体助手。\n\n你可以：\n- 上传一张图片，让我帮你检测目标\n- 使用下方的快捷按钮直接触发检测\n- 用自然语言描述你的需求\n\n试试发一张图片给我吧！",
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
    });
  }
});
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
<<<<<<< HEAD
  background: linear-gradient(180deg, #f0f9ff 0%, #f5f7fa 100%);
=======
  background: #f5f5f5;
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
}

/* ── 消息列表 ── */
.message-list {
  flex: 1;
  overflow-y: auto;
<<<<<<< HEAD
  padding: 16px 24px;
=======
  padding: 20px;
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
}

.message-item {
  display: flex;
<<<<<<< HEAD
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
=======
  margin-bottom: 16px;

  &.message-user {
    justify-content: flex-end;
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
  }

  &.message-assistant {
    justify-content: flex-start;
<<<<<<< HEAD

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
    background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
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
=======
  }
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.5;
  word-break: break-word;
}

.user-bubble {
  background: #409eff;
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant-bubble {
  background: white;
  border: 1px solid #e0e0e0;
  border-bottom-left-radius: 4px;
}

.message-content {
  white-space: pre-wrap;
}

.markdown-body {
  /* markdown 渲染后的 HTML 样式 */
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
    border: 1px solid #e0e0e0;
    padding: 4px 8px;
  }
  code {
    background: #f0f0f0;
    padding: 2px 4px;
    border-radius: 3px;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;

  span {
    width: 6px;
    height: 6px;
    background: #999;
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

/* ── 快捷操作栏 ── */
.quick-actions {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: white;
}

/* ── 输入区域 ── */
.input-area {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background: white;

  .el-input {
    flex: 1;
  }
}

/* ── 附件预览 ── */
.message-attachment {
  margin-top: 8px;

  img {
    max-width: 200px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
  }
}

/* ── 多图附件网格 ── */
.message-attachments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
  margin-top: 8px;

  img {
    width: 100%;
    height: 80px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid #e0e0e0;
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
  }
}

/* ── 工具调用信息 ── */
.tool-call-info {
  margin-top: 8px;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
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
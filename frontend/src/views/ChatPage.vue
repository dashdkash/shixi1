<template>
  <div class="chat-page-layout">
    <!-- ── 会话侧边栏 ── -->
    <div class="session-sidebar">
      <el-button class="new-chat-btn" @click="agentStore.newChat()">
        ＋ 新对话
      </el-button>
      <div class="session-list">
        <div
          v-for="s in agentStore.sessions"
          :key="s.id"
          :class="['session-item', { active: s.id === agentStore.currentSessionId }]"
          @click="agentStore.switchSession(s.id)"
        >
          <span class="session-title">{{ s.title }}</span>
          <el-icon class="session-delete" @click.stop="agentStore.deleteSession(s.id)">
            <Delete />
          </el-icon>
        </div>
      </div>
    </div>

    <!-- ── 聊天主区域 ── -->
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
            </div>
          </div>

          <div
            v-else-if="msg.role === 'assistant'"
            class="message-content-wrapper"
          >
            <el-avatar :size="36" class="message-avatar assistant-avatar">
              <span></span>
            </el-avatar>
            <div class="message-bubble assistant-bubble">
              <!-- thinking 指示器 -->
              <div v-if="msg.thinking" class="thinking-indicator">
                <span class="thinking-dot"></span>
                <span class="thinking-text">正在思考...</span>
              </div>

              <!-- 工具调用状态卡片 -->
              <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="tool-calls">
                <div
                  v-for="(tc, idx) in msg.toolCalls"
                  :key="idx"
                  :class="['tool-call-item', { 'is-loading': tc.status === 'loading' }]"
                >
                  <span v-if="tc.status === 'loading'" class="tool-icon tool-loading">⟳</span>
                  <span v-else class="tool-icon tool-done">✓</span>
                  <span class="tool-name">{{ getToolName(tc.tool) }}</span>
                  <span v-if="tc.summary" class="tool-summary">{{ tc.summary }}</span>
                </div>
              </div>

              <div
                v-if="msg.content"
                class="message-content markdown-body"
                v-html="renderMarkdown(msg.content)"
              ></div>
              <div v-if="msg.loading && !msg.content && !msg.thinking" class="typing-indicator">
                <span></span><span></span><span></span>
              </div>

              <DetectionResultCard
                v-if="msg.detectionResult"
                :result="msg.detectionResult"
              />
            </div>
          </div>

          <!-- 工具调用提示（兼容旧格式） -->
          <div v-if="msg.toolCall && (!msg.toolCalls || msg.toolCalls.length === 0)" class="tool-call-info">
            <el-tag size="small" type="info">
              🔧 调用工具: {{ msg.toolCall.tool }}
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
          📷 单图检测
        </el-button>
        <el-button
          @click="handleQuickDetect('batch')"
          :disabled="agentStore.isLoading"
        >
           批量/ZIP
        </el-button>
        <el-button disabled>🎬 视频</el-button>
        <el-button disabled> 摄像头</el-button>
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
          accept="image/*,.zip"
          style="display: none"
          @change="handleFileSelect"
        />

        <!-- 文本输入框 -->
        <el-input
          v-model="inputText"
          placeholder="输入消息，或拖拽图片/ZIP 到这里..."
          @keyup.enter="sendMessage"
          :disabled="agentStore.isLoading"
        />

        <!-- 发送/停止按钮 -->
        <el-button
          v-if="!agentStore.isLoading"
          type="primary"
          class="send-btn"
          @click="sendMessage"
          :disabled="!inputText.trim() && !selectedFile"
        >
          发送
        </el-button>
        <el-button v-else type="danger" @click="handleStop"> 停止 </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * ChatPage.vue — 智能对话界面
 *
 * 功能：
 *   - 会话侧边栏（新建/切换/删除对话）
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
import { useUserStore } from "@/stores/user";
import { renderMarkdown } from "@/utils/markdown";
import request from "@/utils/request";
import { streamChat, TOOL_NAME_MAP } from "@/utils/stream";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, ref } from "vue";
import { Delete } from "@element-plus/icons-vue";

/** 工具名称中文映射 */
function getToolName(toolName) {
  return TOOL_NAME_MAP[toolName] || toolName;
}

// ── Store ──
const agentStore = useAgentStore();
const userStore = useUserStore();

// ── 响应式状态 ──
const inputText = ref("");
const selectedFile = ref(null);
const messageListRef = ref(null);
const fileInputRef = ref(null);

// ── 计算属性 ──
const canSend = computed(() => {
  return inputText.value.trim() || selectedFile.value;
});

// ── 方法 ──

/** 发送消息 */
async function sendMessage() {
  if (!canSend.value) return;

  const message = inputText.value.trim();
  // ── 关键：在清空之前保存文件引用 ──
  const fileToSend = selectedFile.value;
  const imagePreview = fileToSend ? URL.createObjectURL(fileToSend) : null;

  // 添加用户消息到列表
  agentStore.addMessage({
    role: "user",
    content: message,
    image: fileToSend ? fileToSend.name : null,
    imagePreview,
  });

  // 清空输入
  inputText.value = "";
  selectedFile.value = null;

  // 添加 AI 加载占位
  agentStore.addMessage({
    role: "assistant",
    content: "",
    loading: true,
    thinking: false,
    toolCalls: [],
  });

  // 滚动到底部
  scrollToBottom();

  // ── 如果有附件图片，先上传到服务端获取真实路径 ──
  let serverImagePath = null;
  if (fileToSend) {
    try {
      const formData = new FormData();
      formData.append("file", fileToSend);
      // 不设置 Content-Type，让 axios 自动添加 boundary
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

  // 发起 SSE 流式请求
  const requestBody = {
    message,
    ...(serverImagePath ? { image_path: serverImagePath } : {}),
    // 传递当前会话 ID，为空则后端自动创建新会话
    ...(agentStore.currentSessionId ? { session_id: agentStore.currentSessionId } : {}),
  };

  let fullContent = "";

  const stop = streamChat("/api/chat/stream", requestBody, {
    onMessage: (data) => {
      // 调试日志：查看收到的所有 SSE 事件
      console.log("[SSE事件]", data.type, data.type === "tool_end" || data.type === "tool_result" ? data : "");

      if (data.type === "session_id") {
        // 后端返回当前会话 ID，保存到 store
        // Only refresh if this is a newly created session
        const isNewSession = !agentStore.currentSessionId;

        agentStore.currentSessionId = data.session_id;
        console.log("[会话ID]", data.session_id);

        if (isNewSession) {
          agentStore.fetchSessions();
        }
      } else if (data.type === "thinking") {
        // Agent 正在思考 — 显示 thinking 指示器
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.thinking = true;
        scrollToBottom();
      } else if (data.type === "text_chunk") {
        // 收到第一个文本 chunk 时，关闭 thinking 状态
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        if (lastMsg.thinking) {
          lastMsg.thinking = false;
        }
        fullContent += data.content;
        agentStore.updateLastAssistantMessage(fullContent);
        scrollToBottom();
      } else if (data.type === "tool_call" || data.type === "tool_start") {
        // 工具开始调用 — 添加到 toolCalls 数组
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        if (lastMsg.thinking) lastMsg.thinking = false;
        if (!lastMsg.toolCalls) lastMsg.toolCalls = [];
        lastMsg.toolCalls.push({
          tool: data.tool,
          status: "loading",
          input: data.input,
          status:"running",
          summary: "",
        });
        // 兼容旧格式
        lastMsg.toolCall = { tool: data.tool, input: data.input };
        scrollToBottom();
      } else if (data.type === "tool_result" || data.type === "tool_end") {
        // 工具调用返回结果
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        const resultData = data.result || data.summary || "";
        console.log("[工具结果] tool:", data.tool, "result长度:", resultData?.length);

        // 更新 toolCalls 数组中对应工具的状态
        if (lastMsg.toolCalls && lastMsg.toolCalls.length > 0) {
          const tc = lastMsg.toolCalls.find(
            (t) => t.tool === data.tool && t.status === "loading"
          );
          if (tc) {
            tc.status = "done";
            tc.summary = data.summary || "";
          }
        }

        try {
          const result = JSON.parse(resultData);
          if (result.detections) {
            // 有检测结果，设置到消息中
            lastMsg.detectionResult = result;
            lastMsg.loading = false;
            console.log("[检测结果卡片已设置]", lastMsg.detectionResult);
          }
        } catch (e) {
          console.warn("[工具结果解析失败]", e.message, "原始数据:", resultData?.substring(0, 200));
        }
        scrollToBottom();
      } else if (data.type === "done") {
        // Agent 回复完成
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.loading = false;
        lastMsg.thinking = false;
        console.log("[完成] 回复长度:", data.full_text?.length);
      } else if (data.type === "error") {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = data.content;
        lastMsg.loading = false;
        lastMsg.thinking = false;
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
        content: "正在批量检测中...",
        loading: true,
      });

      try {
        const apiCall = isZip ? detectZip(formData) : detectBatch(formData);
        const result = await apiCall;
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];

        // 检查是否有错误
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
  // 页面加载时加载会话列表 + 显示欢迎消息
  agentStore.fetchSessions();
  if (agentStore.messages.length === 0) {
   agentStore.newChat();
  }
});
</script>

<style lang="scss" scoped>
// ── 主题色（浓琥珀 / 铁锈色系）───────────────────
// 主强调（琥珀锈）      #c2410c
// 强调悬停（深锈）      #9a3412
// 浅色底纹（暖米）      #fdead9
// 浅色边框              #f3d5b5
// 页面背景（暖白到米）  #fdf6ee → #f7f3ec
// 正文次要色（暖灰棕）  #8a7a6d
// 正文主色（暖炭）      #4a3728
// 用户气泡保持蓝色不变，作为与 AI 消息的对比色

.chat-page-layout {
  display: flex;
  height: 100%;
}

.session-sidebar {
  width: 220px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #ece2d4;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.new-chat-btn {
  width: 100%;
  margin-bottom: 12px;

  &:hover,
  &:focus-visible {
    color: #c2410c;
    border-color: #c2410c;
  }
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  margin-bottom: 4px;

  &:hover {
    background: #faf3ea;
  }
  &.active {
    background: #fdead9;
    color: #c2410c;
  }
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.session-delete {
  opacity: 0;
  transition: opacity 0.2s;
  .session-item:hover & {
    opacity: 1;
  }
}

.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  flex: 1;
  min-width: 0;
  background: linear-gradient(180deg, #fdf6ee 0%, #f7f3ec 100%);
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
  border: 2px solid #ece2d4;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);

  // 助手头像改为琥珀-锈渐变，脱离绿色系
  &.assistant-avatar {
    background: linear-gradient(135deg, #c2410c 0%, #ea7c2c 100%);
    border-color: #c2410c;
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

// 用户气泡保持蓝色，与暖色调 AI 消息形成对比
.user-bubble {
  background: linear-gradient(135deg, #5b8def 0%, #409eff 100%);
  color: #fff;
  box-shadow: 0 2px 10px rgba(64, 158, 255, 0.3);
}

.assistant-bubble {
  background: #fff;
  border: 1px solid #ece2d4;
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
    border: 1px solid #e4d9c8;
    padding: 4px 8px;
  }
  code {
    background: #f7f0e6;
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
    background: #d3c4b3;
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
  border-top: 1px solid #ece2d4;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);

  .el-button {
    border-radius: 20px;
    font-size: 13px;
    padding: 6px 16px;

    &:hover:not(.is-disabled) {
      color: #c2410c;
      border-color: #f0b584;
    }
  }
}

.input-area {
  display: flex;
  gap: 10px;
  padding: 12px 20px;
  border-top: 1px solid #ece2d4;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(10px);

  .el-input {
    flex: 1;

    :deep(.el-input__wrapper) {
      border-radius: 24px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
      transition: box-shadow 0.15s ease;

      &.is-focus {
        box-shadow: 0 0 0 1px #c2410c inset, 0 2px 8px rgba(0, 0, 0, 0.06);
      }
    }
  }

  .el-button {
    border-radius: 24px;
    padding: 0 24px;
  }
}

// 发送按钮改为琥珀锈色，替代 Element Plus 默认蓝
.send-btn {
  background-color: #c2410c;
  border-color: #c2410c;

  &:hover,
  &:focus-visible {
    background-color: #9a3412;
    border-color: #9a3412;
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
  background: #fdead9;
  border-radius: 6px;
  font-size: 12px;
  color: #c2410c;
  border: 1px solid #f3d5b5;
}

/* ── Thinking 指示器 ── */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;

  .thinking-dot {
    width: 8px;
    height: 8px;
    background: #c2410c;
    border-radius: 50%;
    animation: thinking-pulse 1.4s infinite ease-in-out;
  }

  .thinking-text {
    font-size: 13px;
    color: #8a7a6d;
  }
}

@keyframes thinking-pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* ── 工具调用状态卡片 ── */
.tool-calls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 8px 0;
}

.tool-call-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #fdead9;
  border: 1px solid #f3d5b5;
  border-radius: 8px;
  font-size: 12px;
  transition: all 0.3s;

  &.is-loading {
    background: #fdf1e0;
    border-color: #f5dfc0;
  }
}

.tool-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 11px;
  font-weight: bold;

  // loading 状态用琥珀锈，呼应品牌色
  &.tool-loading {
    background: #d97706;
    color: #fff;
    animation: spin 1s linear infinite;
  }

  // done 状态保留语义成功绿，不参与主题染色
  &.tool-done {
    background: #67c23a;
    color: #fff;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tool-name {
  font-weight: 500;
  color: #4a3728;
}

.tool-summary {
  color: #8a7a6d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
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
    background: #fdead9;
    border-color: #c2410c;
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
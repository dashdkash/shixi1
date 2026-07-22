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
            src="/head.svg"
          ></el-avatar>
          <div class="message-bubble assistant-bubble">
            <!-- Agent 执行流程展示 -->
            <div v-if="msg.agentFlow && msg.agentFlow.length" class="agent-flow-container">
              <div class="agent-flow-label">Agent 协作流程</div>
              <div class="agent-flow-badges">
                <div
                  v-for="agent in msg.agentFlow"
                  :key="agent.name"
                  :class="['agent-badge', `agent-${agent.status}`]"
                >
                  <span class="agent-icon">{{ agentIcons[agent.name] || '🤖' }}</span>
                  <span class="agent-name">{{ agentLabels[agent.name] || agent.name }}</span>
                  <span v-if="agent.status === 'running'" class="agent-spinner"></span>
                  <span v-else-if="agent.status === 'success'" class="agent-status-icon">✓</span>
                  <span v-else-if="agent.status === 'failed'" class="agent-status-icon agent-failed">✗</span>
                  <span v-else class="agent-status-icon agent-pending">•</span>
                </div>
              </div>
            </div>

            <!-- thinking 指示器 -->
            <div v-if="msg.thinking" class="thinking-indicator">
              <span class="thinking-dot"></span>
              <span class="thinking-text">
                {{ msg.agentFlow?.some(a => a.status === 'running') ? 'Agent 执行中...' 
                   : (msg.agentFlow?.length && msg.agentFlow.every(a => a.status === 'success' || a.status === 'failed') ? '正在汇总结果...' 
                   : '正在思考...') }}
              </span>
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
        {{ $t("chat.quickActions.single") }}
      </el-button>
      <el-button
        @click="handleQuickDetect('batch')"
        :disabled="agentStore.isLoading"
      >
        {{ $t("chat.quickActions.batch") }}
      </el-button>
      <el-button
        @click="handleQuickDetect('video')"
        :disabled="agentStore.isLoading"
      >
        {{ $t("chat.quickActions.video") }}
      </el-button>
      <el-button
        @click="handleQuickDetect('camera')"
        :disabled="agentStore.isLoading"
      >
        {{ $t("chat.quickActions.camera") }}
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
        accept="image/*,.zip,video/mp4,video/avi,video/quicktime,video/x-msvideo,video/x-matroska"
        style="display: none"
        @change="handleFileSelect"
      />

      <!-- 文本输入框 -->
      <el-input
        v-model="inputText"
        placeholder="输入消息，或拖拽图片/视频/ZIP 到这里..."
        @keyup.enter="sendMessage"
        :disabled="agentStore.isLoading"
      />

      <!-- 发送/停止按钮 -->
      <button
        v-if="!agentStore.isLoading"
        class="send-btn"
        @click="sendMessage"
        :disabled="!inputText.trim() && !selectedFile"
      >
        <el-icon :size="18"><Top /></el-icon>
      </button>
      <el-button v-else type="danger" circle @click="handleStop">
        <span style="font-size:12px">II</span>
      </el-button>
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
import { detectBatch, detectSingle, detectVideo, getVideoStatus, detectZip } from "@/api/detection";
import DetectionResultCard from "@/components/DetectionResultCard.vue";
import { useAgentStore } from "@/stores/agent";
import { useUserStore } from "@/stores/user";
import { renderMarkdown } from "@/utils/markdown";
import request from "@/utils/request";
import { streamChat, TOOL_NAME_MAP } from "@/utils/stream";
import { ElMessage } from "element-plus";
import { Top, Delete, Plus } from "@element-plus/icons-vue";
import { computed, nextTick, onActivated, onMounted, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";

// 显式设置组件名称，确保 keep-alive include 生效
defineOptions({ name: 'ChatPage' });

/** 工具名称中文映射 */
function getToolName(toolName) {
  return TOOL_NAME_MAP[toolName] || toolName;
}

/** Agent 图标映射 */
const agentIcons = {
  detection: '🔍',
  analysis: '📊',
  qa: '💬',
};

/** Agent 中文名称映射 */
const agentLabels = {
  detection: '图像检测',
  analysis: '数据分析',
  qa: '知识问答',
};

// ── Store ──
const agentStore = useAgentStore();
const userStore = useUserStore();
const router = useRouter();
const route = useRoute();

// ── 响应式状态 ──
const inputText = ref("");
const selectedFile = ref(null);
const messageListRef = ref(null);
const fileInputRef = ref(null);

/** 视频文件扩展名集合 */
const VIDEO_EXTENSIONS = new Set(["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"]);

/** 判断文件是否为视频 */
function isVideoFile(file) {
  if (!file) return false;
  if (file.type && file.type.startsWith("video/")) return true;
  const ext = file.name.split(".").pop().toLowerCase();
  return VIDEO_EXTENSIONS.has(ext);
}

// ── 计算属性 ──
const canSend = computed(() => {
  return inputText.value.trim() || selectedFile.value;
});

// ── 快捷检测消息持久化 ──

/**
 * 将快捷检测的用户消息和 AI 回复保存到数据库会话中
 * 如果当前没有会话，自动创建新会话
 */
async function saveQuickDetectToHistory(userContent, assistantContent, taskId) {
  try {
    const res = await request.post("/chat/save-messages", {
      session_id: agentStore.currentSessionId || undefined,
      user_content: userContent,
      assistant_content: assistantContent,
      title: userContent,
      task_id: taskId || undefined,
    });
    if (res && res.session_id) {
      agentStore.currentSessionId = res.session_id;
      agentStore.notifySessionsChanged();
    }
  } catch (err) {
    console.warn("[快捷检测] 保存到历史记录失败:", err);
  }
}

/**
 * 构建数据看板报告生成的提示词
 * 引导 Agent 调用 query_detection_stats + search_knowledge_base 生成报告与防治建议
 */
function buildReportPrompt(days) {
  return `请根据近 ${days} 天的检测数据，为我生成一份完整的《杂草检测报告与防治建议》。

请按以下结构输出：

## 📝 杂草检测报告（近 ${days} 天）

### 一、检测概况
调用 query_detection_stats(days=${days}) 获取数据，包括：
- 检测任务总数、检测图片总数、检测目标总数、平均推理耗时

### 二、杂草种类分布
根据上述工具返回的 class_distribution 数据，分析：
- 各类杂草的检测次数及占比
- 哪些杂草种类出现最频繁，哪些是主要威胁

### 三、趋势分析
分析检测趋势的变化特点，是否存在某段时间检测量突增的情况

### 四、防治建议
调用 search_knowledge_base 搜索知识库中关于上述高频杂草的防治方法，给出：
- 针对主要杂草种类的化学防治方案
- 物理/生物防治建议
- 施药时间与注意事项

请用专业但易懂的语言输出，确保报告具有实际参考价值。`;
}

// ── 方法 ──

/** 发送消息 */
async function sendMessage() {
  if (!canSend.value) return;

  agentStore.setLoading(true);
  const message = inputText.value.trim();
  // ── 关键：在清空之前保存文件引用 ──
  const fileToSend = selectedFile.value;
  const isVideo = isVideoFile(fileToSend);
  const filePreview = fileToSend ? URL.createObjectURL(fileToSend) : null;

  // 添加用户消息到列表
  agentStore.addMessage({
    role: "user",
    content: message,
    // 视频文件用 videoUrl 展示预览，图片文件用 imagePreview
    image: fileToSend && !isVideo ? fileToSend.name : null,
    imagePreview: filePreview && !isVideo ? filePreview : null,
    videoUrl: isVideo ? filePreview : null,
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

  // ── 如果有附件文件，先上传到服务端获取真实路径 ──
  let serverImagePath = null;
  let serverVideoPath = null;
  if (fileToSend) {
    try {
      const formData = new FormData();
      formData.append("file", fileToSend);
      // 不设置 Content-Type，让 axios 自动添加 boundary
      const uploadResult = await request.post("/chat/upload", formData);
      // 根据文件类型决定使用哪个字段
      if (isVideo) {
        serverVideoPath = uploadResult.image_path; // 后端统一返回 image_path 字段
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
    ...(agentStore.currentSessionId ? { session_id: agentStore.currentSessionId } : {}),
  };

  let fullContent = "";

  const stop = streamChat("/api/chat/stream", requestBody, {
    onMessage: (data) => {
      // 调试日志：查看收到的所有 SSE 事件
      console.log("[SSE事件]", data.type, data.type === "tool_end" || data.type === "tool_result" ? data : "");

      if (data.type === "session_id") {
        // 后端返回当前会话 ID，保存到 store
        agentStore.currentSessionId = data.session_id;
        // 通知侧栏刷新会话列表
        agentStore.notifySessionsChanged();
        console.log("[会话ID]", data.session_id);
      } else if (data.type === "thinking") {
        // Agent 正在思考 — 显示 thinking 指示器
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.thinking = true;
        scrollToBottom();
      } else if (data.type === "agent_plan") {
        // Supervisor 路由完成，显示 Agent 执行计划
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.agentFlow = (data.agents || []).map(name => ({ name, status: "pending" }));
        // 保持 thinking=true，让用户知道仍在处理中
        console.log("[Agent计划]", data.agents);
        scrollToBottom();
      } else if (data.type === "agent_start") {
        // 子 Agent 开始执行
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        const badge = lastMsg.agentFlow?.find(a => a.name === data.agent);
        if (badge) badge.status = "running";
        console.log("[Agent启动]", data.agent);
        scrollToBottom();
      } else if (data.type === "agent_end") {
        // 子 Agent 执行完成
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        const badge = lastMsg.agentFlow?.find(a => a.name === data.agent);
        if (badge) badge.status = data.status || "success";
        console.log("[Agent完成]", data.agent, data.status);
        scrollToBottom();
      } else if (data.type === "text_chunk") {
        // 文本流式追加 — 保持 thinking=true，让指示器显示“正在汇总结果...”
        // thinking 会在 onDone 时清除
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        fullContent += data.content;
        agentStore.updateLastAssistantMessage(fullContent);
        scrollToBottom();
      } else if (data.type === "tool_call" || data.type === "tool_start") {
        // 工具开始调用 — 添加到 toolCalls 数组
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        if (!lastMsg.toolCalls) lastMsg.toolCalls = [];
        lastMsg.toolCalls.push({
          tool: data.tool,
          status: "loading",
          input: data.input,
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
          // 支持单图/批量检测（result.detections）和视频检测（result.key_frames / result.annotated_video_url）
          if (result.detections || result.key_frames || result.annotated_video_url) {
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
      // 使用索引替换方式确保响应式更新
      const idx = agentStore.messages.length - 1;
      const lastMsg = agentStore.messages[idx];
      if (lastMsg && lastMsg.role === 'assistant') {
        agentStore.messages[idx] = { ...lastMsg, loading: false, thinking: false };
      }
      agentStore.setLoading(false);
    },
    onError: (err) => {
      const idx = agentStore.messages.length - 1;
      const lastMsg = agentStore.messages[idx];
      if (lastMsg && lastMsg.role === 'assistant') {
        agentStore.messages[idx] = { ...lastMsg, content: `抱歉，处理出错了：${err.message}`, loading: false, thinking: false, error: true };
      }
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
        const aiContent = `检测完成！发现 ${result.total_objects} 个目标。`;
        lastMsg.content = aiContent;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        // 保存到历史记录
        saveQuickDetectToHistory(`[快捷检测] ${file.name}`, aiContent, result.task_id);
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
        const aiContent = `批量检测完成！共 ${totalObjects} 个目标。`;
        lastMsg.content = aiContent;
        lastMsg.loading = false;
        lastMsg.detectionResult = result;
        console.log("[批量检测结果]", result);
        // 保存到历史记录
        const userContent = isZip
          ? `[快捷检测] ZIP: ${files[0].name}`
          : `[快捷检测] ${files.length} 张图片`;
        saveQuickDetectToHistory(userContent, aiContent, result.task_id);
      } catch (err) {
        console.error("[批量检测异常]", err);
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `批量检测失败：${err.message || err}`;
        lastMsg.loading = false;
        lastMsg.error = true;
      }
    };
    input.click();
  } else if (type === "video") {
    // 视频检测
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "video/mp4,video/avi,video/quicktime,video/x-msvideo,video/x-matroska";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      agentStore.addMessage({
        role: "user",
        content: `[快捷检测] 视频: ${file.name}`,
      });

      agentStore.addMessage({
        role: "assistant",
        content: "视频已上传，正在后台检测中，请稍候...",
        loading: true,
      });

      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await detectVideo(formData);
        if (res.task_id) {
          // 轮询视频检测结果
          const result = await pollVideoTask(res.task_id);
          const lastMsg = agentStore.messages[agentStore.messages.length - 1];
          if (result) {
            const aiContent = `视频检测完成！共发现 ${result.total_objects || 0} 个目标，处理了 ${result.processed_frames || 0} 帧。`;
            lastMsg.content = aiContent;
            lastMsg.loading = false;
            lastMsg.detectionResult = result;
            // 保存到历史记录
            saveQuickDetectToHistory(`[快捷检测] 视频: ${file.name}`, aiContent, res.task_id);
          } else {
            const aiContent = "视频检测超时，请稍后在历史记录中查看结果。";
            lastMsg.content = aiContent;
            lastMsg.loading = false;
            saveQuickDetectToHistory(`[快捷检测] 视频: ${file.name}`, aiContent, res.task_id);
          }
        }
      } catch (err) {
        const lastMsg = agentStore.messages[agentStore.messages.length - 1];
        lastMsg.content = `视频检测失败：${err.response?.data?.detail || err.message}`;
        lastMsg.loading = false;
      }
    };
    input.click();
  } else if (type === "camera") {
    // 摄像头检测 - 跳转到检测页面的摄像头 Tab
    router.push({ name: "Detection", query: { tab: "camera" } });
  }
}

/**
 * 轮询视频检测任务（每2秒，最多5分钟）
 */
async function pollVideoTask(taskId) {
  const maxAttempts = 150;
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    try {
      const res = await getVideoStatus(taskId);
      if (res.status === "completed") {
        return res.result || res;
      } else if (res.status === "failed") {
        return null;
      }
    } catch {
      // 继续轮询
    }
  }
  return null;
}

onMounted(async () => {
  // 检查是否从数据看板跳转生成报告
  if (route.query.report === "1") {
    const days = Number(route.query.days) || 30;
    // 清除 query 参数，避免刷新时重复触发
    router.replace({ path: "/chat" });
    // 新建会话，发送报告生成请求
    agentStore.newChat();
    await nextTick();
    inputText.value = buildReportPrompt(days);
    await nextTick();
    sendMessage();
    return;
  }
  // 页面加载时显示欢迎消息（仅当消息为空且无会话时）
  if (agentStore.messages.length === 0 && !agentStore.currentSessionId) {
    agentStore.addMessage({
      role: "assistant",
      content:
        "🌿 你好！我是杂草识别智能助手。\n\n我可以帮你：\n- 📷 识别图片中的杂草种类和数量\n- 📊 提供杂草分布统计分析\n- 💡 给出专业的除草建议\n\n上传一张农田或草坪的照片，我来帮你分析！",
    });
  }
});

// 当从其他页面返回对话页时，确保欢迎消息存在并刷新侧栏
onActivated(() => {
  if (agentStore.messages.length === 0 && !agentStore.currentSessionId) {
    agentStore.addMessage({
      role: "assistant",
      content:
        "🌿 你好！我是杂草识别智能助手。\n\n我可以帮你：\n- 📷 识别图片中的杂草种类和数量\n- 📊 提供杂草分布统计分析\n- 💡 给出专业的除草建议\n\n上传一张农田或草坪的照片，我来帮你分析！",
    });
  }
  // 返回对话页时刷新侧栏会话列表，确保最新会话可见
  if (agentStore.currentSessionId) {
    agentStore.notifySessionsChanged();
  }
  // 滚动到底部，以防 SSE 在 deactivated 期间更新了消息
  scrollToBottom();
});
</script>

<style lang="scss" scoped>
.chat-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  background: transparent;
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
    background: transparent;
    border-color: #e4e7ed;
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
  background: linear-gradient(135deg, #333 0%, #1e1e1e 100%);
  color: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
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
  background: transparent;

  .el-button {
    border-radius: 20px;
    font-size: 13px;
    padding: 6px 16px;
  }
}

.input-area {
  display: flex;
  gap: 10px;
  padding: 14px 20px;
  margin: 12px 20px 16px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.2s;

  &:focus-within {
    box-shadow: 0 6px 28px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.08);
  }

  .el-input {
    flex: 1;

    :deep(.el-input__wrapper) {
      border-radius: 24px;
      box-shadow: none;
      background: #f8f8f8;
    }
  }

  .el-button {
    border-radius: 24px;
    padding: 0 24px;
  }
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #1e1e1e;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  transition: all 0.2s;
  flex-shrink: 0;

  &:hover {
    background: #333;
    transform: scale(1.05);
  }

  &:disabled {
    background: #ccc;
    cursor: not-allowed;
    transform: none;
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
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 12px;
  color: #1e1e1e;
  border: 1px solid #e0e0e0;
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
    background: #1e1e1e;
    border-radius: 50%;
    animation: thinking-pulse 1.4s infinite ease-in-out;
  }

  .thinking-text {
    font-size: 13px;
    color: #909399;
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
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 12px;
  transition: all 0.3s;

  &.is-loading {
    background: #fdf6ec;
    border-color: #faecd8;
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

  &.tool-loading {
    background: #e6a23c;
    color: #fff;
    animation: spin 1s linear infinite;
  }

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
  color: #303133;
}

.tool-summary {
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

/* ── Agent 执行流程胶囊标签 ── */
.agent-flow-container {
  margin-bottom: 12px;
}

.agent-flow-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.agent-flow-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.agent-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.3s ease;
  border: 1.5px solid transparent;

  &.agent-pending {
    background: #f4f4f5;
    color: #909399;
    border-color: #e4e7ed;
  }

  &.agent-running {
    background: #ecf5ff;
    color: #409eff;
    border-color: #b3d8ff;
    animation: agent-pulse 1.5s ease-in-out infinite;
  }

  &.agent-success {
    background: #f0f9eb;
    color: #67c23a;
    border-color: #c2e7b0;
  }

  &.agent-failed {
    background: #fef0f0;
    color: #f56c6c;
    border-color: #fbc4c4;
  }
}

.agent-icon {
  font-size: 14px;
  line-height: 1;
}

.agent-name {
  white-space: nowrap;
}

.agent-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid #b3d8ff;
  border-top-color: #409eff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.agent-status-icon {
  font-size: 12px;
  font-weight: bold;
  line-height: 1;

  &.agent-failed {
    color: #f56c6c;
  }

  &.agent-pending {
    font-size: 16px;
    color: #c0c4cc;
  }
}

@keyframes agent-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
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
    background: #f5f5f5;
    border-color: #1e1e1e;
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

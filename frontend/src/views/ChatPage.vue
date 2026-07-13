<template>
  <div class="chat-container">
    <!-- 聊天消息列表 -->
    <div class="message-list" ref="messageList">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message-item', msg.role]"
      >
        <div class="message-avatar">
          <el-icon v-if="msg.role === 'user'">
            <User />
          </el-icon>
          <el-icon v-else>
            <ChatLineRound />
          </el-icon>
        </div>
        <div class="message-content">
          <div class="message-text">{{ msg.content }}</div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <div class="input-wrapper">
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          class="file-input"
          @change="handleFileSelect"
        />
        <el-button
          type="default"
          class="attach-btn"
          @click="triggerFileInput"
          :disabled="isLoading"
        >
          <el-icon><Paperclip /></el-icon>
        </el-button>
        <el-input
          v-model="inputMessage"
          :placeholder="$t('chat.inputPlaceholder')"
          @keyup.enter="sendMessage"
          :disabled="isLoading"
          class="msg-input"
        />
        <el-button
          type="primary"
          class="send-btn"
          @click="sendMessage"
          :disabled="!inputMessage.trim() || isLoading"
          :loading="isLoading"
        >
          <el-icon><ArrowUp /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { streamChat } from "@/utils/stream";
import {
  ArrowUp,
  ChatLineRound,
  Paperclip,
  User,
} from "@element-plus/icons-vue";
import { nextTick, ref, watch } from "vue";

/** 消息列表 */
const messages = ref([
  {
    role: "assistant",
    content: "",
  },
]);

/** 输入框消息 */
const inputMessage = ref("");

/** 是否正在加载 */
const isLoading = ref(false);

/** 消息列表引用 */
const messageList = ref(null);

/** 文件输入框引用 */
const fileInput = ref(null);

/** 当前语言 */
const currentLang = ref(localStorage.getItem("rsod_lang") || "zh");

/** 监听语言变化 */
watch(
  () => localStorage.getItem("rsod_lang"),
  (newLang) => {
    currentLang.value = newLang || "zh";
  },
);

/** 滚动到底部 */
const scrollToBottom = async () => {
  await nextTick();
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight;
  }
};

/** 触发文件选择 */
const triggerFileInput = () => {
  fileInput.value?.click();
};

/** 处理文件选择 */
const handleFileSelect = (event) => {
  const files = event.target.files;
  if (files && files.length > 0) {
    const file = files[0];
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = e.target?.result;
      inputMessage.value = `${$t("chat.attachedImage")}: ${file.name}`;
    };
    reader.readAsDataURL(file);
  }
  event.target.value = "";
};

/** 发送消息 */
const sendMessage = () => {
  if (!inputMessage.value.trim() || isLoading.value) return;

  const userMessage = inputMessage.value.trim();
  inputMessage.value = "";

  // 添加用户消息
  messages.value.push({
    role: "user",
    content: userMessage,
  });

  // 添加空的助手消息（用于流式填充）
  messages.value.push({
    role: "assistant",
    content: "",
  });

  isLoading.value = true;
  scrollToBottom();

  // 发起流式请求
  const stop = streamChat(
    "/api/chat/stream",
    { message: userMessage, stream: true },
    {
      onMessage: (chunk) => {
        if (typeof chunk === "object" && chunk.content) {
          // 追加内容到最后一条消息
          const lastMsg = messages.value[messages.value.length - 1];
          lastMsg.content += chunk.content;
          scrollToBottom();
        }
      },
      onDone: () => {
        isLoading.value = false;
        scrollToBottom();
      },
      onError: (err) => {
        isLoading.value = false;
        const lastMsg = messages.value[messages.value.length - 1];
        lastMsg.content =
          lastMsg.content || `${$t("chat.error")}: ${err.message}`;
      },
    },
  );

  // 保存停止函数（可选：用于手动中断）
  stop;
};

/** 页面加载时发送欢迎消息 */
const sendWelcomeMessage = async () => {
  const lastMsg = messages.value[messages.value.length - 1];
  if (!lastMsg.content) {
    await nextTick();
    const stop = streamChat(
      "/api/chat/stream",
      { message: "hello", stream: true },
      {
        onMessage: (chunk) => {
          if (typeof chunk === "object" && chunk.content) {
            lastMsg.content += chunk.content;
            scrollToBottom();
          }
        },
        onDone: () => {
          scrollToBottom();
        },
        onError: (err) => {
          lastMsg.content = `${$t("chat.error")}: ${err.message}`;
        },
      },
    );
    stop;
  }
};

sendWelcomeMessage();
</script>

<style lang="scss" scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
  border-radius: 8px;
  overflow: hidden;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
}

.message-item {
  display: flex;
  margin-bottom: 20px;

  &.user {
    flex-direction: row-reverse;

    .message-content {
      background: #409eff;
      color: #fff;
      border-radius: 12px 12px 0 12px;
    }
  }

  &.assistant {
    .message-content {
      background: #f0f0f0;
      color: #303133;
      border-radius: 12px 12px 12px 0;
    }
  }
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin: 0 12px;
  font-size: 20px;

  .user & {
    background: #409eff;
    color: #fff;
  }

  .assistant & {
    background: #67c23a;
    color: #fff;
  }
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.6;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.input-area {
  padding: 16px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 24px;
  border: 1px solid #e4e7ed;

  &:focus-within {
    border-color: #409eff;
    background: #fff;
  }
}

.file-input {
  display: none;
}

.attach-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: #e4e7ed;
    border-color: #e4e7ed;
  }

  .el-icon {
    font-size: 18px;
    color: #606266;
  }
}

.msg-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0;

  :deep(.el-input__wrapper) {
    box-shadow: none;
    border: none;
    background: transparent;
    padding: 0;
  }
}

.send-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;

  &:disabled {
    opacity: 0.5;
  }

  .el-icon {
    font-size: 18px;
  }
}
</style>

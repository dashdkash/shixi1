/**
 * 智能体对话状态管理
 * 管理对话会话列表、当前会话消息等
 */
import { defineStore } from "pinia";
import request from "@/utils/request";

const WELCOME_MESSAGE = {
  role: "assistant",
  content:
    "🌿 你好！我是杂草识别智能助手。\n\n我可以帮你：\n- 📷 识别图片中的杂草种类和数量\n- 📊 提供杂草分布统计分析\n- 💡 给出专业的除草建议\n\n上传一张农田或草坪的照片，我来帮你分析！",
};

export const useAgentStore = defineStore("agent", {
  state: () => ({
    // 当前会话 ID
    currentSessionId: null,
    // 当前会话的消息列表
    messages: [],
    // 会话列表
    sessions: [],
    // 是否正在等待 AI 响应
    isLoading: false,
    // 中断函数（用于取消 SSE 流式请求）
    abortController: null,
    // 会话列表版本号（触发侧栏刷新）
    _sessionVersion: 0,
  }),

  getters: {
    /** 消息数量 */
    messageCount: (state) => state.messages.length,
    /** 是否有会话 */
    hasSession: (state) => state.sessions.length > 0,
  },

  actions: {
    /** 添加一条消息 */
    addMessage(message) {
      this.messages.push(message);
    },

    /** 更新最后一条 AI 消息（用于流式追加） */
    updateLastAssistantMessage(content) {
      const lastMsg = this.messages[this.messages.length - 1];
      if (lastMsg && lastMsg.role === "assistant") {
        const index = this.messages.length - 1;
        this.messages[index] = { ...lastMsg, content };
      }
    },

    /** 设置加载状态 */
    setLoading(loading) {
      this.isLoading = loading;
    },

    /** 中断当前流式请求 */
    abort() {
      if (this.abortController) {
        this.abortController();
        this.abortController = null;
        this.isLoading = false;
      }
    },

    /** 新建对话 */
    newChat() {
      this.currentSessionId = null;
      this.messages = [{ ...WELCOME_MESSAGE }];
      this.abort();
    },

    /** 清除所有状态 */
    clear() {
      this.currentSessionId = null;
      this.messages = [];
      this.sessions = [];
      this.abort();
    },

    /** 加载历史会话 */
    loadSession(sessionId, messages) {
      this.currentSessionId = sessionId;
      this.messages = messages;
    },

    /** 从后端获取会话列表 */
    async fetchSessions() {
      try {
        const res = await request.get("/chat/sessions?page=1&page_size=30");
        if (res && res.data) {
          this.sessions = res.data;
        }
      } catch {
        // 静默处理
      }
    },

    /** 切换到指定会话 */
    async switchSession(sessionId) {
      try {
        const res = await request.get(`/history/chat/${sessionId}`);
        if (res && res.messages) {
          const messages = [];
          for (const m of res.messages) {
            const msg = {
              role: m.role === "ai" ? "assistant" : m.role,
              content: m.content,
            };
            // 解析 tool_result 中的检测结果
            if (m.tool_result) {
              try {
                const toolData = typeof m.tool_result === "string"
                  ? JSON.parse(m.tool_result) : m.tool_result;
                if (toolData.task_id) {
                  try {
                    const detail = await request.get(`/history/detection/${toolData.task_id}`);
                    msg.detectionResult = {
                      task_id: detail.id,
                      total_objects: detail.total_objects,
                      total_inference_time: detail.total_inference_time,
                      total_images: detail.total_images,
                      class_counts: _buildClassCounts(detail.images),
                      annotated_image_url: detail.images?.[0]?.annotated_image_url,
                      // 优先从数据库获取，旧记录回退到 tool_result
                      annotated_video_url: detail.annotated_video_url || toolData.annotated_video_url,
                    };
                  } catch {
                    msg.detectionResult = { task_id: toolData.task_id };
                  }
                }
              } catch {
                // tool_result 解析失败
              }
            }
            messages.push(msg);
          }
          this.currentSessionId = sessionId;
          this.messages = messages;
        }
      } catch {
        // 静默处理
      }
    },

    /** 删除指定会话 */
    async deleteSession(sessionId) {
      try {
        await request.delete(`/chat/sessions/${sessionId}`);
        this.sessions = this.sessions.filter((s) => s.id !== sessionId);
        if (this.currentSessionId === sessionId) {
          this.newChat();
        }
      } catch {
        // 静默处理
      }
    },

    /** 通知侧栏刷新会话列表 */
    notifySessionsChanged() {
      this._sessionVersion = (this._sessionVersion || 0) + 1;
    },
  },
});

/** 从检测结果图片列表构建 class_counts 对象 */
function _buildClassCounts(images) {
  const counts = {};
  if (!Array.isArray(images)) return counts;
  for (const img of images) {
    if (!Array.isArray(img.objects)) continue;
    for (const obj of img.objects) {
      const name = obj.class_name_cn || obj.class_name;
      if (name) counts[name] = (counts[name] || 0) + 1;
    }
  }
  return counts;
}

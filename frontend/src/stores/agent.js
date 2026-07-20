/**
 * 智能体对话状态管理
 * 管理对话会话列表、当前会话消息等
 */
import { defineStore } from "pinia";
import request from "@/utils/request";

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
      this.messages = [
        {
          role: "assistant",
          content:
            "🌿 你好！我是杂草识别智能助手。\n\n我可以帮你：\n- 📷 识别图片中的杂草种类和数量\n- 📊 提供杂草分布统计分析\n- 💡 给出专业的除草建议\n\n上传一张农田或草坪的照片，我来帮你分析！",
        },
      ];
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

    /** 会话列表刷新事件计数器（触发侧栏重新获取） */
    _sessionVersion: 0,

    /** 通知侧栏刷新会话列表 */
    notifySessionsChanged() {
      this._sessionVersion = (this._sessionVersion || 0) + 1;
    },
  },
});

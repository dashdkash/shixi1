/**
 * 智能体对话状态管理
 * 管理对话会话列表、当前会话消息等
 */
import { defineStore } from "pinia";

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
        lastMsg.content = content;
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
      this.messages = [];
      this.abort();
    },

    /** 清除所有状态 */
    clear() {
      this.currentSessionId = null;
      this.messages = [];
      this.sessions = [];
      this.abort();
    },
  },
});

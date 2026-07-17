/**
 * 智能体对话状态管理
 * 管理对话会话列表、当前会话消息等
 */
import { defineStore } from "pinia";

const WELCOME_MESSAGE = {
  role: "assistant",
  content:
  `🌿 你好！我是杂草识别智能助手。

  我可以帮你：

  📷 识别图片中的杂草种类和数量

  📊 提供杂草分布统计分析

  💡 给出专业的除草建议

  上传一张农田或草坪的照片，我来帮你分析！`
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
    async newChat() {
      this.currentSessionId = null;
      this.abort();
      
      this.messages = [
        {
          role: "assistant",
          loading: true,
          content: "",
          thinking: false,
          toolCalls: [],
        }
      ];

      const delay = 200 + Math.random() * 300;
      await new Promise(resolve => setTimeout(resolve, delay));

      this.messages = [
        {
        ...WELCOME_MESSAGE,
        loading: false,
        thinking: false,
        toolCalls: [],
        }
      ];
    },

    /** 清除所有状态 */
    clear() {
      this.currentSessionId = null;
      this.messages = [];
      this.sessions = [];
      this.abort();
    },
    /** 获取会话列表 */
    async fetchSessions() {
      const { listSessionsApi } = await import("@/api/chat");
      const res = await listSessionsApi();
      this.sessions = res.data;
    },

    async switchSession(sessionId) {
      console.log("switch session:", sessionId);

      const { getSessionMessagesApi } = await import("@/api/chat");

      const res = await getSessionMessagesApi(sessionId);
      console.log("res =", res);

      this.currentSessionId = sessionId;
      this.messages = res.messages;
    },
    /** 删除指定会话 */
    async deleteSession(sessionId) {
      const { deleteSessionApi } = await import("@/api/chat");
      await deleteSessionApi(sessionId);
      this.sessions = this.sessions.filter((s) => s.id !== sessionId);
      if (this.currentSessionId === sessionId) {
        this.newChat();
      }
    },
  },
});

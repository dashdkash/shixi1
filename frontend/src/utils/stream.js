/**
 * SSE (Server-Sent Events) 流式处理工具
 * 用于 Day 11 智能体对话的流式渲染
 *
 * 支持的事件类型：
 *   - thinking: Agent 正在思考
 *   - tool_start: 开始调用工具
 *   - tool_end: 工具调用完成
 *   - text_chunk: LLM 回复文本片段
 *   - done: 对话完成
 *   - error: 出错
 */

/**
 * 工具名称中文映射
 */
export const TOOL_NAME_MAP = {
  detect_single_image: "单图检测",
  detect_batch_images: "批量检测",
  detect_zip_images_file: "ZIP 检测",
  detect_video_file: "视频检测",
  search_knowledge_base: "知识库检索",
  query_detection_stats: "统计查询",
  query_detection_history: "历史查询",
  query_user_list: "用户查询",
};

/**
 * 发起 SSE 流式请求
 *
 * @param {string} url - 请求地址（相对路径，会经过 Vite proxy）
 * @param {Object} body - 请求体
 * @param {Object} callbacks - 回调函数
 * @param {Function} callbacks.onMessage - 收到消息片段时的回调
 * @param {Function} callbacks.onDone - 流结束时的回调
 * @param {Function} callbacks.onError - 错误时的回调
 * @returns {Function} stop - 调用此函数可中断连接
 */
export function streamChat(url, body, callbacks) {
  const { onMessage, onDone, onError } = callbacks;

  // 从 localStorage 获取 Token
  const token = localStorage.getItem("rsod_token");

  // 使用 fetch + ReadableStream 实现 SSE
  const controller = new AbortController();

  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        // 401：Token 过期或无效，清除用户信息并跳转登录页
        if (response.status === 401) {
          const { ElMessage } = await import("element-plus");
          const [{ useUserStore }, { default: router }] = await Promise.all([
            import("@/stores/user"),
            import("@/router"),
          ]);
          ElMessage.error("登录已过期，请重新登录");
          useUserStore().logout();
          router.push("/login");
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      // 缓冲区：用于拼接跨 chunk 的不完整 SSE 消息
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // 流结束，处理缓冲区剩余数据
          if (buffer.trim()) {
            processSSEMessage(buffer, onMessage);
          }
          onDone?.();
          break;
        }

        // 解码并追加到缓冲区
        buffer += decoder.decode(value, { stream: true });

        // 按双换行分割完整的 SSE 消息
        const messages = buffer.split("\n\n");

        // 最后一个元素可能是不完整的，保留在缓冲区
        buffer = messages.pop() || "";

        // 处理完整的消息
        for (const msg of messages) {
          if (msg.trim()) {
            const shouldStop = processSSEMessage(msg, onMessage);
            if (shouldStop) {
              onDone?.();
              return;
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError?.(err);
      }
    });

  // 返回中断函数
  return () => controller.abort();
}

/**
 * 处理单条 SSE 消息
 * @param {string} message - 完整的 SSE 消息（可能包含多行 data:）
 * @param {Function} onMessage - 消息回调
 * @returns {boolean} 是否应该停止（遇到 [DONE]）
 */
function processSSEMessage(message, onMessage) {
  // SSE 消息可能包含多行（data:, event:, id: 等），只处理 data: 行
  const lines = message.split("\n");

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = line.slice(6); // 去掉 "data: " 前缀

      if (data === "[DONE]") {
        return true;
      }

      try {
        const parsed = JSON.parse(data);
        onMessage?.(parsed);
      } catch {
        // JSON 解析失败，可能是数据太大或被截断
        // 尝试作为纯文本处理
        console.warn("[SSE] JSON解析失败，数据长度:", data.length);
        onMessage?.({ type: "text_chunk", content: data });
      }
    }
  }

  return false;
}

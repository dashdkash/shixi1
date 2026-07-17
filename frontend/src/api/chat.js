import request from "@/utils/request";

/** 获取会话列表 */
export function listSessionsApi(page = 1, pageSize = 20) {
  return request.get("/chat/sessions", {
    params: { page, page_size: pageSize },
  });
}

/** 删除会话 */
export function deleteSessionApi(sessionId) {
  return request.delete(`/chat/sessions/${sessionId}`);
}

export function getSessionMessagesApi(sessionId) {
    return request({
        url: `/chat/sessions/${sessionId}/messages`,
        method: "get",
    });
}
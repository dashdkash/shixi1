/**
 * 知识库管理 API
 *
 * - GET    /knowledge/documents     获取文档列表
 * - POST   /knowledge/upload        上传文档
 * - DELETE /knowledge/documents/:id 删除文档
 * - POST   /knowledge/search        检索测试
 * - GET    /knowledge/stats         统计信息
 * - POST   /knowledge/build         构建预置文档索引
 */
import request from "@/utils/request";

/** 获取文档列表 */
export function listDocumentsApi() {
  return request.get("/knowledge/documents");
}

/** 上传知识文档 */
export function uploadDocumentApi(formData) {
  return request.post("/knowledge/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

/** 删除知识文档 */
export function deleteDocumentApi(docId) {
  return request.delete(`/knowledge/documents/${docId}`);
}

/** 检索测试 */
export function searchKnowledgeApi(query, topK = 5) {
  return request.post("/knowledge/search", { query, top_k: topK });
}

/** 获取统计信息 */
export function getKnowledgeStatsApi() {
  return request.get("/knowledge/stats");
}

/** 构建预置文档索引 */
export function buildPresetApi() {
  return request.post("/knowledge/build");
}

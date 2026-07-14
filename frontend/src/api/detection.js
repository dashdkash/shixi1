/**
 * 检测相关 API 接口
 *
 * 快捷按钮直接调用这些接口（跳过 LLM），结果渲染在对话中
 */
import request from "@/utils/request";

/**
 * 单图检测
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @returns {Promise} - 检测结果（标注图 + 目标统计）
 */
export function detectSingle(formData) {
  // 不设置 Content-Type，让 axios 自动添加 multipart/form-data + boundary
  return request.post("/detection/single", formData, {
    timeout: 60000,
  });
}

/**
 * 批量检测
 * @param {FormData} formData - 包含多个 files 字段的 FormData
 * @returns {Promise} - 批量检测结果
 */
export function detectBatch(formData) {
  return request.post("/detection/batch", formData, {
    timeout: 120000,
  });
}

/**
 * ZIP 检测
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @returns {Promise} - ZIP 解压后的批量检测结果
 */
export function detectZip(formData) {
  return request.post("/detection/zip", formData, {
    timeout: 180000,
  });
}

/**
 * 获取检测任务状态
 * @param {number} taskId - 检测任务 ID
 * @returns {Promise} - 任务状态和结果
 */
export function getDetectionStatus(taskId) {
  return request.get(`/detection/status/${taskId}`);
}

/**
 * 前端全局错误监控与上报
 *
 * 职责：
 *   - 捕获 JavaScript 运行时错误
 *   - 捕获未处理的 Promise 异常
 *   - 捕获 Vue 组件渲染错误
 *   - 将错误信息上报到后端（用于分析和告警）
 *
 * 使用方式（在 main.js 中）：
 *   import { setupErrorReporting } from "@/utils/errorReporter";
 *   setupErrorReporting(app);
 */

import { ElMessage } from "element-plus";

// ── 错误上报地址 ──────────────────────────────────────
// Day 4 先上报到控制台 + 本地存储，Day 11 接入后端 API
const REPORT_TO_BACKEND = false; // 生产环境设为 true
const REPORT_API = "/api/errors/report";

/**
 * 上报错误信息
 * 当前实现：输出到控制台 + 存入 localStorage
 * 生产环境可发送到后端日志收集服务
 */
function reportError(errorInfo) {
  // 1. 控制台输出（开发调试）
  console.error("[ErrorReporter]", errorInfo);

  // 2. 存入本地存储（最近 50 条错误）
  try {
    const errors = JSON.parse(localStorage.getItem("error_logs") || "[]");
    errors.push({
      ...errorInfo,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
    });
    // 只保留最近 50 条
    if (errors.length > 50) {
      errors.splice(0, errors.length - 50);
    }
    localStorage.setItem("error_logs", JSON.stringify(errors));
  } catch (e) {
    // localStorage 写入失败不影响程序运行
    console.warn("ErrorReporter: localStorage 写入失败", e);
  }

  // 3. 上报到后端（生产环境启用）
  if (REPORT_TO_BACKEND) {
    fetch(REPORT_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(errorInfo),
    }).catch(() => {
      // 上报失败时静默处理，不能因为上报失败而再次报错
    });
  }
}

/**
 * 初始化全局错误监控
 * @param {import('vue').App} app - Vue 应用实例
 */
export function setupErrorReporting(app) {
  // ── 1. Vue 组件错误 ────────────────────────────────
  app.config.errorHandler = (err, instance, info) => {
    reportError({
      type: "vue_error",
      message: err.message,
      stack: err.stack,
      component: info, // 错误发生所在组件的生命周期钩子
    });

    // 给用户友好提示
    ElMessage.error("页面渲染出错，请刷新重试");
  };

  // ── 2. JavaScript 运行时错误 ────────────────────────
  window.onerror = (message, source, lineno, colno, error) => {
    reportError({
      type: "js_error",
      message: message,
      source: source,
      lineno: lineno,
      colno: colno,
      stack: error?.stack,
    });
  };

  // ── 3. 未捕获的 Promise 异常 ────────────────────────
  window.onunhandledrejection = (event) => {
    reportError({
      type: "promise_rejection",
      message: event.reason?.message || String(event.reason),
      stack: event.reason?.stack,
    });

    // 阻止默认的浏览器控制台输出（已自行处理）
    event.preventDefault();
  };

  console.log("[ErrorReporter] 全局错误监控已启用");
}

import { getCurrentLanguage } from "@/locales";
import router from "@/router";
import { useUserStore } from "@/stores/user";
import axios from "axios";
import { ElMessage } from "element-plus";

// ── 创建 Axios 实例 ──────────────────────────────────
const request = axios.create({
  baseURL: "/api", // 配合 Vite proxy，实际请求转发到后端
  timeout: 30000, // 请求超时 30 秒
});

// ── 请求拦截器 ──────────────────────────────────────
request.interceptors.request.use(
  (config) => {
    // 从 Pinia store 获取 Token，自动注入请求头
    const userStore = useUserStore();
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`;
    }
    // 添加语言参数到请求头
    config.headers["Accept-Language"] = getCurrentLanguage();
    // FormData 文件上传时不设置 Content-Type，让 axios 自动添加 multipart/form-data + boundary
    if (!(config.data instanceof FormData)) {
      config.headers["Content-Type"] = "application/json";
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// ── 响应拦截器 ──────────────────────────────────────
request.interceptors.response.use(
  (response) => {
    // 请求成功，直接返回响应数据
    return response.data;
  },
  (error) => {
    const { response } = error;

    if (response) {
      switch (response.status) {
        case 401:
          // Token 过期或无效，清除用户信息并跳转登录页
          ElMessage.error("登录已过期，请重新登录");
          const userStore = useUserStore();
          userStore.logout();
          router.push("/login");
          break;

        case 403:
          ElMessage.error("没有权限执行此操作");
          break;

        case 404:
          ElMessage.error("请求的资源不存在");
          break;

        case 400:
          // 请求参数错误（用户名/邮箱已存在等）
          ElMessage.error(response.data?.message || response.data?.detail || "请求参数错误");
          break;

        case 422:
          // Pydantic 验证错误
          const detail = response.data?.detail;
          if (Array.isArray(detail)) {
            ElMessage.error(detail[0]?.msg || "参数验证失败");
          } else {
            ElMessage.error(detail || "参数验证失败");
          }
          break;

        case 500:
          ElMessage.error("服务器内部错误");
          break;

        default:
          ElMessage.error(
            response.data?.detail || `请求失败 (${response.status})`,
          );
      }
    } else {
      // 网络错误或请求超时
      ElMessage.error("网络连接异常，请检查后端服务是否启动");
    }

    return Promise.reject(error);
  },
);

export default request;

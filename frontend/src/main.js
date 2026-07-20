/**
 * 应用入口文件
 * - 创建 Vue 应用实例
 * - 注册全局插件（Element Plus、Router、Pinia、i18n）
 * - 挂载应用
 */
import { createApp } from "vue";

// Element Plus
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import en from "element-plus/es/locale/lang/en";

// 全局样式（必须在 Element Plus CSS 之后导入，以覆盖主题变量）
import "@/assets/styles/global.scss";

// 核心模块
import App from "./App.vue";
import router from "./router";
import pinia from "./stores";
import i18n from "./locales";

// 错误监控
import { setupErrorReporting } from "@/utils/errorReporter";

const STORAGE_KEY = "rsod_lang";
function getStoredLang() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && ["zh", "en"].includes(stored)) {
    return stored;
  }
  const navigatorLang = navigator.language || navigator.userLanguage;
  if (navigatorLang.startsWith("zh")) {
    return "zh";
  }
  return "en";
}

const currentLang = getStoredLang();
const elementLocale = currentLang === "zh" ? zhCn : en;

// ── 创建并配置应用 ────────────────────────────────────
const app = createApp(App);

// 注册全局错误监控（在其他插件之前注册）
setupErrorReporting(app);

// 注册插件
app.use(pinia); // 状态管理
app.use(router); // 路由
app.use(i18n); // 多语言
app.use(ElementPlus, { locale: elementLocale }); // UI 组件库

app.config.globalProperties.$elementLocales = { zh: zhCn, en };

// 挂载到 DOM
app.mount("#app");

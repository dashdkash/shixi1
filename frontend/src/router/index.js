/**
 * Vue Router 路由配置
 * - 登录/注册页面无需认证
 * - 其他页面需要登录后才能访问
 * - 路由守卫自动检查登录状态
 */
import i18n from "@/locales";
import { useUserStore } from "@/stores/user";
import { createRouter, createWebHistory } from "vue-router";

// ── 路由定义 ────────────────────────────────────────
const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/LoginPage.vue"),
    meta: { titleKey: "login.title", requiresAuth: false },
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("@/views/RegisterPage.vue"),
    meta: { titleKey: "register.title", requiresAuth: false },
  },

  // ── 需要登录的页面（使用 MainLayout 布局） ──────
  {
    path: "/",
    component: () => import("@/components/layout/MainLayout.vue"),
    redirect: "/chat",
    meta: { requiresAuth: true },
    children: [
      {
        path: "chat",
        name: "Chat",
        component: () => import("@/views/ChatPage.vue"),
        meta: {
          titleKey: "page.chat.title",
          icon: "ChatDotRound",
          requiresAdmin: false,
        },
      },
      {
        path: "detection",
        name: "Detection",
        component: () => import("@/views/DetectionPage.vue"),
        meta: {
          titleKey: "page.detection.title",
          icon: "Camera",
          requiresAdmin: false,
        },
      },
      {
        path: "training",
        name: "Training",
        component: () => import("@/views/TrainingPage.vue"),
        meta: {
          titleKey: "page.training.title",
          icon: "Cpu",
          requiresAdmin: true,
        },
      },
      {
        path: "history",
        name: "History",
        component: () => import("@/views/HistoryPage.vue"),
        meta: {
          titleKey: "page.history.title",
          icon: "Clock",
          requiresAdmin: false,
        },
      },
      {
        path: "profile",
        name: "Profile",
        component: () => import("@/views/ProfilePage.vue"),
        meta: {
          titleKey: "page.profile.title",
          icon: "User",
          requiresAdmin: false,
        },
      },
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/DashboardPage.vue"),
        meta: {
          titleKey: "page.dashboard.title",
          icon: "DataAnalysis",
          requiresAdmin: true,
        },
      },
    ],
  },

  // ── 404 页面 ─────────────────────────────────────
  {
    path: "/:pathMatch(.*)*",
    redirect: "/login",
  },
];

// ── 创建路由实例 ──────────────────────────────────────
const router = createRouter({
  history: createWebHistory(),
  routes,
});

// ── 路由守卫 ────────────────────────────────────────
router.beforeEach((to, from, next) => {
  const appTitle = i18n.global.t("app.title");
  const pageTitle = to.meta.titleKey ? i18n.global.t(to.meta.titleKey) : null;
  document.title = pageTitle ? `${pageTitle} - ${appTitle}` : appTitle;

  const userStore = useUserStore();
  const requiresAuth = to.matched.some(
    (record) => record.meta.requiresAuth !== false,
  );

  if (requiresAuth && !userStore.isLoggedIn) {
    next({ path: "/login", query: { redirect: to.fullPath } });
  } else if (
    (to.path === "/login" || to.path === "/register") &&
    userStore.isLoggedIn
  ) {
    next("/");
  } else {
    // 检查是否需要管理员权限
    const requiresAdmin = to.matched.some(
      (record) => record.meta.requiresAdmin === true,
    );
    if (requiresAdmin && !userStore.isSuperuser) {
      next("/chat");
      return;
    }
    next();
  }
});

export default router;

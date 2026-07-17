/**
 * Vue Router 路由配置
 * - 登录/注册页面无需认证
 * - 其他页面需要登录后才能访问
 * - 路由守卫自动检查登录状态和 token 有效性
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

// 路由定义
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterPage.vue'),
    meta: { title: '注册', requiresAuth: false },
  },
  // 需要登录的页面（使用 MainLayout 布局）
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    redirect: '/chat',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/ChatPage.vue'),
        meta: { title: '智能对话', icon: 'ChatDotRound' },
      },
      {
        path: 'detection',
        name: 'Detection',
        component: () => import('@/views/DetectionPage.vue'),
        meta: { title: '检测工作台', icon: 'Camera' },
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('@/views/TrainingPage.vue'),
        meta: { title: '模型训练', icon: 'Cpu' },
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/HistoryPage.vue'),
        meta: { title: '历史记录', icon: 'Clock' },
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardPage.vue'),
        meta: { title: '数据看板', icon: 'DataAnalysis' },
      },
    ],
  },
  // 404 重定向
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title
    ? `${to.meta.title} - RSOD Agent Platform`
    : 'RSOD Agent Platform'

  // 检查是否需要认证
  const userStore = useUserStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth !== false)

  if (requiresAuth && !userStore.isLoggedIn) {
    // 需要登录但未登录或 token 已过期，清除用户信息并跳转到登录页
    if (userStore.token) {
      ElMessage.error('登录已过期，请重新登录')
    }
    userStore.logout()
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if ((to.path === '/login' || to.path === '/register') && userStore.isLoggedIn) {
    // 已登录用户访问登录/注册页，跳转到首页
    next('/')
  } else {
    next()
  }
})

export default router
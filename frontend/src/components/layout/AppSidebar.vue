<template>
  <aside class="app-sidebar" :class="{ collapsed: isCollapsed }">
    <!-- 顶部：Logo + 应用名 -->
    <div class="sidebar-header">
      <img src="/logo.svg" alt="logo" class="sidebar-logo" />
      <span v-show="!isCollapsed" class="sidebar-title">{{ $t("sidebar.appName") }}</span>
    </div>

    <!-- 折叠切换按钮 -->
    <button class="collapse-toggle" @click="toggleCollapse" :title="isCollapsed ? '展开' : '收起'">
      <el-icon :size="16">
        <component :is="isCollapsed ? Expand : Fold" />
      </el-icon>
    </button>

    <!-- 导航菜单 -->
    <nav class="sidebar-nav">
      <router-link
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        :title="isCollapsed ? $t(item.i18nKey) : ''"
      >
        <el-icon :size="20"><component :is="item.icon" /></el-icon>
        <span v-show="!isCollapsed">{{ $t(item.i18nKey) }}</span>
      </router-link>
    </nav>

    <!-- 底部：用户信息 -->
    <div class="sidebar-footer">
      <el-dropdown trigger="click" @command="handleCommand" placement="top-start">
        <div class="user-area">
          <el-avatar :size="isCollapsed ? 32 : 38" :src="userStore.avatar || undefined">
            {{ userStore.username?.charAt(0)?.toUpperCase() }}
          </el-avatar>
          <span v-show="!isCollapsed" class="user-name">{{ userStore.username }}</span>
          <el-icon v-show="!isCollapsed"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>{{ $t("sidebar.profile") }}
            </el-dropdown-item>
            <el-dropdown-item command="lang">
              <el-icon><Operation /></el-icon>{{ currentLang === "zh" ? "English" : "中文" }}
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>{{ $t("sidebar.logout") }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import { useAgentStore } from "@/stores/agent";
import { setLanguage } from "@/locales";
import { useI18n } from "vue-i18n";
import { ElMessageBox } from "element-plus";
import {
  ChatDotRound,
  Camera,
  Cpu,
  DataAnalysis,
  Clock,
  ArrowDown,
  User,
  SwitchButton,
  Operation,
  Collection,
} from "@element-plus/icons-vue";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const agentStore = useAgentStore();
const { locale, t } = useI18n({ useScope: "global" });

const currentLang = ref(locale.value);
const isCollapsed = ref(false);

/** 侧边栏菜单配置（训练仅管理员可见） */
const allMenuItems = [
  { path: "/detection", i18nKey: "sidebar.detection", icon: Camera },
  { path: "/training", i18nKey: "sidebar.training", icon: Cpu, adminOnly: true },
  { path: "/dashboard", i18nKey: "sidebar.dashboard", icon: DataAnalysis },
  { path: "/knowledge", i18nKey: "sidebar.knowledge", icon: Collection },
  { path: "/history", i18nKey: "sidebar.history", icon: Clock },
];

const menuItems = computed(() => {
  if (userStore.isSuperuser) return allMenuItems;
  return allMenuItems.filter((item) => !item.adminOnly);
});

/** 判断当前路由是否匹配 */
function isActive(path) {
  return route.path.startsWith(path);
}

// ── 历史对话 ──
const sessions = ref([]);
const historyCollapsed = ref(false);
const currentPage = ref(1);
const hasMore = ref(false);
const loadingMore = ref(false);

async function fetchSessions(page = 1) {
  try {
    const res = await request.get(`/chat/sessions?page=${page}&page_size=30`);
    if (res && res.data) {
      if (page === 1) {
        sessions.value = res.data;
      } else {
        sessions.value.push(...res.data);
      }
      hasMore.value = sessions.value.length < res.total;
      currentPage.value = page;
    }
  } catch {
    // 静默处理
  }
}

function loadMore() {
  if (loadingMore.value) return;
  loadingMore.value = true;
  fetchSessions(currentPage.value + 1).finally(() => {
    loadingMore.value = false;
  });
}

function handleScroll() {
  // 可扩展为滚动到底部自动加载
}

/** 新建会话 */
function handleNewChat() {
  agentStore.newChat();
  router.push("/chat");
}

/** 选择历史会话 */
async function handleSelectSession(session) {
  // 如果点击的是当前正在查看的会话，不重新加载消息
  // keep-alive 已保持 ChatPage 存活，内存中的流式状态（agentFlow、toolCalls 等）
  // 比 DB 加载的更完整，重新加载会丢失这些中间状态
  if (session.id === agentStore.currentSessionId) {
    router.push("/chat");
    return;
  }

  try {
    const res = await request.get(`/history/chat/${session.id}`);
    if (res && res.messages) {
      const messages = [];
      for (const m of res.messages) {
        const msg = {
          role: m.role === "ai" ? "assistant" : m.role,
          content: m.content,
          loading: false,  // DB 加载的消息已完成，不显示加载指示器
        };
        // 解析 tool_result 中的 task_id，重建检测结果卡片
        if (m.tool_result) {
          try {
            const toolData = typeof m.tool_result === "string"
              ? JSON.parse(m.tool_result)
              : m.tool_result;
            if (toolData.task_id) {
              // 获取检测任务详情，丰富卡片数据
              try {
                const detail = await request.get(`/history/detection/${toolData.task_id}`);
                msg.detectionResult = {
                  task_id: detail.id,
                  total_objects: detail.total_objects,
                  total_inference_time: detail.total_inference_time,
                  total_images: detail.total_images,
                  class_counts: buildClassCounts(detail.images),
                  annotated_image_url: detail.images?.[0]?.annotated_image_url,
                };
              } catch {
                // 降级：仅使用 task_id 显示标注图
                msg.detectionResult = { task_id: toolData.task_id };
              }
            }
          } catch {
            // tool_result 解析失败，忽略
          }
        }
        messages.push(msg);
      }
      agentStore.loadSession(session.id, messages);
      router.push("/chat");
    }
  } catch {
    // 静默处理
  }
}

/** 从检测结果图片列表构建 class_counts 对象 */
function buildClassCounts(images) {
  const counts = {};
  if (!Array.isArray(images)) return counts;
  for (const img of images) {
    if (!Array.isArray(img.objects)) continue;
    for (const obj of img.objects) {
      const name = obj.class_name_cn || obj.class_name;
      if (name) counts[name] = (counts[name] || 0) + 1;
    }
  }
  return counts;
}

/** 删除会话 */
async function handleDeleteSession(session) {
  try {
    await ElMessageBox.confirm("确定删除此对话？", "提示", {
      type: "warning",
    });
    await request.delete(`/chat/sessions/${session.id}`);
    sessions.value = sessions.value.filter((s) => s.id !== session.id);
    if (agentStore.currentSessionId === session.id) {
      agentStore.newChat();
    }
  } catch {
    // 取消或失败
  }
}

/** 处理用户菜单 */
function handleCommand(command) {
  switch (command) {
    case "profile":
      router.push("/profile");
      break;
    case "lang":
      const newLang = currentLang.value === "zh" ? "en" : "zh";
      setLanguage(newLang);
      currentLang.value = newLang;
      break;
    case "logout":
      ElMessageBox.confirm("确定要退出登录吗？", "提示", {
        type: "warning",
      })
        .then(() => {
          userStore.logout();
          agentStore.clear();
          router.push("/login");
        })
        .catch(() => {});
      break;
  }
}
</script>

<style lang="scss" scoped>
.app-sidebar {
  width: 220px;
  height: 100%;
  background: #f0e9dd;
  display: flex;
  flex-direction: column;
  color: #555;
  flex-shrink: 0;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;

  &.collapsed {
    width: 64px;

    .sidebar-header {
      justify-content: center;
      padding: 16px 8px;
    }

    .sidebar-logo {
      width: 36px;
    }

    .sidebar-nav {
      padding: 8px 6px;
    }

    .nav-item {
      justify-content: center;
      padding: 0;
      gap: 0;
    }

    .sidebar-footer {
      padding: 10px 6px;
    }

    .user-area {
      justify-content: center;
      padding: 8px;
    }
  }
}

/* ── 顶部 Logo ── */
.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  min-height: 64px;
}

.sidebar-logo {
  width: 40px;
  height: auto;
  border-radius: 6px;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  letter-spacing: 1px;
  white-space: nowrap;
}

/* ── 折叠按钮 ── */
.collapse-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 36px;
  margin: 4px 0;
  background: transparent;
  border: none;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 0;

  &:hover {
    background: rgba(0, 0, 0, 0.06);
    color: #333;
  }
}

/* ── 导航菜单 ── */
.sidebar-nav {
  flex: 1;
  padding: 8px 10px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  padding: 0 12px;
  border-radius: 8px;
  color: #666;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;

  &:hover {
    background: rgba(0, 0, 0, 0.06);
    color: #333;
  }

  &.active {
    background: rgba(0, 0, 0, 0.1);
    color: #1e1e1e;
    font-weight: 500;
  }
}

/* ── 底部用户 ── */
.sidebar-footer {
  padding: 12px 14px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.user-area {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s;
  overflow: hidden;

  &:hover {
    background: rgba(0, 0, 0, 0.06);
  }

  .user-name {
    flex: 1;
    font-size: 14px;
    font-weight: 600;
    color: #333;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>

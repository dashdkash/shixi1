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
import { ref, computed } from "vue";
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
  Expand,
  Fold,
  Reading,
} from "@element-plus/icons-vue";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const agentStore = useAgentStore();
const { locale, t } = useI18n({ useScope: "global" });

const currentLang = ref(locale.value);
const isCollapsed = ref(false);

/** 侧边栏菜单配置 */
const allMenuItems = [
  { path: "/chat", i18nKey: "sidebar.chat", icon: ChatDotRound },
  { path: "/detection", i18nKey: "sidebar.detection", icon: Camera },
  { path: "/training", i18nKey: "sidebar.training", icon: Cpu, adminOnly: true },
  { path: "/dashboard", i18nKey: "sidebar.dashboard", icon: DataAnalysis, adminOnly: true },
  { path: "/knowledge", i18nKey: "sidebar.knowledge", icon: Reading, adminOnly: true },
  { path: "/history", i18nKey: "sidebar.history", icon: Clock },
];

/** 根据角色过滤菜单项 */
const menuItems = computed(() => {
  if (userStore.isSuperuser) return allMenuItems;
  return allMenuItems.filter(item => !item.adminOnly);
});

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value;
}

/** 判断当前路由是否匹配 */
function isActive(path) {
  return route.path.startsWith(path);
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

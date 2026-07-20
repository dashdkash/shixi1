<template>
  <aside class="app-sidebar" :class="{ 'is-collapsed': isCollapsed }">
    <el-menu
      :default-active="activeMenu"
      :router="true"
      :collapse="isCollapsed"
      :collapse-transition="false"
      background-color="#3b2a1f"
      text-color="#cbb79c"
      active-text-color="#ea7c2c"
    >
      <el-menu-item
        v-for="item in visibleMenuItems"
        :key="item.path"
        :index="item.path"
      >
        <el-icon>
          <component :is="item.icon" />
        </el-icon>
        <span>{{ $t(item.i18nKey) }}</span>
      </el-menu-item>
    </el-menu>

    <!-- ── 折叠/展开切换按钮 ── -->
    <button
      class="collapse-toggle"
      type="button"
      :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
      @click="toggleCollapse"
    >
      <el-icon :size="16">
        <component :is="isCollapsed ? Expand : Fold" />
      </el-icon>
    </button>
  </aside>
</template>

<script setup>
import { isAdmin } from "@/utils/auth";
import { useUserStore } from "@/stores/user";
import {
  Camera,
  ChatDotRound,
  Clock,
  Collection,
  Cpu,
  DataAnalysis,
  Expand,
  Fold,
} from "@element-plus/icons-vue";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const userStore = useUserStore();

/** 折叠状态（持久化到 localStorage，刷新页面后保持） */
const STORAGE_KEY = "sidebar-collapsed";
const isCollapsed = ref(localStorage.getItem(STORAGE_KEY) === "true");

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value;
}

watch(isCollapsed, (val) => {
  localStorage.setItem(STORAGE_KEY, String(val));
});

/** 当前激活的菜单项 */
const activeMenu = computed(() => {
  return "/" + route.path.split("/")[1];
});

/** 侧边栏菜单配置 */
const allMenuItems = [
  {
    path: "/chat",
    i18nKey: "sidebar.chat",
    icon: ChatDotRound,
    requiresAdmin: false,
  },
  {
    path: "/knowledge",
    i18nKey: "sidebar.knowledge",
    icon: Collection,
    requiresAdmin: false,
  },
  {
    path: "/detection",
    i18nKey: "sidebar.detection",
    icon: Camera,
    requiresAdmin: false,
  },
  {
    path: "/training",
    i18nKey: "sidebar.training",
    icon: Cpu,
    requiresAdmin: true,
  },
  {
    path: "/history",
    i18nKey: "sidebar.history",
    icon: Clock,
    requiresAdmin: false,
  },
  {
    path: "/dashboard",
    i18nKey: "sidebar.dashboard",
    icon: DataAnalysis,
    requiresAdmin: true,
  },
];

/** 根据用户角色过滤菜单 */
const visibleMenuItems = computed(() => {
  if (isAdmin(userStore.user)) {
    return allMenuItems;
  }
  return allMenuItems.filter((item) => !item.requiresAdmin);
});
</script>

<style lang="scss" scoped>
.app-sidebar {
  position: relative;
  width: $sidebar-width;
  height: 100%;
  background: $sidebar-bg;
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
  // 宽度变化时平滑过渡，这是"滑入滑出"观感的关键
  transition: width 0.25s ease;

  &.is-collapsed {
    width: 64px;
  }

  .el-menu {
    border-right: none;
    height: 100%;
  }

  .el-menu-item {
    height: 50px;
    line-height: 50px;

    &.is-active {
      background-color: rgba(234, 124, 44, 0.15) !important;
    }

    &:hover {
      background-color: rgba(255, 255, 255, 0.05) !important;
    }
  }
}

.collapse-toggle {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #cbb79c;
  cursor: pointer;
  transition: background 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #fff;
  }

  &:focus-visible {
    outline: 2px solid #ea7c2c;
    outline-offset: 2px;
  }
}
</style>
<template>
  <aside class="app-sidebar">
    <el-menu
      :default-active="activeMenu"
      :router="true"
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409eff"
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
  </aside>
</template>

<script setup>
import { isAdmin } from "@/utils/auth";
import { useUserStore } from "@/stores/user";
import {
  Camera,
  ChatDotRound,
  Clock,
  Cpu,
  DataAnalysis,
} from "@element-plus/icons-vue";
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const userStore = useUserStore();

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
  width: $sidebar-width;
  height: 100%;
  background: $sidebar-bg;
  overflow-y: auto;

  .el-menu {
    border-right: none;
    height: 100%;
  }

  .el-menu-item {
    height: 50px;
    line-height: 50px;

    &.is-active {
      background-color: rgba(64, 158, 255, 0.15) !important;
    }

    &:hover {
      background-color: rgba(255, 255, 255, 0.05) !important;
    }
  }
}
</style>

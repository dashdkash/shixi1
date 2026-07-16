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
        v-for="item in menuItems"
        :key="item.path"
        :index="item.path"
      >
        <el-icon>
          <component :is="item.icon" />
        </el-icon>
        <span>{{ item.title }}</span>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup>
import {
  Camera,
  ChatDotRound,
  Clock,
  Cpu,
  DataAnalysis,
} from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

/** 当前激活的菜单项 */
const activeMenu = computed(() => {
  return '/' + route.path.split('/')[1]
})

/** 侧边栏菜单配置 */
const menuItems = [
  { path: '/chat', title: '智能对话', icon: ChatDotRound },
  { path: '/detection', title: '检测工作台', icon: Camera },
  { path: '/training', title: '模型训练', icon: Cpu },
  { path: '/history', title: '历史记录', icon: Clock },
  { path: '/dashboard', title: '数据看板', icon: DataAnalysis },
]
</script>

<style lang="scss" scoped>
.app-sidebar {
  width: $sidebar-width;
  height: 100%;
  background: $sidebar-bg;
  overflow-y: auto;

  :deep(.el-menu) {
    border-right: none;
    height: 100%;
  }

  :deep(.el-menu-item) {
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
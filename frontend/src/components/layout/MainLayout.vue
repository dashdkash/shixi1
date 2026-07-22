<template>
  <div class="main-layout">
    <AppSidebar />

    <!-- 页面内容区 -->
    <main class="layout-content">
      <router-view v-slot="{ Component }">
        <keep-alive :include="['ChatPage']">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import AppSidebar from "./AppSidebar.vue";
</script>

<style lang="scss" scoped>
.main-layout {
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden;
}

.layout-content {
  flex: 1;
  background: #fdf8f0;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  /* 非全高页面使用 padding */
  > :deep(*) {
    min-height: 0;
  }
}

/* 聊天页和知识库页面自己处理内边距和滚动 */
:deep(.chat-page-layout),
:deep(.knowledge-page) {
  height: 100%;
  overflow-y: auto;
}

:deep(.knowledge-page) {
  padding: $spacing-lg;
}

/* 其他页面默认带 padding */
:deep(.detection-page),
:deep(.training-page),
:deep(.history-page),
:deep(.dashboard-page),
:deep(.profile-page) {
  padding: $spacing-lg;
  height: 100%;
  overflow-y: auto;
}
</style>

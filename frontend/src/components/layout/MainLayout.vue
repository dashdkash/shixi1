<template>
  <div class="main-layout">
    <AppSidebar />

    <!-- 页面内容区 -->
    <main class="layout-content">
      <router-view />
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
  overflow-y: auto;
  padding: $spacing-lg;
}
</style>

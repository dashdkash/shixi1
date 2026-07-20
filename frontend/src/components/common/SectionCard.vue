<template>
  <el-card shadow="never" class="section-card" :body-class="bodyClass">
    <template v-if="title || $slots.header" #header>
      <div class="section-card-header">
        <div class="section-card-title">
          <slot name="header">{{ title }}</slot>
        </div>
        <div v-if="$slots.extra" class="section-card-extra">
          <slot name="extra" />
        </div>
      </div>
    </template>
    <div class="section-card-content">
      <slot />
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  title: { type: String, default: "" },
  bodyClass: { type: String, default: "" },
});
</script>

<style lang="scss" scoped>
.section-card {
  margin-bottom: $spacing-lg;
  border-radius: $border-radius-md;
  border: 1px solid #ebeef5;
}

.section-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-card-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
}

.section-card-content {
  :deep(.el-table) {
    border-radius: $border-radius-md;
  }
}
</style>

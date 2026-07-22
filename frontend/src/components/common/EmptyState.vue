<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon">🌿</slot>
    </div>
    <div class="empty-title">{{ title }}</div>
    <div v-if="description" class="empty-description">{{ description }}</div>
    <slot />
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
});
</script>

<style lang="scss" scoped>
.empty-state {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 8px;
  text-align: center;
  color: #909399;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.empty-description {
  margin-top: 8px;
  max-width: 360px;
  color: #909399;
}
.empty-action {
  margin-top: 20px;
}
</style>

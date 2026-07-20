<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon">🌿</slot>
    </div>
    <div class="empty-title">{{ title }}</div>
    <div class="empty-description">{{ description }}</div>
    <slot />
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "" },
});
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-xl $spacing-lg;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: $spacing-md;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: $spacing-xs;
}

.empty-description {
  font-size: 13px;
  color: $text-secondary;
  max-width: 320px;
  line-height: 1.6;
}

.empty-action {
  margin-top: $spacing-md;
}
</style>

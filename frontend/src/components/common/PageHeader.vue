<template>
  <div class="page-header">
    <div class="page-header-left">
      <h1 class="page-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.extra" class="page-actions">
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
});
</script>

<style lang="scss" scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: $spacing-lg;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: $text-primary;
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: $text-secondary;
  margin-top: $spacing-xs;
}
</style>

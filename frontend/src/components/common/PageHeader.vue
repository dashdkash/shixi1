<template>
  <div class="page-header">
    <div class="page-header-left">
      <div class="page-header-title">
        <slot name="icon" />
        <h1 class="page-title">{{ title }}</h1>
      </div>
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
  subtitle: { type: String, default: '' },
});
</script>

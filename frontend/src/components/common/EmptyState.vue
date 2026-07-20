<template>
  <div class="empty-state">

    <div class="empty-icon">
      <slot name="icon">
        🌿
      </slot>
    </div>

    <div class="empty-title">
      {{ title }}
    </div>

    <div class="empty-description">
      {{ description }}
    </div>

    <slot />

    <div
      v-if="$slots.action"
      class="empty-action"
    >
      <slot name="action" />
    </div>

  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },

  description: {
    type: String,
    default: "",
  },
});
</script>
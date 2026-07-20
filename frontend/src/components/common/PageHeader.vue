<template>
  <div class="page-header">
    <div class="page-header-left">
      <h1 class="page-title">{{ title }}</h1>

      <p v-if="subtitle" class="page-subtitle">
        {{ subtitle }}
      </p>
    </div>

    <div
        v-if="$slots.extra"
        class="page-actions"
        >
        <slot name="extra" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: "",
  },
});
</script>

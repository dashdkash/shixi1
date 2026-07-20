<template>
  <el-card shadow="never" class="stats-card">
    <div class="stats-header">

      <div
        v-if="icon"
        class="stats-icon"
      >
        <el-icon :size="22">
          <component :is="icon" />
        </el-icon>
      </div>

      <div class="stats-label">
        {{ title }}
      </div>

    </div>

    <div class="stats-value">

      <slot name="value">

        {{ value }}

        <span
          v-if="unit"
          class="unit"
        >
          {{ unit }}
        </span>

      </slot>

    </div>

    <div
      v-if="growth !== null"
      class="stats-growth"
      :class="growthClass"
    >
      {{ growthText }}
    </div>
  </el-card>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  title: {
    type: String,
    required: true,
  },

  value: {
    type: [String, Number],
    required: true,
  },

  icon: {
    type: Object,
    default: null,
  },

  unit: {
    type: String,
    default: "",
  },

  growth: {
    type: Number,
    default: null,
  },

  iconColor: {
    type: String,
    default: "var(--primary-color)",
  },

  iconBackground: {
    type: String,
    default: "rgba(76,175,80,.12)",
  },

  inverse: {
    type: Boolean,
    default: false,
  },
});

const growthClass = computed(() => {
  if (props.growth === null || props.growth === undefined || props.growth === 0) {
    return "growth-flat";
  }

  if (props.inverse) {
    return props.growth < 0 ? "growth-up" : "growth-down";
  }

  return props.growth > 0 ? "growth-up" : "growth-down";
});

const growthText = computed(() => {
  if (props.growth === null || props.growth === undefined) {
    return "";
  }

  if (props.growth === 0) {
    return "No Change"; // or "持平"
  }

  if (props.growth > 0) {
    return `↑ +${props.growth}%`;
  }

  return `↓ ${props.growth}%`;
});
</script>
<template>
  <el-card shadow="never" class="stats-card">
    <div class="stats-header">
      <div v-if="icon" class="stats-icon">
        <template v-if="typeof icon === 'string'">{{ icon }}</template>
        <el-icon v-else :size="22"><component :is="icon" /></el-icon>
      </div>
      <div class="stats-label">{{ title }}</div>
    </div>
    <div class="stats-value">
      <slot name="value">
        {{ value }}
        <span v-if="unit" class="unit">{{ unit }}</span>
      </slot>
    </div>
    <div v-if="growth !== null" class="stats-growth" :class="growthClass">
      {{ growthText }}
    </div>
  </el-card>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  icon: { type: [Object, String], default: null },
  unit: { type: String, default: "" },
  growth: { type: Number, default: null },
  iconColor: { type: String, default: "#1e1e1e" },
  iconBackground: { type: String, default: "rgba(30,30,30,.08)" },
  inverse: { type: Boolean, default: false },
});

const growthClass = computed(() => {
  if (props.growth === null || props.growth === undefined || props.growth === 0) return "growth-flat";
  if (props.inverse) return props.growth < 0 ? "growth-up" : "growth-down";
  return props.growth > 0 ? "growth-up" : "growth-down";
});

const growthText = computed(() => {
  if (props.growth === null || props.growth === undefined) return "";
  if (props.growth === 0) return "持平";
  return props.growth > 0 ? `↑ +${props.growth}%` : `↓ ${props.growth}%`;
});
</script>

<style lang="scss" scoped>
.stats-card {
  border-radius: $border-radius-md;
  border: 1px solid #ebeef5;
}

.stats-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
}

.stats-icon {
  width: 40px;
  height: 40px;
  border-radius: $border-radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
  background: v-bind(iconBackground);
  color: v-bind(iconColor);
}

.stats-label {
  font-size: 13px;
  color: $text-secondary;
}

.stats-value {
  font-size: 28px;
  font-weight: 700;
  color: $text-primary;
  line-height: 1.2;

  .unit {
    font-size: 14px;
    font-weight: 400;
    color: $text-secondary;
    margin-left: 4px;
  }
}

.stats-growth {
  font-size: 12px;
  margin-top: $spacing-sm;

  &.growth-up { color: $success-color; }
  &.growth-down { color: $danger-color; }
  &.growth-flat { color: $text-secondary; }
}
</style>

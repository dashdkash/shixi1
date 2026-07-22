<template>
  <el-card shadow="never" class="stats-card">
    <div class="stats-header">
      <div v-if="icon" class="stats-icon" :style="{ background: iconBackground, color: iconColor }">
        <el-icon :size="22"><component :is="icon" /></el-icon>
      </div>
      <div class="stats-label">{{ title }}</div>
    </div>
    <div class="stats-value">
      <slot name="value">
        {{ value }}
        <span v-if="unit" class="unit">{{ unit }}</span>
      </slot>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  icon: { type: Object, default: null },
  unit: { type: String, default: '' },
  iconColor: { type: String, default: '#1e1e1e' },
  iconBackground: { type: String, default: 'rgba(30,30,30,.08)' },
});
</script>

<style lang="scss" scoped>
.stats-card {
  border: none;
  cursor: default;
  transition: all 0.25s ease;
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}
.stats-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.stats-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stats-label {
  font-size: 14px;
  color: #909399;
}
.stats-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  color: #1e1e1e;
}
.unit {
  font-size: 14px;
  color: #909399;
}
</style>

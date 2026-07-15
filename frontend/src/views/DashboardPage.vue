<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2>{{ $t("page.dashboard.title") }}</h2>
      <p>{{ $t("page.dashboard.description") }}</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon detection-icon">
          <el-icon><Search /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ statsStore.total_detections }}</div>
          <div class="stat-label">{{ $t("profile.totalDetections") }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon image-icon">
          <el-icon><Picture /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ statsStore.total_images }}</div>
          <div class="stat-label">{{ $t("profile.totalImages") }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon object-icon">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ statsStore.total_objects }}</div>
          <div class="stat-label">{{ $t("profile.totalObjects") }}</div>
        </div>
      </div>
    </div>

    <div class="quick-actions">
      <h3>{{ $t("page.dashboard.quickActions") }}</h3>
      <div class="action-grid">
        <div class="action-card" @click="goToChat">
          <el-icon class="action-icon"><ChatDotRound /></el-icon>
          <span>{{ $t("page.dashboard.chat") }}</span>
        </div>
        <div class="action-card" @click="goToDetection">
          <el-icon class="action-icon"><Search /></el-icon>
          <span>{{ $t("page.dashboard.detection") }}</span>
        </div>
        <div class="action-card" @click="goToHistory">
          <el-icon class="action-icon"><Clock /></el-icon>
          <span>{{ $t("page.dashboard.history") }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useStatsStore } from "@/stores/stats";
import {
  ChatDotRound,
  DataAnalysis,
  Picture,
  Search,
} from "@element-plus/icons-vue";
import { onMounted, watch } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const statsStore = useStatsStore();

const goToChat = () => {
  router.push("/chat");
};

const goToDetection = () => {
  router.push("/detection");
};

const goToHistory = () => {
  router.push("/history");
};

onMounted(() => {
  statsStore.fetchStats();
});

watch(
  () => [
    statsStore.total_detections,
    statsStore.total_images,
    statsStore.total_objects,
  ],
  () => {},
  { deep: true },
);

defineExpose({
  refreshStats: () => statsStore.fetchStats(),
});
</script>

<style lang="scss" scoped>
.dashboard-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 32px;

  h2 {
    font-size: 24px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: #909399;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;

  &.detection-icon {
    background: linear-gradient(135deg, #ecf5ff 0%, #dbeafe 100%);
    color: #409eff;
  }

  &.image-icon {
    background: linear-gradient(135deg, #f0f9eb 0%, #dcfce7 100%);
    color: #67c23a;
  }

  &.object-icon {
    background: linear-gradient(135deg, #fff7e6 0%, #ffedd5 100%);
    color: #e6a23c;
  }
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.quick-actions {
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 16px;
  }
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 20px rgba(64, 158, 255, 0.15);
  }

  .action-icon {
    font-size: 32px;
    color: #409eff;
  }

  span {
    font-size: 14px;
    color: #303133;
    font-weight: 500;
  }
}
</style>

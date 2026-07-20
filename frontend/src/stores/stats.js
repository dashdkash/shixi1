import { getProfileApi } from "@/api/auth";
import { defineStore } from "pinia";

export const useStatsStore = defineStore("stats", {
  state: () => ({
    total_detections: 0,
    total_images: 0,
    total_objects: 0,
  }),

  actions: {
    async fetchStats() {
      try {
        const profile = await getProfileApi();
        this.total_detections = profile.total_detections || 0;
        this.total_images = profile.total_images_detected || 0;
        this.total_objects = profile.total_objects_found || 0;
      } catch (e) {
        console.error("获取检测统计失败", e);
      }
    },

    incrementDetections() {
      this.total_detections++;
    },

    incrementImages(count = 1) {
      this.total_images += count;
    },

    incrementObjects(count = 1) {
      this.total_objects += count;
    },
  },
});
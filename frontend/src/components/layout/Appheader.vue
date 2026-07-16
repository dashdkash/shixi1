<template>
  <header class="app-header">
    <!-- 左侧：Logo + 平台名称 -->
    <div class="header-left">
      <img src="/logo.svg" alt="logo" class="header-logo" />
      <span class="header-title">{{ $t("app.title") }}</span>
    </div>

    <!-- 右侧：语言选择 + 用户信息 + 退出按钮 -->
    <div class="header-right">
      <el-select
        v-model="currentLang"
        class="lang-select"
        @change="handleLangChange"
        size="small"
      >
        <el-option :label="$t('lang.zh')" value="zh" />
        <el-option :label="$t('lang.en')" value="en" />
      </el-select>

      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-info">
          <el-avatar :size="32" :src="userStore.avatar || undefined">
            {{ userStore.username?.charAt(0)?.toUpperCase() }}
          </el-avatar>
          <span class="username">{{ userStore.username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>{{ $t("header.profile") }}
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>{{ $t("header.logout") }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
import { ref, watch } from "vue";
import { useUserStore } from "@/stores/user";
import { ArrowDown, SwitchButton, User } from "@element-plus/icons-vue";
import { ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { setLanguage } from "@/locales";

const router = useRouter();
const userStore = useUserStore();
const { locale, t } = useI18n({ useScope: "global" });

const currentLang = ref(locale.value);

watch(
  () => locale.value,
  (newLang) => {
    currentLang.value = newLang;
  }
);

function handleLangChange(lang) {
  setLanguage(lang);
}

/** 处理下拉菜单命令 */
function handleCommand(command) {
  switch (command) {
    case "profile":
      router.push("/profile");
      break;
    case "logout":
      ElMessageBox.confirm(t("header.confirmLogout"), t("common.warning"), {
        confirmButtonText: t("common.confirm"),
        cancelButtonText: t("common.cancel"),
        type: "warning",
      })
        .then(() => {
          userStore.logout();
          router.push("/login");
        })
        .catch(() => {});
      break;
  }
}
</script>

<style lang="scss" scoped>
.app-header {
  height: $header-height;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $spacing-lg;
  box-shadow: $shadow-sm;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.header-logo {
  width: 28px;
  height: 28px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
}

.header-right {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.lang-select {
  width: 80px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: $border-radius-sm;
  transition: background 0.2s;

  &:hover {
    background: #f5f7fa;
  }
}

.username {
  font-size: 14px;
  color: $text-primary;
}
</style>

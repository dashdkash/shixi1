<template>
  <div class="reset-page">
    <div class="reset-container">
      <!-- 左侧：重置密码表单 -->
      <div class="reset-card">
        <div class="reset-header">
          <h2>{{ $t("resetPassword.title") }}</h2>
          <p class="reset-desc">{{ $t("resetPassword.description") }}</p>
        </div>

        <div v-if="!hasParams" class="no-params">
          <el-alert title="链接无效" type="error" :closable="false" show-icon>
            <p>{{ $t("resetPassword.invalidLink") }}</p>
            <router-link to="/forgot-password" class="forgot-link">
              {{ $t("resetPassword.goToForgot") }}
            </router-link>
          </el-alert>
        </div>

        <div v-else>
          <el-form
            :model="resetForm"
            ref="formRef"
            :rules="resetRules"
            label-width="0"
            size="large"
            @submit.prevent="handleReset"
          >
            <el-form-item prop="newPassword">
              <el-input
                v-model="resetForm.newPassword"
                type="password"
                :placeholder="$t('resetPassword.newPassword')"
                prefix-icon="Lock"
                show-password
              />
            </el-form-item>

            <el-form-item prop="confirmPassword">
              <el-input
                v-model="resetForm.confirmPassword"
                type="password"
                :placeholder="$t('resetPassword.confirmPassword')"
                prefix-icon="Lock"
                show-password
                @keyup.enter="handleReset"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                class="reset-btn"
                :loading="loading"
                @click="handleReset"
              >
                {{ $t("resetPassword.submit") }}
              </el-button>
            </el-form-item>
          </el-form>

          <div v-if="resetSuccess" class="success-info">
            <el-alert
              title="密码重置成功"
              type="success"
              :closable="false"
              show-icon
            >
              <p>{{ $t("resetPassword.success") }}</p>
              <router-link to="/login" class="login-link">
                {{ $t("resetPassword.goToLogin") }}
              </router-link>
            </el-alert>
          </div>
        </div>

        <div class="reset-footer">
          <router-link to="/login">{{
            $t("resetPassword.backToLogin")
          }}</router-link>
          <span>|</span>
          <router-link to="/forgot-password">{{
            $t("resetPassword.forgotPassword")
          }}</router-link>
        </div>
      </div>

      <!-- 右侧：品牌展示 -->
      <div class="brand-panel">
        <div class="brand-content">
          <img src="/logo.svg" alt="logo" class="brand-logo" />
          <h1 class="brand-title">智慧农业</h1>
          <p class="brand-subtitle">农田杂草智能检测平台</p>
        </div>
        <el-select
          v-model="currentLang"
          class="lang-select"
          @change="handleLangChange"
          size="small"
        >
          <el-option :label="$t('lang.zh')" value="zh" />
          <el-option :label="$t('lang.en')" value="en" />
        </el-select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { resetPasswordApi } from "@/api/auth";
import { setLanguage } from "@/locales";
import { ElMessage } from "element-plus";
import { reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";

const { t, locale } = useI18n({ useScope: "global" });
const route = useRoute();

const currentLang = ref(locale.value);

watch(
  () => locale.value,
  (newLang) => {
    currentLang.value = newLang;
  },
);

function handleLangChange(lang) {
  setLanguage(lang);
}

const formRef = ref(null);
const loading = ref(false);
const resetSuccess = ref(false);

const email = route.query.email || "";
const code = route.query.code || "";
const hasParams = email && code;

const resetForm = reactive({
  newPassword: "",
  confirmPassword: "",
});

const resetRules = {
  newPassword: [
    {
      required: true,
      message: t("validation.required", { field: t("common.password") }),
      trigger: "blur",
    },
    {
      min: 6,
      message: t("validation.minLength", {
        field: t("common.password"),
        min: 6,
      }),
      trigger: "blur",
    },
  ],
  confirmPassword: [
    {
      required: true,
      message: t("validation.required", {
        field: t("resetPassword.confirmPassword"),
      }),
      trigger: "blur",
    },
  ],
};

async function handleReset() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  if (resetForm.newPassword !== resetForm.confirmPassword) {
    ElMessage.error(t("resetPassword.notMatch"));
    return;
  }

  loading.value = true;
  try {
    await resetPasswordApi({
      email: email,
      code: code,
      new_password: resetForm.newPassword,
    });
    resetSuccess.value = true;
    ElMessage.success(t("resetPassword.success"));
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t("resetPassword.error"));
  } finally {
    loading.value = false;
  }
}
</script>

<style lang="scss" scoped>
.reset-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: url("/grass.jpg") no-repeat center center;
  background-size: cover;
  position: relative;

  /* 暗色遮罩 */
  &::before {
    content: "";
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 0;
  }
}

.reset-container {
  position: relative;
  z-index: 1;
  display: flex;
  width: 880px;
  min-height: 480px;
  border-radius: $border-radius-lg;
  overflow: hidden;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
}

/* ── 左侧重置表单 ── */
.reset-card {
  width: 420px;
  padding: 48px 40px 36px;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.reset-header {
  margin-bottom: 36px;

  h2 {
    font-size: 22px;
    font-weight: 700;
    color: #1e1e1e;
    font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
    letter-spacing: 4px;
    margin-bottom: 8px;
  }

  .reset-desc {
    font-size: 13px;
    color: #909399;
  }
}

.no-params {
  .forgot-link {
    display: inline-block;
    margin-top: 8px;
    color: #1e1e1e;
    font-weight: 500;
  }
}

.reset-btn {
  width: 100%;
  background: #1e1e1e;
  border-color: #1e1e1e;
  color: #fff;

  &:hover,
  &:focus {
    background: #333;
    border-color: #333;
    color: #fff;
  }
}

.success-info {
  margin-top: 20px;

  .login-link {
    display: inline-block;
    margin-top: 8px;
    color: #1e1e1e;
    font-weight: 500;
  }
}

.reset-footer {
  text-align: center;
  font-size: 13px;
  color: #909399;
  margin-top: auto;
  padding-top: 16px;

  a {
    color: #1e1e1e;

    &:hover {
      text-decoration: underline;
    }
  }

  span {
    margin: 0 8px;
    color: #c0c4cc;
  }
}

/* ── 右侧品牌展示 ── */
.brand-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(4px);

  .lang-select {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 80px;
  }
}

.brand-content {
  text-align: center;
  color: #fff;
  margin-top: -60px;
}

.brand-logo {
  width: 120px;
  height: auto;
  margin-bottom: 32px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 50%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}

.brand-title {
  font-size: 36px;
  font-weight: 700;
  letter-spacing: 6px;
  margin-bottom: 12px;
  font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.brand-subtitle {
  font-size: 22px;
  font-weight: 400;
  letter-spacing: 4px;
  opacity: 0.95;
  font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}
</style>
<template>
  <div class="reset-password-page">
    <div class="reset-card">
      <div class="reset-header">
        <el-select
          v-model="currentLang"
          class="lang-select"
          @change="handleLangChange"
          size="small"
        >
          <el-option :label="$t('lang.zh')" value="zh" />
          <el-option :label="$t('lang.en')" value="en" />
        </el-select>
        <img src="/logo.svg" alt="logo" class="reset-logo" />
        <h2>{{ $t("resetPassword.title") }}</h2>
        <p>{{ $t("resetPassword.description") }}</p>
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
// ── 杂草识别智能体 · 主题色（与登录/注册页一致） ──
// 强调色（聚焦态·土壤棕） #8b5e34

:global(html),
:global(body) {
  height: 100%;
  margin: 0;
}

.reset-password-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #346b3d;
  background-image:
    radial-gradient(
      circle at center,
      rgba(224, 240, 195, 0.65) 30%,
      rgba(52, 107, 61, 0.75) 100%
    ),
    url("/bg.png");
  background-size: cover, 650px auto;
  background-position: center, center;
  background-repeat: no-repeat, no-repeat;
}

.reset-card {
  width: 420px;
  padding: 40px;
  background: #fbfbf4;
  border-radius: $border-radius-lg;
  box-shadow: 0 8px 32px rgba(61, 107, 36, 0.18);
  position: relative;
  border: 1px solid rgba(164, 201, 105, 0.35);

  // ── 淡入动画 ──
  opacity: 0;
  animation: fade-in-card 0.4s ease-out 0.2s forwards;
}

@keyframes fade-in-card {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.reset-header {
  text-align: center;
  margin-bottom: 32px;

  .lang-select {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 80px;
  }

  .reset-logo {
    width: 48px;
    height: 48px;
    margin-bottom: 12px;
  }

  h2 {
    font-size: 22px;
    color: #3d6b24;
    margin-bottom: 8px;
  }

  p {
    font-size: 13px;
    color: $text-secondary;
  }
}

// el-alert 的 error/success 语义色保持默认，不参与主题染色
// 仅将链接色调整为品牌绿，使其与页面其余部分呼应
.no-params {
  .forgot-link {
    display: inline-block;
    margin-top: 8px;
    color: #3d6b24;
    font-weight: 500;

    &:hover {
      text-decoration: underline;
    }
  }
}

.success-info {
  margin-top: 20px;

  .login-link {
    display: inline-block;
    margin-top: 8px;
    color: #3d6b24;
    font-weight: 500;

    &:hover {
      text-decoration: underline;
    }
  }
}

// 输入框聚焦时使用土壤棕作为强调色，失焦后恢复默认
:deep(.el-input__wrapper) {
  transition: box-shadow 0.15s ease;
  box-shadow: 0 0 0 1px transparent inset;

  &.is-focus {
    box-shadow: 0 0 0 1px #8b5e34 inset !important;
  }
}

.reset-btn {
  width: 100%;
  background-color: #a4c969;
  border-color: #a4c969;

  &:hover,
  &:focus-visible {
    background-color: #8fb355;
    border-color: #8fb355;
  }

  &:focus-visible {
    outline: 2px solid #8b5e34;
    outline-offset: 2px;
  }
}

.reset-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: $text-secondary;

  a {
    color: #3d6b24;

    &:hover {
      text-decoration: underline;
    }
  }

  span {
    margin: 0 8px;
    color: $text-secondary;
  }
}
</style>
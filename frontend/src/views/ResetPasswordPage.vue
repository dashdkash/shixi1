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
.reset-password-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.reset-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  position: relative;
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
    color: #303133;
    margin-bottom: 8px;
  }

  p {
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
  margin-top: 24px;
  font-size: 14px;
  color: #909399;

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
</style>
<template>
  <div class="forgot-password-page">
    <div class="forgot-card">
      <div class="forgot-header">
        <el-select
          v-model="currentLang"
          class="lang-select"
          @change="handleLangChange"
          size="small"
        >
          <el-option :label="$t('lang.zh')" value="zh" />
          <el-option :label="$t('lang.en')" value="en" />
        </el-select>
        <img src="/logo.svg" alt="logo" class="forgot-logo" />
        <h2>{{ $t("forgotPassword.title") }}</h2>
        <p>{{ $t("forgotPassword.description") }}</p>
      </div>

      <div v-if="step === 1">
        <el-form
          :model="forgotForm"
          ref="formRef"
          :rules="forgotRules"
          label-width="0"
          size="large"
          @submit.prevent="handleForgot"
        >
          <el-form-item prop="email">
            <el-input
              v-model="forgotForm.email"
              :placeholder="$t('forgotPassword.email')"
              prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              class="forgot-btn"
              :loading="loading"
              @click="handleForgot"
            >
              {{ $t("forgotPassword.sendCode") }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <div v-else-if="step === 2">
        <div class="code-section">
          <el-alert type="info" :closable="false" show-icon>
            <p>{{ $t("forgotPassword.codeSent") }}</p>
          </el-alert>

          <el-form
            :model="codeForm"
            ref="codeFormRef"
            :rules="codeRules"
            label-width="0"
            size="large"
            @submit.prevent="handleVerifyCode"
          >
            <el-form-item prop="code">
              <el-input
                v-model="codeForm.code"
                :placeholder="$t('forgotPassword.enterCode')"
                prefix-icon="Key"
                maxlength="6"
              />
            </el-form-item>

            <div class="code-actions">
              <el-button
                type="text"
                class="resend-btn"
                :disabled="countdown > 0"
                @click="handleResendCode"
              >
                {{
                  countdown > 0
                    ? $t("forgotPassword.resendCountdown", {
                        seconds: countdown,
                      })
                    : $t("forgotPassword.resend")
                }}
              </el-button>
            </div>

            <el-form-item>
              <el-button
                type="primary"
                class="verify-btn"
                :loading="verifying"
                @click="handleVerifyCode"
              >
                {{ $t("forgotPassword.verify") }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-button type="text" class="back-btn" @click="step = 1">
            {{ $t("forgotPassword.changeEmail") }}
          </el-button>
        </div>
      </div>

      <div class="forgot-footer">
        <router-link to="/login">{{
          $t("forgotPassword.backToLogin")
        }}</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { forgotPasswordApi, verifyResetCodeApi } from "@/api/auth";
import { setLanguage } from "@/locales";
import { ElMessage } from "element-plus";
import { reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";

const { t, locale } = useI18n({ useScope: "global" });
const router = useRouter();

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
const codeFormRef = ref(null);
const loading = ref(false);
const verifying = ref(false);
const step = ref(1);
const countdown = ref(0);

const forgotForm = reactive({
  email: "",
});

const codeForm = reactive({
  code: "",
});

const forgotRules = {
  email: [
    {
      required: true,
      message: t("validation.required", { field: t("common.email") }),
      trigger: "blur",
    },
    {
      type: "email",
      message: t("validation.email"),
      trigger: "blur",
    },
  ],
};

const codeRules = {
  code: [
    {
      required: true,
      message: t("forgotPassword.codeRequired"),
      trigger: "blur",
    },
    {
      pattern: /^\d{6}$/,
      message: t("forgotPassword.codeFormat"),
      trigger: "blur",
    },
  ],
};

let timer = null;

function startCountdown() {
  countdown.value = 60;
  timer = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      clearInterval(timer);
      timer = null;
    }
  }, 1000);
}

async function handleForgot() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    const response = await forgotPasswordApi({ email: forgotForm.email });
    if (response.email_exists) {
      ElMessage.success(response.message);
      step.value = 2;
      startCountdown();
    } else {
      ElMessage.warning(response.message);
    }
  } catch {
    ElMessage.error(t("forgotPassword.error"));
  } finally {
    loading.value = false;
  }
}

async function handleResendCode() {
  loading.value = true;
  try {
    const response = await forgotPasswordApi({ email: forgotForm.email });
    if (response.email_exists) {
      ElMessage.success(t("forgotPassword.codeResent"));
      startCountdown();
    } else {
      ElMessage.warning(response.message);
    }
  } catch {
    ElMessage.error(t("forgotPassword.error"));
  } finally {
    loading.value = false;
  }
}

async function handleVerifyCode() {
  const valid = await codeFormRef.value.validate().catch(() => false);
  if (!valid) return;

  verifying.value = true;
  try {
    const response = await verifyResetCodeApi({
      email: forgotForm.email,
      code: codeForm.code,
    });
    if (response.valid) {
      ElMessage.success(response.message);
      router.push({
        path: "/reset-password",
        query: {
          email: forgotForm.email,
          code: codeForm.code,
        },
      });
    }
  } catch (error) {
    ElMessage.error(
      error.response?.data?.detail || t("forgotPassword.invalidCode"),
    );
  } finally {
    verifying.value = false;
  }
}
</script>

<style lang="scss" scoped>
// ── 杂草识别智能体 · 主题色（与登录/注册/重置密码页一致） ──
// 强调色（聚焦态·土壤棕） #8b5e34

:global(html),
:global(body) {
  height: 100%;
  margin: 0;
}

.forgot-password-page {
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

.forgot-card {
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

.forgot-header {
  text-align: center;
  margin-bottom: 32px;

  .lang-select {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 80px;
  }

  .forgot-logo {
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

// el-alert 的 info 语义色保持默认，不参与主题染色
.code-section {
  .el-alert {
    margin-bottom: 20px;
  }
}

.code-actions {
  text-align: right;
  margin-bottom: 16px;

  .resend-btn {
    font-size: 13px;
    padding: 0;
    color: #3d6b24;

    &.is-disabled {
      color: $text-secondary;
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

.forgot-btn,
.verify-btn {
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

.back-btn {
  display: block;
  width: 100%;
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: #3d6b24;
}

.forgot-footer {
  text-align: center;
  margin-top: 24px;

  a {
    color: #3d6b24;
    font-size: 14px;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
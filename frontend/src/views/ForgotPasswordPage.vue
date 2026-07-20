<template>
  <div class="forgot-page">
    <div class="forgot-container">
      <!-- 左侧：找回密码表单 -->
      <div class="forgot-card">
        <div class="forgot-header">
          <h2>{{ $t("forgotPassword.title") }}</h2>
          <p class="forgot-desc">{{ $t("forgotPassword.description") }}</p>
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
                  class="forgot-btn"
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
      if (response.code) {
        ElMessage.success({
          message: `${response.message}，验证码：${response.code}`,
          duration: 10000,
        });
      } else {
        ElMessage.success(response.message);
      }
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
.forgot-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: url("/grass.jpg") no-repeat center center;
  background-size: cover;
  position: relative;

  &::before {
    content: "";
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 0;
  }
}

.forgot-container {
  position: relative;
  z-index: 1;
  display: flex;
  width: 880px;
  min-height: 520px;
  border-radius: $border-radius-lg;
  overflow: hidden;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
}

/* ── 左侧找回密码表单 ── */
.forgot-card {
  width: 420px;
  padding: 48px 40px 36px;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.forgot-header {
  margin-bottom: 28px;

  h2 {
    font-size: 22px;
    font-weight: 700;
    color: #1e1e1e;
    font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
    letter-spacing: 4px;
  }

  .forgot-desc {
    font-size: 13px;
    color: $text-secondary;
    margin-top: 8px;
  }
}

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
  }
}

.forgot-btn {
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

.back-btn {
  display: block;
  width: 100%;
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
}

.forgot-footer {
  text-align: center;
  font-size: 13px;
  color: $text-secondary;
  margin-top: auto;
  padding-top: 16px;

  a {
    color: $primary-color;
    margin-left: 4px;

    &:hover {
      text-decoration: underline;
    }
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

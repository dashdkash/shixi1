<template>
  <div class="register-page">
    <div class="register-container">
      <!-- 左侧：注册表单 -->
      <div class="register-card">
        <div class="register-header">
          <h2>{{ $t("register.title") }}</h2>
        </div>

        <el-form
          ref="formRef"
          :model="registerForm"
          :rules="registerRules"
          label-width="0"
          size="large"
          @submit.prevent="handleRegister"
        >
          <el-form-item prop="username">
            <el-input
              v-model="registerForm.username"
              :placeholder="$t('register.username')"
              prefix-icon="User"
            />
          </el-form-item>

          <el-form-item prop="email">
            <el-input
              v-model="registerForm.email"
              :placeholder="$t('register.email')"
              prefix-icon="Message"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              :placeholder="$t('register.password')"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              :placeholder="$t('register.confirmPassword')"
              prefix-icon="Lock"
              show-password
              @keyup.enter="handleRegister"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              class="register-btn"
              :loading="loading"
              @click="handleRegister"
            >
              {{ $t("register.registerBtn") }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="register-footer">
          <span>{{ $t("register.hasAccount") }}</span>
          <router-link to="/login">{{ $t("register.login") }}</router-link>
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
import { registerApi } from "@/api/auth";
import { setLanguage } from "@/locales";
import { ElMessage } from "element-plus";
import { reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";

const { t, locale } = useI18n({ useScope: "global" });
const router = useRouter();
const formRef = ref(null);
const loading = ref(false);

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

/** 注册表单数据 */
const registerForm = reactive({
  username: "",
  email: "",
  password: "",
  confirmPassword: "",
});

/** 确认密码验证器 */
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error(t("validation.passwordMatch")));
  } else {
    callback();
  }
};

/** 表单验证规则 */
const registerRules = {
  username: [
    {
      required: true,
      message: t("validation.required", { field: t("common.username") }),
      trigger: "blur",
    },
    {
      min: 3,
      max: 50,
      message: t("validation.usernameLength"),
      trigger: "blur",
    },
  ],
  email: [
    {
      required: true,
      message: t("validation.required", { field: t("common.email") }),
      trigger: "blur",
    },
    { type: "email", message: t("validation.email"), trigger: "blur" },
  ],
  password: [
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
        field: t("register.confirmPassword"),
      }),
      trigger: "blur",
    },
    { validator: validateConfirmPassword, trigger: "blur" },
  ],
};

/** 处理注册 */
async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await registerApi({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
    });

    ElMessage.success(t("register.success"));
    router.push("/login");
  } catch {
    // 错误已在 Axios 拦截器中统一处理
  } finally {
    loading.value = false;
  }
}
</script>

<style lang="scss" scoped>
.register-page {
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

.register-container {
  position: relative;
  z-index: 1;
  display: flex;
  width: 880px;
  min-height: 520px;
  border-radius: $border-radius-lg;
  overflow: hidden;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
}

/* ── 左侧注册表单 ── */
.register-card {
  width: 420px;
  padding: 48px 40px 36px;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.register-header {
  margin-bottom: 28px;

  h2 {
    font-size: 22px;
    font-weight: 700;
    color: #1e1e1e;
    font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
    letter-spacing: 4px;
  }
}

.register-btn {
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

.register-footer {
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

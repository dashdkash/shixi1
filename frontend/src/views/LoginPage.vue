<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <el-select
          v-model="currentLang"
          class="lang-select"
          @change="handleLangChange"
          size="small"
        >
          <el-option :label="$t('lang.zh')" value="zh" />
          <el-option :label="$t('lang.en')" value="en" />
        </el-select>
        <img src="/logo.svg" alt="logo" class="login-logo" />
        <h2>{{ $t("app.title") }}</h2>
        <p>{{ $t("app.description") }}</p>
      </div>

      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="loginRules"
        label-width="0"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            :placeholder="$t('login.username')"
            prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            :placeholder="$t('login.password')"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            {{ $t("login.loginBtn") }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <router-link to="/forgot-password" class="forgot-link">
          {{ $t("forgotPassword.title") }}
        </router-link>
        <span>{{ $t("login.noAccount") }}</span>
        <router-link to="/register">{{ $t("login.register") }}</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { setLanguage } from "@/locales";
import { useUserStore } from "@/stores/user";
import { ElMessage } from "element-plus";
import { reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";

const { t, locale } = useI18n({ useScope: "global" });
const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

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

/** 登录表单数据 */
const loginForm = reactive({
  username: "",
  password: "",
});

/** 表单验证规则 */
const loginRules = {
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
};

/** 处理登录 */
async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await userStore.login({
      username: loginForm.username,
      password: loginForm.password,
    });

    ElMessage.success(t("login.success"));

    const redirect = route.query.redirect || "/";
    router.push(redirect);
  } catch {
    // 错误已在 Axios 拦截器中统一处理
  } finally {
    loading.value = false;
  }
}
</script>

<style lang="scss" scoped>
// ── 杂草识别智能体 · 主题色 ──────────────────────
// 背景基调（浅豆绿）  #e0f0c3
// 卡片表面（暖白）    #fbfbf4
// 主按钮（叶绿）      #a4c969
// 按钮悬停（深叶绿）  #8fb355
// 标题/强调（深林绿）  #3d6b24
// 强调色（十字准星橙，取自 mascot 图标）  #d85a30

// 确保 html/body 撑满视口高度，避免 100vh 页面下半部分留白
:global(html),
:global(body) {
  height: 100%;
  margin: 0;
}

.login-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
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

.login-card {
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

.login-header {
  text-align: center;
  margin-bottom: 32px;

  .lang-select {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 80px;
  }

  .login-logo {
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

// 输入框聚焦时使用土壤棕作为强调色（与注册页一致），失焦后恢复默认
:deep(.el-input__wrapper) {
  transition: box-shadow 0.15s ease;
  box-shadow: 0 0 0 1px transparent inset;

  &.is-focus {
    box-shadow: 0 0 0 1px #8b5e34 inset !important;
  }
}

.login-btn {
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

.login-footer {
  text-align: center;
  font-size: 13px;
  color: $text-secondary;
  margin-top: 16px;

  .forgot-link {
    float: left;
    margin-left: 0;
    color: #3d6b24;
  }

  a {
    color: #3d6b24;
    margin-left: 4px;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
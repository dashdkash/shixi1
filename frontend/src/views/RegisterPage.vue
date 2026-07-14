<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-header">
        <el-select
          v-model="currentLang"
          class="lang-select"
          @change="handleLangChange"
          size="small"
        >
          <el-option :label="$t('lang.zh')" value="zh" />
          <el-option :label="$t('lang.en')" value="en" />
        </el-select>
        <img src="/logo.svg" alt="logo" class="register-logo" />
        <h2>{{ $t("register.title") }}</h2>
        <p>{{ $t("register.description") }}</p>
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-lg;
  position: relative;
}

.register-header {
  text-align: center;
  margin-bottom: 32px;

  .lang-select {
    position: absolute;
    top: 16px;
    right: 16px;
    width: 80px;
  }

  .register-logo {
    width: 48px;
    height: 48px;
    margin-bottom: 12px;
  }

  h2 {
    font-size: 22px;
    color: $text-primary;
    margin-bottom: 8px;
  }

  p {
    font-size: 13px;
    color: $text-secondary;
  }
}

.register-btn {
  width: 100%;
}

.register-footer {
  text-align: center;
  font-size: 13px;
  color: $text-secondary;

  a {
    color: $primary-color;
    margin-left: 4px;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>

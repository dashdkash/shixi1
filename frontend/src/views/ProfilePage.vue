<template>
  <div class="profile-container">
    <div class="profile-card">
      <div class="profile-header">
        <div class="avatar-section">
          <div class="avatar-wrapper" @click="triggerAvatarUpload">
            <el-avatar :size="120" :src="userStore.avatar || undefined">
              {{ userStore.username?.charAt(0)?.toUpperCase() }}
            </el-avatar>
            <div class="avatar-edit">
              <el-icon><Camera /></el-icon>
            </div>
          </div>
          <input
            ref="avatarInput"
            type="file"
            accept="image/*"
            class="avatar-input"
            @change="handleAvatarUpload"
          />
          <h2 class="username">{{ userStore.username }}</h2>
          <p class="email">{{ userStore.user?.email }}</p>
        </div>
      </div>

      <div class="profile-content">
        <div class="section">
          <h3 class="section-title">
            <el-icon><User /></el-icon>
            {{ $t("profile.userInfo") }}
          </h3>
          <div class="info-grid">
            <div class="info-item">
              <label>{{ $t("profile.username") }}</label>
              <span>{{ userStore.username }}</span>
            </div>
            <div class="info-item">
              <label>{{ $t("profile.email") }}</label>
              <span>{{ userStore.user?.email || "-" }}</span>
            </div>
            <div class="info-item">
              <label>{{ $t("profile.status") }}</label>
              <span :class="userStore.user?.is_active ? 'active' : 'inactive'">
                {{
                  userStore.user?.is_active
                    ? $t("profile.active")
                    : $t("profile.inactive")
                }}
              </span>
            </div>
            <div class="info-item">
              <label>{{ $t("profile.role") }}</label>
              <span>{{
                userStore.isSuperuser
                  ? $t("profile.admin")
                  : $t("profile.normal")
              }}</span>
            </div>
            <div class="info-item">
              <label>{{ $t("profile.createdAt") }}</label>
              <span>{{ formatDate(userStore.user?.created_at) }}</span>
            </div>
            <div class="info-item">
              <label>{{ $t("profile.lastLogin") }}</label>
              <span>{{ formatDate(userStore.user?.last_login_at) }}</span>
            </div>
          </div>
        </div>

        <div class="section">
          <h3 class="section-title">
            <el-icon><Lock /></el-icon>
            {{ $t("profile.changePassword") }}
          </h3>
          <el-form
            :model="passwordForm"
            ref="passwordFormRef"
            label-width="120px"
          >
            <el-form-item label="旧密码" prop="oldPassword">
              <el-input
                v-model="passwordForm.oldPassword"
                :type="showOldPassword ? 'text' : 'password'"
                placeholder="请输入旧密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="passwordForm.newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                placeholder="请输入新密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="passwordForm.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                placeholder="请再次输入新密码"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="handleChangePassword"
                :loading="isChanging"
              >
                {{ $t("profile.savePassword") }}
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useUserStore } from "@/stores/user";
import request from "@/utils/request";
import { Camera, Lock, User } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const userStore = useUserStore();

const avatarInput = ref(null);
const passwordFormRef = ref(null);
const isChanging = ref(false);

const showOldPassword = ref(false);
const showNewPassword = ref(false);
const showConfirmPassword = ref(false);

const passwordForm = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const formatDate = (dateStr) => {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("zh-CN");
};

const triggerAvatarUpload = () => {
  avatarInput.value?.click();
};

const handleAvatarUpload = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await request.post("/api/auth/avatar", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    if (response.avatar) {
      userStore.user.avatar = response.avatar;
      localStorage.setItem("rsod_user", JSON.stringify(userStore.user));
      ElMessage.success("头像上传成功");
    }
  } catch (error) {
    ElMessage.error("头像上传失败");
  }

  event.target.value = "";
};

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return;

  await passwordFormRef.value.validate((valid) => {
    if (!valid) return;

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      ElMessage.error("两次输入的密码不一致");
      return;
    }

    if (passwordForm.newPassword.length < 6) {
      ElMessage.error("新密码长度至少6位");
      return;
    }

    isChanging.value = true;

    request
      .post("/api/auth/change-password", {
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword,
      })
      .then(() => {
        ElMessage.success("密码修改成功");
        passwordForm.oldPassword = "";
        passwordForm.newPassword = "";
        passwordForm.confirmPassword = "";
      })
      .catch((error) => {
        ElMessage.error(error.response?.data?.detail || "密码修改失败");
      })
      .finally(() => {
        isChanging.value = false;
      });
  });
};
</script>

<style lang="scss" scoped>
.profile-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
}

.profile-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.profile-header {
  background: linear-gradient(135deg, #5b8def 0%, #409eff 100%);
  padding: 40px;
  text-align: center;
}

.avatar-section {
  position: relative;
}

.avatar-wrapper {
  position: relative;
  display: inline-block;
  cursor: pointer;

  :deep(.el-avatar) {
    border: 4px solid rgba(255, 255, 255, 0.5);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transition: transform 0.2s;

    &:hover {
      transform: scale(1.05);
    }
  }
}

.avatar-edit {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 36px;
  height: 36px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  opacity: 0;
  transition: opacity 0.2s;

  .avatar-wrapper:hover & {
    opacity: 1;
  }
}

.avatar-input {
  display: none;
}

.username {
  margin-top: 16px;
  font-size: 24px;
  font-weight: 600;
  color: #fff;
}

.email {
  margin-top: 8px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.profile-content {
  padding: 32px;
}

.section {
  margin-bottom: 32px;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 20px;
  padding-left: 8px;
  border-left: 4px solid #409eff;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;

  label {
    font-size: 12px;
    color: #909399;
    margin-bottom: 4px;
  }

  span {
    font-size: 14px;
    color: #303133;
    font-weight: 500;

    &.active {
      color: #67c23a;
    }

    &.inactive {
      color: #f56c6c;
    }
  }
}

:deep(.el-form) {
  .el-form-item {
    margin-bottom: 20px;
  }

  .el-input__wrapper {
    border-radius: 8px;
  }
}
</style>

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
              <label>{{ $t("profile.phone") }}</label>
              <span>{{ userStore.user?.phone || "-" }}</span>
            </div>
          </div>
        </div>

        <div class="section">
          <h3 class="section-title">
            <el-icon><User /></el-icon>
            {{ $t("profile.editInfo") }}
          </h3>
          <el-form
            :model="profileForm"
            ref="profileFormRef"
            label-width="120px"
          >
            <el-form-item :label="$t('profile.email')" prop="email">
              <el-input
                v-model="profileForm.email"
                :placeholder="$t('profile.email')"
              />
            </el-form-item>
            <el-form-item :label="$t('profile.phone')" prop="phone">
              <el-input
                v-model="profileForm.phone"
                :placeholder="$t('profile.phone')"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="handleUpdateProfile"
                :loading="isUpdatingProfile"
              >
                {{ $t("profile.saveProfile") }}
              </el-button>
            </el-form-item>
          </el-form>
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
import {
  changePasswordApi,
  getProfileApi,
  updateProfileApi,
  uploadAvatarApi,
} from "@/api/auth";
import { useUserStore } from "@/stores/user";
import { Camera, Lock, User } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

const userStore = useUserStore();

const avatarInput = ref(null);
const passwordFormRef = ref(null);
const profileFormRef = ref(null);
const isChanging = ref(false);
const isUpdatingProfile = ref(false);

const showOldPassword = ref(false);
const showNewPassword = ref(false);
const showConfirmPassword = ref(false);

const passwordForm = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const profileForm = reactive({
  email: "",
  phone: "",
});

const triggerAvatarUpload = () => {
  avatarInput.value?.click();
};

const handleAvatarUpload = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await uploadAvatarApi(formData);

    if (response.avatar_url) {
      userStore.updateAvatar(response.avatar_url);
      ElMessage.success("头像上传成功");
    }
  } catch (error) {
    ElMessage.error("头像上传失败");
  }

  event.target.value = "";
};

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return;

  const valid = await passwordFormRef.value.validate().catch(() => false);
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

  try {
    await changePasswordApi({
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
    });
    ElMessage.success("密码修改成功");
    passwordForm.oldPassword = "";
    passwordForm.newPassword = "";
    passwordForm.confirmPassword = "";
  } catch (error) {
    ElMessage.error("密码修改失败");
  } finally {
    isChanging.value = false;
  }
};

const handleUpdateProfile = async () => {
  if (!profileFormRef.value) return;

  const valid = await profileFormRef.value.validate().catch(() => false);
  if (!valid) return;

  isUpdatingProfile.value = true;

  try {
    const response = await updateProfileApi({
      email: profileForm.email,
      phone: profileForm.phone,
    });
    userStore.user.email = response.email;
    userStore.user.phone = response.phone;
    localStorage.setItem("rsod_user", JSON.stringify(userStore.user));
    ElMessage.success("个人信息更新成功");
  } catch (error) {
    ElMessage.error("个人信息更新失败");
  } finally {
    isUpdatingProfile.value = false;
  }
};

onMounted(async () => {
  try {
    const profile = await getProfileApi();
    profileForm.email = profile.email || "";
    profileForm.phone = profile.phone || "";
  } catch (error) {
    console.error("获取个人信息失败", error);
  }
});
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 12px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;

  &.detection-icon {
    background: #ecf5ff;
    color: #409eff;
  }

  &.image-icon {
    background: #f0f9eb;
    color: #67c23a;
  }

  &.object-icon {
    background: #fff7e6;
    color: #e6a23c;
  }
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>

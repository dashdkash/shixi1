import request from "@/utils/request";

/**
 * 用户注册
 * @param {Object} data - { username, email, password }
 */
export function registerApi(data) {
  return request.post("/auth/register", data);
}

/**
 * 用户登录
 * @param {Object} data - { username, password }
 * @returns {Promise} - { access_token, token_type, user }
 */
export function loginApi(data) {
  return request.post("/auth/login", data);
}

/**
 * 获取当前用户信息（需要 Token）
 */
export function getUserInfoApi() {
  return request.get("/auth/me");
}

/**
 * 忘记密码
 * @param {Object} data - { email }
 * @returns {Object} - { message, email_exists }
 */
export function forgotPasswordApi(data) {
  return request.post("/auth/forgot-password", data);
}

/**
 * 验证重置密码验证码
 * @param {Object} data - { email, code }
 * @returns {Object} - { message, valid }
 */
export function verifyResetCodeApi(data) {
  return request.post("/auth/verify-reset-code", data);
}

/**
 * 重置密码
 * @param {Object} data - { email, code, new_password }
 */
export function resetPasswordApi(data) {
  return request.post("/auth/reset-password", data);
}

/**
 * 获取个人信息（含检测统计）
 */
export function getProfileApi() {
  return request.get("/auth/profile");
}

/**
 * 更新个人信息
 * @param {Object} data - { email, phone }
 */
export function updateProfileApi(data) {
  return request.put("/auth/profile", data);
}

/**
 * 修改密码
 * @param {Object} data - { old_password, new_password }
 */
export function changePasswordApi(data) {
  return request.put("/auth/password", data);
}

/**
 * 上传头像
 * @param {FormData} formData - { file }
 */
export function uploadAvatarApi(formData) {
  return request.post("/auth/avatar", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
}

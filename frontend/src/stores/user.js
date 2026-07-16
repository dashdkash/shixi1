/**
 * 用户状态管理
 * 管理用户登录信息、Token、角色等
 */
import { getUserInfoApi, loginApi } from "@/api/auth";
import { defineStore } from "pinia";

const TOKEN_KEY = "rsod_token";
const USER_KEY = "rsod_user";

/**
 * 解析 JWT Token 中的 exp 字段，判断是否已过期
 * @param {string} token
 * @returns {boolean} true = 未过期，false = 已过期或无法解析
 */
function isTokenValid(token) {
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    // exp 为 Unix 时间戳（秒），留 30 秒缓冲
    return payload.exp * 1000 > Date.now() + 30000;
  } catch {
    return false;
  }
}

export const useUserStore = defineStore("user", {
  state: () => ({
    // JWT Token
    token: localStorage.getItem(TOKEN_KEY) || "",
    // 用户信息
    user: JSON.parse(localStorage.getItem(USER_KEY) || "null"),
  }),

  getters: {
    /** 是否已登录（同时检查 Token 是否过期） */
    isLoggedIn: (state) => !!state.token && isTokenValid(state.token),

    /** 用户名 */
    username: (state) => state.user?.username || "",

    /** 用户头像 */
    avatar: (state) => state.user?.avatar || "",

    /** 用户角色列表 */
    roles: (state) => state.user?.roles || [],

    /** 是否为管理员 */
    isSuperuser: (state) => {
      if (state.user?.is_superuser) return true;
      if (state.user?.roles && state.user.roles.includes('admin')) return true;
      return false;
    },
  },

  actions: {
    /**
     * 用户登录
     * @param {Object} credentials - { username, password }
     */
    async login(credentials) {
      const res = await loginApi(credentials);

      // 保存 Token
      this.token = res.access_token;
      localStorage.setItem(TOKEN_KEY, res.access_token);

      // 保存用户信息
      this.user = res.user;
      localStorage.setItem(USER_KEY, JSON.stringify(res.user));

      return res;
    },

    /**
     * 获取最新用户信息
     */
    async fetchUserInfo() {
      try {
        const user = await getUserInfoApi();
        this.user = user;
        localStorage.setItem(USER_KEY, JSON.stringify(user));
      } catch {
        this.logout();
      }
    },

    /**
     * 退出登录
     */
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    },
  },
});

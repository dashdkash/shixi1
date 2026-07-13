/**
 * 用户状态管理
 * 管理用户登录信息、Token、角色等
 */
import { getUserInfoApi, loginApi } from "@/api/auth";
import { defineStore } from "pinia";

const TOKEN_KEY = "rsod_token";
const USER_KEY = "rsod_user";

export const useUserStore = defineStore("user", {
  state: () => ({
    // JWT Token
    token: localStorage.getItem(TOKEN_KEY) || "",
    // 用户信息
    user: JSON.parse(localStorage.getItem(USER_KEY) || "null"),
  }),

  getters: {
    /** 是否已登录 */
    isLoggedIn: (state) => !!state.token,

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

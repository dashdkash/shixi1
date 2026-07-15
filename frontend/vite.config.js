import vue from "@vitejs/plugin-vue";
import path from "path";
import net from "net";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 自动寻找后端服务端口（从 8200 开始尝试）
async function findBackendPort(start = 8200, end = 8300) {
  for (let port = start; port < end; port++) {
    try {
      await new Promise((resolve, reject) => {
        const socket = new net.Socket();
        socket.setTimeout(200);
        socket.on("connect", () => { socket.destroy(); resolve(); });
        socket.on("timeout", () => { socket.destroy(); reject(); });
        socket.on("error", () => { socket.destroy(); reject(); });
        socket.connect(port, "127.0.0.1");
      });
      return port;
    } catch { /* port not in use, try next */ }
  }
  return start; // 回退到默认端口
}

export default defineConfig(async () => {
  // 优先使用环境变量，否则自动探测后端端口
  const backendPort = process.env.VITE_BACKEND_PORT
    ? parseInt(process.env.VITE_BACKEND_PORT)
    : await findBackendPort();
  console.log(`[vite] 后端代理端口: ${backendPort}`);

  return {
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },

  // ── CSS 预处理器配置 ──────────────────────────────
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/assets/styles/variables.scss" as *;`,
      },
    },
  },

  // ── 开发服务器配置 ────────────────────────────────
  server: {
    port: 3000,
    open: true,
    proxy: {
      "/api": {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
    },
  },

  // ── Vitest 测试配置 ───────────────────────────────
  test: {
    // 使用 happy-dom 模拟浏览器环境
    environment: "happy-dom",
    // 全局 setup 文件
    setupFiles: ["./tests/setup.js"],
    // 测试文件匹配模式
    include: ["tests/**/*.{test,spec}.{js,ts}"],
    // 覆盖率（可选）
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
    },
  },
};
});

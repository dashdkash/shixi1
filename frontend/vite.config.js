import vue from "@vitejs/plugin-vue";
import http from "http";
import path from "path";
import { fileURLToPath } from "url";
import { defineConfig, loadEnv } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 通过 HTTP 请求 /api/health 验证是否是后端服务
// 避免 TCP 连接误匹配 Windows 系统保留端口
function probeBackend(port) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/api/health`, { timeout: 500 }, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          const json = JSON.parse(data);
          resolve(json.code === 200 || json.data?.status === "healthy");
        } catch {
          resolve(false);
        }
      });
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
  });
}

async function findBackendPort(start = 8200, end = 8300) {
  for (let port = start; port < end; port++) {
    if (await probeBackend(port)) return port;
  }
  return start;
}

export default defineConfig(async ({ mode }) => {
  // 优先使用 .env 文件中的端口，否则自动探测
  const env = loadEnv(mode, process.cwd());
  const backendPort = env.VITE_BACKEND_PORT
    ? parseInt(env.VITE_BACKEND_PORT)
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
      "/uploads": {
        target: "http://localhost:8200",
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

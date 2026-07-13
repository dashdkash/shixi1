/**
 * Vitest 全局 setup
 * 在每个测试文件执行前自动运行
 */

// 模拟 localStorage（happy-dom 已内置）
// 如需额外 mock，在此添加

// 模拟 Element Plus 的 ElMessage（避免测试中弹出消息框）
import { vi } from "vitest";

vi.mock("element-plus", async () => {
  const actual = await vi.importActual("element-plus");
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});

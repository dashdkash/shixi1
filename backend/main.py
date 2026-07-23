# backend/main.py
"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router  # Day 8 新增
from app.api.detection import router as detection_router  # Day 8 新增
from app.api.health import router as health_router
from app.api.training import router as training_router  # 新增：训练路由
from app.api.dashboard import router as dashboard_router  # 数据看板路由
from app.api.history import router as history_router
from app.api.knowledge import router as knowledge_router
from fastapi.staticfiles import StaticFiles
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.middleware.request_logger import RequestLogMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def init_minio():
    """初始化 MinIO 存储桶（失败则记录警告，不阻止启动）"""
    try:
        from app.storage.minio_client import MinIOClient

        minio_client = MinIOClient()
        print(f"✅ MinIO 存储桶 '{minio_client.bucket_name}' 初始化完成")
    except Exception as e:
        print(f"⚠️ MinIO 初始化失败（不影响核心功能）: {str(e)}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    print("🚀 正在初始化服务...")
    init_minio()
    print("✅ 服务初始化完成")
    yield
    print("🛑 服务已关闭")


# 创建 FastAPI 实例
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 YOLOv11 的目标检测智能体平台 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ===== 中间件（按顺序注册） =====
# 1. CORS 中间件（最先执行）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 请求日志中间件
app.add_middleware(RequestLogMiddleware)

# ===== 注册全局异常处理器 =====
register_exception_handlers(app)

# ===== 注册路由 =====
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(training_router)  # 新增：注册训练路由
app.include_router(chat_router)  # Day 8 新增
app.include_router(detection_router)  # Day 8 新增

app.include_router(knowledge_router)
app.include_router(history_router)
app.include_router(dashboard_router)  # 数据看板路由

# ===== 静态文件挂载 =====
import os
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
detections_dir = os.path.join(os.path.dirname(__file__), "detections")
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(detections_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/detections", StaticFiles(directory=detections_dir), name="detections")

# ===== 根路径 =====
@app.get("/")
def root():
    return {
        "message": "欢迎使用 RSOD Agent Platform",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import socket
    import uvicorn

    def find_free_port(start: int = 8200, end: int = 8300) -> int:
        """从 start 开始寻找可用端口"""
        for port in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        raise RuntimeError(f"在 {start}-{end} 范围内未找到可用端口")

    port = find_free_port()
    print(f"启动服务: http://127.0.0.1:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True, reload_excludes=["**/__pycache__/*", "**/*.pyc", "**/.venv/*"])

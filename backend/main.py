from contextlib import asynccontextmanager

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.detection import router as detection_router
from app.api.health import router as health_router
from app.api.history import router as history_router
from app.api.knowledge import router as knowledge_router
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.middleware.request_logger import RequestLogMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def init_minio():
    """初始化 MinIO 存储桶"""
    from app.storage.minio_client import MinIOClient

    try:
        minio_client = MinIOClient()
        print(f"MinIO 存储桶 '{minio_client.bucket_name}' 初始化完成")
    except Exception as e:
        print(f"MinIO 初始化失败: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("正在初始化服务...")
    init_minio()
    yield
    # 关闭时执行（如果需要）
    print("服务已关闭")


# 创建 FastAPI 实例
app = FastAPI(
    title="RSOD Agent Platform",
    version="0.1.0",
    description="基于 YOLOv11 的目标检测智能体平台 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── 注册中间件（注意顺序）──────────────────────────────
# 中间件执行顺序：后添加的先执行（洋葱模型）
# 请求进入 → CORS（最外层）→ RequestLog → 路由 → ...
# 响应返回 ← CORS（最外层）← RequestLog ← 路由 ← ...

# 1. 请求日志中间件（内层，后执行）
app.add_middleware(RequestLogMiddleware)

# 2. CORS 中间件（外层，最先处理跨域，后添加）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 注册路由 ─────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(detection_router)
app.include_router(history_router)
app.include_router(health_router)
app.include_router(knowledge_router)

@app.get("/")
def root():
    return {
        "message": "欢迎使用 RSOD Agent Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ── 注册全局异常处理器 ─────────────────────────────────
register_exception_handlers(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8200, reload=True)

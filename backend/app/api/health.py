"""
健康检查 API 路由

接口列表：
  - GET /api/health           基础健康检查（应用状态）
  - GET /api/health/detail    详细健康检查（含数据库、Redis、MinIO 状态）

设计原则：
  - 基础检查不依赖外部服务，响应快
  - 详细检查逐一验证各依赖服务的连通性
  - 任一服务不可用时不抛异常，而是标记为 unhealthy
"""

from app.config.settings import settings
from app.core.logger import get_logger
from fastapi import APIRouter

logger = get_logger(__name__)

router = APIRouter(tags=["健康检查"])


@router.get("/api/health")
async def health_check():
    """
    基础健康检查

    用途：Docker liveness probe、负载均衡器探活
    特点：不检查外部依赖，只确认应用进程存活
    """
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
    }


@router.get("/api/health/detail")
async def health_check_detail():
    """
    详细健康检查

    用途：管理后台状态展示、运维监控
    特点：逐一检测 PostgreSQL、Redis、MinIO 连通性
    """
    services = {}

    # ── 检查 PostgreSQL ──────────────────────────────
    try:
        from app.database.session import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        # 执行最简单的查询验证连接（SQLAlchemy 2.x 语法）
        db.execute(text("SELECT 1"))
        db.close()
        services["database"] = {"status": "healthy", "message": "PostgreSQL 连接正常"}
    except Exception as e:
        services["database"] = {
            "status": "unhealthy",
            "message": f"PostgreSQL 连接失败: {str(e)}",
        }
        logger.error("PostgreSQL 健康检查失败: %s", str(e))

    # ── 检查 Redis ───────────────────────────────────
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        r.close()
        services["redis"] = {"status": "healthy", "message": "Redis 连接正常"}
    except Exception as e:
        services["redis"] = {
            "status": "unhealthy",
            "message": f"Redis 连接失败: {str(e)}",
        }
        logger.error("Redis 健康检查失败: %s", str(e))

    # ── 检查 MinIO ───────────────────────────────────
    try:
        from app.storage.minio_client import MinIOClient

        minio = MinIOClient()
        minio.client.list_buckets()
        services["minio"] = {"status": "healthy", "message": "MinIO 连接正常"}
    except Exception as e:
        services["minio"] = {
            "status": "unhealthy",
            "message": f"MinIO 连接失败: {str(e)}",
        }
        logger.error("MinIO 健康检查失败: %s", str(e))

    # ── 汇总状态 ─────────────────────────────────────
    all_healthy = all(s["status"] == "healthy" for s in services.values())

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "status": "healthy" if all_healthy else "degraded",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "services": services,
        },
    }

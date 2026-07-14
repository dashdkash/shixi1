"""
API 速率限制中间件

生产环境标准：
  - 基于 Redis 的分布式速率限制
  - 支持不同路由的自定义限流规则
  - 友好的错误提示
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.storage.redis_client import redis_client


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """API 速率限制中间件"""

    DEFAULT_LIMIT = 60
    DEFAULT_WINDOW = 60

    RATE_LIMITS = {
        "/api/detection/single": {"limit": 30, "window": 60},
        "/api/detection/batch": {"limit": 10, "window": 60},
        "/api/detection/video": {"limit": 5, "window": 60},
        "/api/detection/camera": {"limit": 10, "window": 60},
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        limit_config = self.RATE_LIMITS.get(path)
        if not limit_config:
            limit_config = {"limit": self.DEFAULT_LIMIT, "window": self.DEFAULT_WINDOW}

        client_ip = self._get_client_ip(request)
        key = f"rate_limit:{path}:{client_ip}"

        try:
            current = redis_client.get(key)
            if current is None:
                redis_client.set(key, 1, expire=limit_config["window"])
                current = 1
            else:
                current = int(current) + 1
                redis_client.set(key, current, expire=limit_config["window"])

            if current > limit_config["limit"]:
                return Response(
                    content='{"error": "Rate limit exceeded", "message": "Too many requests, please try again later"}',
                    status_code=429,
                    media_type="application/json",
                )

        except Exception:
            pass

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            return x_real_ip

        return request.client.host if request.client else "unknown"
"""
全局异常处理模块

职责：
  - 捕获所有未处理的异常，返回统一 JSON 格式
  - 区分已知异常（HTTP 业务错误）和未知异常（程序 Bug）
  - 未知异常自动记录 ERROR 级别日志

注册方式（在 main.py 中）：
  from app.core.exceptions import register_exception_handlers
  register_exception_handlers(app)
"""

from app.core.logger import get_logger
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        处理 HTTP 业务异常（如 400、401、404 等）

        这些是代码中主动 raise 的业务错误，不需要记录 ERROR 日志，
        只需返回给前端即可。
        """
        # 4xx 错误用 WARNING 级别（客户端问题）
        if 400 <= exc.status_code < 500:
            logger.warning(
                "HTTP %d: %s | path=%s",
                exc.status_code,
                exc.detail,
                request.url.path,
            )
        else:
            logger.error(
                "HTTP %d: %s | path=%s",
                exc.status_code,
                exc.detail,
                request.url.path,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": exc.detail,
                "data": None,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """
        处理 Pydantic 参数验证异常

        当请求参数不符合 Pydantic 模型定义时触发，
        如：缺少必填字段、类型不匹配、超出范围等。
        """
        # 提取所有验证错误信息
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors.append(f"{field}: {error['msg']}")

        logger.warning(
            "参数验证失败 | path=%s | errors=%s",
            request.url.path,
            errors,
        )

        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "参数验证失败",
                "data": errors,
            },
        )

    @app.exception_handler(JWTError)
    async def jwt_exception_handler(request: Request, exc: JWTError):
        """处理 JWT Token 解析异常"""
        logger.warning("JWT 验证失败 | path=%s | error=%s", request.url.path, str(exc))

        return JSONResponse(
            status_code=401,
            content={
                "code": 401,
                "message": "无效的认证凭据",
                "data": None,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        处理所有未预期的异常（兜底处理器）

        这是最后一道防线：任何没有被上面三个处理器捕获的异常都会到这里。
        必须记录完整的错误堆栈，但返回给前端时隐藏细节（安全考虑）。
        """
        # 使用 exc_info=True 记录完整堆栈信息
        logger.error(
            "未处理的异常 | path=%s | method=%s | error=%s",
            request.url.path,
            request.method,
            str(exc),
            exc_info=True,  # 关键：记录完整堆栈
        )

        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "data": None,
            },
        )

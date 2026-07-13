"""
统一日志配置模块

职责：
  - 配置全局日志格式和输出级别
  - 同时输出到控制台和日志文件
  - 日志文件按大小自动轮转（保留最近 N 份）

使用方式：
  在其他模块中引入：
    from app.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("服务启动成功")
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config.settings import settings

# ── 日志目录 ──────────────────────────────────────────
# 日志文件存放在 backend/logs/ 目录下
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs"
)
os.makedirs(LOG_DIR, exist_ok=True)

# ── 日志格式 ──────────────────────────────────────────
# 格式说明：
#   %(asctime)s     — 时间戳（精确到毫秒）
#   %(levelname)-8s — 日志级别（左对齐，8 字符宽）
#   %(name)s        — Logger 名称（通常是模块名）
#   %(funcName)s    — 调用日志的函数名
#   %(lineno)d      — 调用日志的代码行号
#   %(message)s     — 日志内容
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── 格式化器 ──────────────────────────────────────────
formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

# ── 是否已初始化标记（避免重复添加 handler）────────────
_initialized = False


def setup_logging():
    """
    初始化全局日志系统（只需调用一次）

    配置两个输出目标：
      1. 控制台（StreamHandler）— 开发时实时查看
      2. 文件（RotatingFileHandler）— 持久化存储，按大小轮转
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    # 获取根 Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))

    # ── 控制台 Handler ────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ── 文件 Handler（轮转）──────────────────────────
    # maxBytes=10MB：单个日志文件超过 10MB 时自动切割
    # backupCount=5：保留最近 5 份历史日志
    # encoding="utf-8"：确保中文日志正常显示
    file_path = os.path.join(LOG_DIR, "app.log")
    file_handler = RotatingFileHandler(
        filename=file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)  # 文件只记录 INFO 及以上
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # ── 降低第三方库日志级别，避免刷屏 ──────────────────
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("minio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 Logger

    Args:
        name: Logger 名称，通常传入 __name__（模块路径）

    Returns:
        配置好的 Logger 实例

    使用示例：
        logger = get_logger(__name__)
        logger.info("用户登录成功: user_id=%d", user_id)
        logger.error("数据库连接失败: %s", error_msg)
    """
    setup_logging()  # 确保日志系统已初始化
    return logging.getLogger(name)

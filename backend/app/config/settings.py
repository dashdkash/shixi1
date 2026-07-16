# backend/app/config/settings.py
"""
全局配置模块
使用 pydantic-settings 管理所有配置项，支持从 .env 文件和环境变量读取
加载优先级：环境变量（系统级别）> .env 文件 > 代码中的默认值
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    # ---- 应用基础配置 ----
    # ── 训练配置 ──────────────────────────────────────
    TRAIN_OUTPUT_DIR: str = "runs/train"  # 训练输出目录（模型权重、日志等）
    DATASET_BASE_DIR: str = "datasets"    # 数据集根目录
    APP_NAME: str = "RSOD Agent Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"  # 已存在，保留
    
    SERVER_HOST: str = "http://localhost"
    SERVER_PORT: int = 8200

    # ── 日志文件配置（新增） ──────────────────────────
    LOG_DIR: str = "logs"  # 日志目录（相对于 backend/）
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 单文件最大 10MB
    LOG_BACKUP_COUNT: int = 5  # 保留 5 份历史日志

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "rsod_agent"
    DB_USER: str = "rsod_admin"
    DB_PASSWORD: str = "rsod_admin"

    @property
    def DATABASE_URL(self) -> str:
        """构造 PostgreSQL 连接字符串"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # ---- Redis 配置 ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        """构造 Redis 连接字符串"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # ---- MinIO 配置 ----
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "rsod-agent-images"
    MINIO_AVATAR_BUCKET: str = "rsod-agent-avatars"
    MINIO_SECURE: bool = False

    # ---- JWT 认证配置 ----
    JWT_SECRET_KEY: str = "rsod-dev-secret-key-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时

    # ---- CORS 配置 ----
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    )

    # ========== LLM 配置（Day 8 新增） ==========
    # 通义千问（推荐）
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    # OpenAI（备选）
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # 本地 LLM（可选）
    USE_LOCAL_LLM: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    # 通义千问（推荐，国内访问快）
    QWEN_API_KEY: str = "sk-your-qwen-api-key"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    # ── RAG 配置 ──────────────────────────────────────
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_DIM: int = 1024
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5
    RERANKER_MODEL: str = "gte-rerank"  # DashScope 重排模型
    RERANKER_TOP_N: int = 3  # 重排后保留的条数（<= RAG_TOP_K）
    RAG_ENABLE_RERANK: bool = True  # 是否启用重排

    # ── 邮件配置 ──────────────────────────────────────
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "noreply@example.com"
    SMTP_PASSWORD: str = "your-smtp-password"
    SMTP_FROM_NAME: str = "RSOD Agent Platform"
    SMTP_USE_TLS: bool = True
    
    # 前端地址（用于生成重置链接）
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """将 CORS 配置字符串转为列表"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # ---- 训练配置（Day 6 新增） ----
    TRAIN_OUTPUT_DIR: str = "runs/train"  # 训练输出目录（模型权重、日志等）
    DATASET_BASE_DIR: str = "datasets"  # 数据集根目录

    # ---- Pydantic V2 配置 ----
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略 .env 中未定义的额外字段，更安全
    )


# 创建全局单例，其他模块直接 import 使用
settings = Settings()

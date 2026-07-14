"""
数据库连接与会话管理
- 创建 SQLAlchemy 引擎和会话工厂
- 提供 get_db 依赖注入函数，供 API 层使用
- 注册 pgvector 扩展支持
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from app.config.settings import settings
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

# 注册 pgvector 扩展（必须在 Base 创建前导入）
from pgvector.sqlalchemy import Vector  # noqa: F401

# 创建数据库引擎
# pool_pre_ping=True：每次从连接池取连接前先测试是否可用
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,  # DEBUG 模式下打印 SQL 语句
)

# 会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ORM 模型的基类，所有模型都继承自它
Base = declarative_base()


@event.listens_for(engine, "connect")
def _register_pgvector(dbapi_connection, connection_record):
    """每次新连接时确保 pgvector 扩展可用"""
    cursor = dbapi_connection.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cursor.close()


def get_psycopg2_conn():
    """
    获取 psycopg2 原生连接（用于 pgvector 原生 SQL 查询）

    场景：SQLAlchemy 的 :param 语法与 PostgreSQL ::vector 类型转换冲突时，
    使用 psycopg2 原生连接执行 SQL，通过 %s 占位符安全传参。

    用法示例：
        conn = get_psycopg2_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM t WHERE col = %s", (val,))
            rows = cursor.fetchall()
        finally:
            conn.close()
    """
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    # 确保 pgvector 扩展可用
    cursor = conn.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cursor.close()
    return conn


def get_db():
    """
    获取数据库会话的依赖注入函数
    在 FastAPI 路由中通过 Depends(get_db) 使用

    用法示例：
        @router.get("/xxx")
        def my_api(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

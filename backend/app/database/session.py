"""
数据库连接与会话管理
- 创建 SQLAlchemy 引擎和会话工厂
- 提供 get_db 依赖注入函数，供 API 层使用
"""

from app.config.settings import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

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

"""
创建管理员账号脚本

使用方法：
1. 确保后端项目已安装依赖
2. 设置好环境变量（数据库连接）
3. 运行: python create_admin.py

如果管理员已存在，会提示更新密码
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import get_db, Base, engine
from app.entity.db_models import User
from app.core.security import get_password_hash


def create_admin(username: str, email: str, password: str):
    """创建或更新管理员账号"""
    # 创建表（如果不存在）
    Base.metadata.create_all(bind=engine)
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 检查管理员是否已存在
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"用户 '{username}' 已存在，正在更新为管理员...")
            existing_user.is_superuser = True
            existing_user.hashed_password = get_password_hash(password)
            db.commit()
            print(f"✓ 已将 '{username}' 更新为管理员")
        else:
            print(f"创建管理员账号 '{username}'...")
            admin_user = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
                is_superuser=True,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"✓ 管理员账号 '{username}' 创建成功")
            
    except Exception as e:
        db.rollback()
        print(f"✗ 创建管理员失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("杂草识别智能体 - 管理员账号创建工具")
    print("=" * 50)
    
    username = input("请输入管理员用户名: ").strip() or "admin"
    email = input("请输入管理员邮箱: ").strip() or "admin@example.com"
    password = input("请输入管理员密码: ").strip() or "admin123"
    
    print()
    create_admin(username, email, password)
    print("=" * 50)

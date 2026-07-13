"""
将指定用户设置为管理员

使用方法：
python set_admin.py <username>

示例：
python set_admin.py testuser
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import get_db, Base, engine
from app.entity.db_models import User


def set_admin(username: str):
    """将指定用户设置为管理员"""
    Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"✗ 用户 '{username}' 不存在")
            return
        
        if user.is_superuser:
            print(f"✓ 用户 '{username}' 已经是管理员")
            return
        
        user.is_superuser = True
        db.commit()
        print(f"✓ 用户 '{username}' 已成功设置为管理员")
        
    except Exception as e:
        db.rollback()
        print(f"✗ 设置管理员失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("杂草识别智能体 - 设置管理员工具")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("用法: python set_admin.py <username>")
        print("示例: python set_admin.py testuser")
        sys.exit(1)
    
    username = sys.argv[1]
    print(f"\n正在将用户 '{username}' 设置为管理员...")
    set_admin(username)
    print("=" * 50)

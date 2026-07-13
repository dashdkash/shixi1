"""
将指定用户添加到管理员角色

使用方法：
python add_admin_role.py <username>

示例：
python add_admin_role.py testuser
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.database.session import get_db, Base, engine
    from app.entity.db_models import Role, User, UserRole
    
    print("=" * 50)
    print("杂草识别智能体 - 添加管理员角色")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("用法: python add_admin_role.py <username>")
        print("示例: python add_admin_role.py testuser")
        sys.exit(1)
    
    username = sys.argv[1]
    
    # 创建表（如果不存在）
    Base.metadata.create_all(bind=engine)
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 查找用户
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"✗ 用户 '{username}' 不存在")
            print("请先注册该用户")
            sys.exit(1)
        
        # 查找 admin 角色
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            print("✗ admin 角色不存在")
            print("请先运行: python init_roles.py")
            sys.exit(1)
        
        # 检查用户是否已拥有 admin 角色
        existing_assignment = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role_id == admin_role.id
        ).first()
        
        if existing_assignment:
            print(f"✓ 用户 '{username}' 已经是管理员")
        else:
            # 添加角色关联
            admin_assignment = UserRole(user_id=user.id, role_id=admin_role.id)
            db.add(admin_assignment)
            db.commit()
            print(f"✓ 用户 '{username}' 已成功添加管理员角色")
        
        # 同时设置 is_superuser 为 true（保持兼容性）
        if not user.is_superuser:
            user.is_superuser = True
            db.commit()
            print(f"✓ 用户 '{username}' 的 is_superuser 已设置为 true")
        
    except Exception as e:
        db.rollback()
        print(f"✗ 设置管理员失败: {e}")
        raise
    finally:
        db.close()
        
    print("=" * 50)
    
except Exception as e:
    print(f"初始化失败: {e}")

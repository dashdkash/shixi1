"""
初始化系统角色脚本

创建 admin 和 user 两个角色
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.database.session import get_db, Base, engine
    from app.entity.db_models import Role
    
    print("=" * 50)
    print("杂草识别智能体 - 初始化角色")
    print("=" * 50)
    
    # 创建表（如果不存在）
    Base.metadata.create_all(bind=engine)
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 创建 user 角色（普通用户）
        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(
                name="user",
                display_name="普通用户",
                description="普通用户角色，拥有基础访问权限",
                is_system=True,
            )
            db.add(user_role)
            print("✓ 创建 user 角色")
        else:
            print("✓ user 角色已存在")
        
        # 创建 admin 角色（管理员）
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                display_name="管理员",
                description="系统管理员，拥有全部权限",
                is_system=True,
            )
            db.add(admin_role)
            print("✓ 创建 admin 角色")
        else:
            print("✓ admin 角色已存在")
        
        db.commit()
        print("\n✓ 角色初始化完成")
        
    except Exception as e:
        db.rollback()
        print(f"✗ 初始化失败: {e}")
        raise
    finally:
        db.close()
        
    print("=" * 50)
    
except Exception as e:
    print(f"初始化失败: {e}")

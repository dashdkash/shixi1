"""
简单版：使用 SQLAlchemy 直接连接数据库修改用户角色

确保后端服务正在运行，或者数据库可访问
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.database.session import get_db, Base, engine
    from app.entity.db_models import User
    
    print("=" * 50)
    print("杂草识别智能体 - 设置管理员工具")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("用法: python set_admin_simple.py <username>")
        print("示例: python set_admin_simple.py testuser")
        sys.exit(1)
    
    username = sys.argv[1]
    
    # 创建表（如果不存在）
    Base.metadata.create_all(bind=engine)
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"✗ 用户 '{username}' 不存在")
            print("请先注册该用户")
        elif user.is_superuser:
            print(f"✓ 用户 '{username}' 已经是管理员")
        else:
            user.is_superuser = True
            db.commit()
            print(f"✓ 用户 '{username}' 已成功设置为管理员")
            
    except Exception as e:
        db.rollback()
        print(f"✗ 设置管理员失败: {e}")
        raise
    finally:
        db.close()
        
    print("=" * 50)
    
except Exception as e:
    print(f"初始化失败: {e}")
    print("\n尝试使用环境变量直接连接数据库...")
    
    # 尝试另一种方式：直接使用 psycopg2
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        load_dotenv()
        
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            dbname=os.getenv("DB_NAME", "rsod_agent"),
            user=os.getenv("DB_USER", "rsod_admin"),
            password=os.getenv("DB_PASSWORD", "rsod_admin")
        )
        
        cursor = conn.cursor()
        
        if len(sys.argv) >= 2:
            username = sys.argv[1]
            
            cursor.execute("SELECT id, is_superuser FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            
            if not result:
                print(f"✗ 用户 '{username}' 不存在")
            elif result[1]:
                print(f"✓ 用户 '{username}' 已经是管理员")
            else:
                cursor.execute("UPDATE users SET is_superuser = true WHERE username = %s", (username,))
                conn.commit()
                print(f"✓ 用户 '{username}' 已成功设置为管理员")
        else:
            print("用法: python set_admin_simple.py <username>")
            
        cursor.close()
        conn.close()
        
    except Exception as e2:
        print(f"✗ 连接数据库失败: {e2}")
        print("\n你也可以手动执行以下 SQL:")
        print(f"UPDATE users SET is_superuser = true WHERE username = '{username}';")

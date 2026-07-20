"""
用户服务层
处理用户注册、登录、鉴权等业务逻辑
"""

import secrets
from datetime import datetime, timedelta

from app.core.security import create_access_token, hash_password, verify_password
from app.entity.db_models import DetectionTask, Role, User, UserRole
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session


class UserService:
    """用户服务"""

    @staticmethod
    def register(db: Session, username: str, email: str, password: str, require_verification: bool = False) -> User:
        """
        用户注册

        Args:
            db: 数据库会话
            username: 用户名
            email: 邮箱
            password: 明文密码
            require_verification: 是否需要邮箱验证

        Returns:
            新创建的用户对象

        Raises:
            HTTPException: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")

        # 检查邮箱是否已存在
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已被注册")

        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            email_verified=not require_verification,  # 开发环境直接验证
        )
        
        # 如果需要验证，生成验证令牌
        if require_verification:
            new_user.verification_token = secrets.token_urlsafe(32)
            new_user.verification_token_expires_at = datetime.now() + timedelta(hours=24)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 自动分配 user 角色
        user_role = db.query(Role).filter(Role.name == "user").first()
        if user_role:
            user_role_assignment = UserRole(user_id=new_user.id, role_id=user_role.id)
            db.add(user_role_assignment)
            db.commit()

        return new_user

    @staticmethod
    def verify_email(db: Session, token: str) -> bool:
        """
        验证邮箱

        Args:
            db: 数据库会话
            token: 验证令牌

        Returns:
            是否验证成功
        """
        user = db.query(User).filter(User.verification_token == token).first()
        if not user:
            return False

        # 检查令牌是否过期
        if user.verification_token_expires_at and user.verification_token_expires_at < datetime.now():
            return False

        # 更新验证状态
        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        db.commit()

        return True

    @staticmethod
    def resend_verification_email(db: Session, email: str) -> str | None:
        """
        重新发送验证邮件

        Args:
            db: 数据库会话
            email: 用户邮箱

        Returns:
            验证令牌，如果用户不存在或已验证返回 None
        """
        user = db.query(User).filter(User.email == email).first()
        if not user or user.email_verified:
            return None

        # 生成新的验证令牌
        token = secrets.token_urlsafe(32)
        user.verification_token = token
        user.verification_token_expires_at = datetime.now() + timedelta(hours=24)
        db.commit()

        return token

    @staticmethod
    def login(db: Session, username: str, password: str, require_verification: bool = False) -> User:
        """
        用户登录

        Args:
            db: 数据库会话
            username: 用户名
            password: 明文密码
            require_verification: 是否要求邮箱已验证

        Returns:
            登录成功的用户对象

        Raises:
            HTTPException: 用户名或密码错误，或邮箱未验证
        """
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not verify_password(password, user.hashed_password):  # type: ignore
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 检查邮箱是否已验证（生产环境）
        if require_verification and not user.email_verified:
            raise HTTPException(status_code=403, detail="邮箱未验证，请先验证邮箱")

        # 更新最后登录时间
        user.last_login_at = datetime.now()
        db.commit()

        return user

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        """为用户生成 JWT Token"""
        return create_access_token(data={"sub": str(user.id)})

    @staticmethod
    def get_user_roles(db: Session, user: User) -> list[str]:
        """获取用户的角色标识列表"""
        return [ur.role.name for ur in user.user_roles]

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """根据 ID 获取用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        """根据邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def generate_reset_token(db: Session, email: str) -> str | None:
        """
        生成密码重置令牌

        Args:
            db: 数据库会话
            email: 用户邮箱

        Returns:
            重置令牌，如果用户不存在返回 None
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None

        # 生成 32 位随机令牌
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now() + timedelta(hours=1)
        db.commit()

        return token

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> bool:
        """
        使用令牌重置密码

        Args:
            db: 数据库会话
            token: 重置令牌
            new_password: 新密码

        Returns:
            是否重置成功
        """
        user = db.query(User).filter(User.reset_token == token).first()
        if not user:
            return False

        # 检查令牌是否过期
        if user.reset_token_expires_at and user.reset_token_expires_at < datetime.now():
            return False

        # 更新密码
        user.hashed_password = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires_at = None
        db.commit()

        return True

    @staticmethod
    def generate_reset_verification_code(db: Session, email: str) -> str | None:
        """
        生成密码重置验证码（6位数字）

        Args:
            db: 数据库会话
            email: 用户邮箱

        Returns:
            验证码，如果用户不存在返回 None
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None

        import random
        code = str(random.randint(100000, 999999))

        user.reset_verification_code = code
        user.reset_verification_code_expires_at = datetime.now() + timedelta(minutes=5)
        db.commit()

        return code

    @staticmethod
    def verify_reset_code(db: Session, email: str, code: str) -> bool:
        """
        验证密码重置验证码
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False

        if not user.reset_verification_code or user.reset_verification_code != code:
            return False

        if user.reset_verification_code_expires_at and user.reset_verification_code_expires_at < datetime.now():
            return False

        return True

    @staticmethod
    def reset_password_with_code(db: Session, email: str, code: str, new_password: str) -> bool:
        """
        使用验证码重置密码
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False

        if not user.reset_verification_code or user.reset_verification_code != code:
            return False

        if user.reset_verification_code_expires_at and user.reset_verification_code_expires_at < datetime.now():
            return False

        user.hashed_password = hash_password(new_password)
        user.reset_verification_code = None
        user.reset_verification_code_expires_at = None
        db.commit()

        return True

    @staticmethod
    def update_profile(db: Session, user: User, email: str | None = None, phone: str | None = None) -> User:
        """
        更新用户个人信息

        Args:
            db: 数据库会话
            user: 当前用户
            email: 新邮箱
            phone: 新手机号

        Returns:
            更新后的用户对象
        """
        if email and email != user.email:
            # 检查邮箱是否已被其他用户使用
            existing_user = db.query(User).filter(User.email == email, User.id != user.id).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="邮箱已被其他用户使用")
            user.email = email

        if phone is not None:
            user.phone = phone

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def change_password(db: Session, user: User, old_password: str, new_password: str) -> bool:
        """
        修改密码

        Args:
            db: 数据库会话
            user: 当前用户
            old_password: 旧密码
            new_password: 新密码

        Returns:
            是否修改成功
        """
        if not verify_password(old_password, user.hashed_password):  # type: ignore
            return False

        user.hashed_password = hash_password(new_password)
        db.commit()
        return True

    @staticmethod
    def update_avatar(db: Session, user: User, avatar_url: str) -> User:
        """
        更新用户头像

        Args:
            db: 数据库会话
            user: 当前用户
            avatar_url: 头像 URL

        Returns:
            更新后的用户对象
        """
        user.avatar = avatar_url
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_detection_stats(db: Session, user_id: int) -> dict:
        """
        获取用户检测统计数据

        Args:
            db: 数据库会话
            user_id: 用户 ID

        Returns:
            统计数据字典
        """
        # 总检测任务数
        total_detections = db.query(DetectionTask).filter(DetectionTask.user_id == user_id).count()

        # 总处理图像数和检测目标数
        stats = db.query(
            func.coalesce(func.sum(DetectionTask.total_images), 0),
            func.coalesce(func.sum(DetectionTask.total_objects), 0)
        ).filter(DetectionTask.user_id == user_id).first()

        return {
            "total_detections": total_detections,
            "total_images_detected": stats[0] if stats else 0,
            "total_objects_found": stats[1] if stats else 0,
        }


# 全局单例
user_service = UserService()

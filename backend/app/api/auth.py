"""
认证相关 API 路由
- POST /api/auth/register          用户注册
- POST /api/auth/login             用户登录
- GET  /api/auth/me                获取当前用户信息
- POST /api/auth/forgot-password   忘记密码
- POST /api/auth/reset-password    重置密码
- GET  /api/auth/profile           获取个人信息（含检测统计）
- PUT  /api/auth/profile           修改个人信息
- PUT  /api/auth/password          修改密码
- POST /api/auth/avatar            上传头像
- POST /api/auth/verify-email      验证邮箱
- POST /api/auth/resend-verification 重新发送验证邮件
"""

import os
import uuid
from typing import Optional

from app.config.settings import settings
from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.schemas import (
    AvatarResponse,
    ChangePassword,
    ForgotPasswordRequest,
    ProfileUpdate,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserResponseWithStats,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app.services.user_service import user_service
from app.storage.minio_client import MinIOClient
from app.core.email import send_password_reset_email, send_verification_email
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/auth", tags=["认证"])

# OAuth2 密码模式，用于从请求 Header 中提取 Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    从 JWT Token 中解析当前用户
    在需要认证的路由中通过 Depends(get_current_user) 使用
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = user_service.get_user_by_id(db, user_id)
    return user


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(request: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册

    - **username**: 用户名（3-50 字符）
    - **email**: 邮箱
    - **password**: 密码（至少 6 位）
    
    开发环境（DEBUG=true）：注册后自动验证，可直接登录
    生产环境（DEBUG=false）：需要验证邮箱后才能登录
    """
    # 根据环境决定是否要求邮箱验证
    require_verification = not settings.DEBUG
    
    user = user_service.register(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
        require_verification=require_verification,
    )
    
    # 如果需要验证，发送验证邮件
    if require_verification and user.verification_token:
        email_sent = send_verification_email(user.email, user.verification_token)
        
        # 开发环境下如果发送失败，返回 token 便于测试
        if not email_sent and settings.DEBUG:
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "avatar": user.avatar,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "email_verified": user.email_verified,
                "roles": [],
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
                "verification_token": user.verification_token,  # 仅开发环境返回
            }
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录

    - 返回 JWT access_token（24小时有效）
    - 后续请求在 Header 中携带：Authorization: Bearer <token>
    
    开发环境（DEBUG=true）：不检查邮箱验证状态
    生产环境（DEBUG=false）：需要邮箱已验证才能登录
    """
    # 根据环境决定是否检查邮箱验证
    require_verification = not settings.DEBUG
    
    user = user_service.login(
        db=db,
        username=request.username,
        password=request.password,
        require_verification=require_verification,
    )

    access_token = user_service.create_access_token_for_user(user)
    roles = user_service.get_user_roles(db, user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "is_superuser": user.is_superuser,
            "email_verified": user.email_verified,
            "roles": roles,
        },
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前登录用户信息（需要 Token 认证）"""
    roles = user_service.get_user_roles(db, current_user)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "roles": roles,
        "last_login_at": current_user.last_login_at,
        "created_at": current_user.created_at,
    }


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    忘记密码

    - 生成一次性重置令牌（1h 有效）
    - 发送重置邮件到用户邮箱
    """
    token = user_service.generate_reset_token(db, request.email)

    # 如果用户存在，发送邮件
    if token:
        # 生产环境发送邮件
        email_sent = send_password_reset_email(request.email, token)
        
        # 开发环境下如果发送失败，返回 token 便于测试
        if not email_sent and settings.DEBUG:
            return {
                "message": "重置令牌已生成（邮件发送失败，开发环境直接返回）",
                "reset_url": f"/reset-password?token={token}",
                "token": token,
            }

    # 无论邮箱是否存在都返回成功，防止邮箱枚举攻击
    return {
        "message": "如果该邮箱已注册，重置链接将发送至您的邮箱"
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    重置密码

    - 验证令牌并更新密码
    - 令牌使用后自动失效
    """
    success = user_service.reset_password(db, request.token, request.new_password)

    if not success:
        raise HTTPException(status_code=400, detail="重置令牌无效或已过期")

    return {"message": "密码重置成功"}


@router.get("/profile", response_model=UserResponseWithStats)
async def get_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前登录用户信息（含检测统计数据）"""
    roles = user_service.get_user_roles(db, current_user)
    stats = user_service.get_user_detection_stats(db, current_user.id)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "roles": roles,
        "last_login_at": current_user.last_login_at,
        "created_at": current_user.created_at,
        **stats,
    }


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: ProfileUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    修改个人信息

    - 修改邮箱（唯一性校验）
    - 修改手机号
    """
    user = user_service.update_profile(
        db=db,
        user=current_user,
        email=request.email,
        phone=request.phone,
    )
    roles = user_service.get_user_roles(db, user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": roles,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


@router.put("/password")
async def change_password(
    request: ChangePassword,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    修改密码

    - 验证旧密码后更新
    """
    success = user_service.change_password(
        db=db,
        user=current_user,
        old_password=request.old_password,
        new_password=request.new_password,
    )

    if not success:
        raise HTTPException(status_code=400, detail="旧密码错误")

    return {"message": "密码修改成功"}


@router.post("/avatar", response_model=AvatarResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传头像

    - 上传至 MinIO avatars bucket
    - 支持 JPG/PNG 格式
    - 文件大小限制 5MB
    """
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="仅支持 JPG/PNG 格式的图片"
        )

    # 验证文件大小（5MB）
    content = await file.read()
    file_size = len(content)
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="文件大小不能超过 5MB"
        )

    # 生成唯一文件名
    file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
    object_name = f"avatars/{current_user.id}_{uuid.uuid4()}.{file_extension}"

    # 上传到 MinIO
    try:
        minio_client = MinIOClient(bucket_name=settings.MINIO_AVATAR_BUCKET)
        avatar_url = minio_client.upload_bytes(
            object_name=object_name,
            data=content,
            content_type=file.content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"头像上传失败: {str(e)}"
        )

    # 更新用户头像 URL
    user_service.update_avatar(db, current_user, avatar_url)

    return {"avatar_url": avatar_url}


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    验证邮箱

    - 验证令牌并更新邮箱验证状态
    - 令牌使用后自动失效
    """
    success = user_service.verify_email(db, request.token)

    if not success:
        raise HTTPException(status_code=400, detail="验证令牌无效或已过期")

    return {"message": "邮箱验证成功"}


@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest, 
    db: Session = Depends(get_db)
):
    """
    重新发送验证邮件

    - 生成新的验证令牌
    - 发送验证邮件到用户邮箱
    """
    token = user_service.resend_verification_email(db, request.email)

    # 如果用户存在且未验证，发送邮件
    if token:
        email_sent = send_verification_email(request.email, token)
        
        # 开发环境下如果发送失败，返回 token 便于测试
        if not email_sent and settings.DEBUG:
            return {
                "message": "验证邮件已发送（邮件发送失败，开发环境直接返回）",
                "verify_url": f"/verify-email?token={token}",
                "token": token,
            }

    # 无论邮箱是否存在都返回成功，防止邮箱枚举攻击
    return {
        "message": "如果该邮箱已注册且未验证，验证链接将发送至您的邮箱"
    }

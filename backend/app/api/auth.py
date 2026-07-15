"""
认证相关 API 路由
- POST /api/auth/register          用户注册
- POST /api/auth/login             用户登录
- GET  /api/auth/me                获取当前用户信息
- POST /api/auth/forgot-password   忘记密码
- POST /api/auth/reset-password    重置密码
- GET  /api/auth/reset-password-redirect    重置密码跳转（邮件链接用）
- GET  /api/auth/verify-email-redirect      邮箱验证跳转（邮件链接用）
- GET  /api/auth/profile           获取个人信息（含检测统计）
- PUT  /api/auth/profile           修改个人信息
- PUT  /api/auth/password          修改密码
- POST /api/auth/avatar            上传头像
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
)
from app.core.email import send_password_reset_email
from app.services.user_service import user_service
from app.storage.minio_client import MinIOClient
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
    """
    user = user_service.register(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
    )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录

    - 返回 JWT access_token（24小时有效）
    - 后续请求在 Header 中携带：Authorization: Bearer <token>
    """
    user = user_service.login(
        db=db,
        username=request.username,
        password=request.password,
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
    忘记密码 - 发送验证码

    - 验证邮箱是否已注册
    - 如果邮箱存在，生成6位验证码并发送邮件
    """
    user = user_service.get_user_by_email(db, request.email)

    if user:
        code = user_service.generate_reset_verification_code(db, request.email)
        if code:
            try:
                send_password_reset_email(request.email, code)
            except Exception as e:
                print(f"发送验证码邮件失败: {str(e)}")
        
        return {
            "message": "如果该邮箱已注册，您将收到一封验证码邮件",
            "email_exists": True,
        }
    else:
        return {
            "message": "该邮箱未注册，请检查输入或先注册",
            "email_exists": False,
        }


@router.post("/verify-reset-code")
async def verify_reset_code(request: dict, db: Session = Depends(get_db)):
    """
    验证密码重置验证码

    - 验证邮箱和验证码是否匹配
    """
    email = request.get("email")
    code = request.get("code")

    if not email or not code:
        raise HTTPException(status_code=400, detail="邮箱和验证码不能为空")

    is_valid = user_service.verify_reset_code(db, email, code)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="验证码无效或已过期")

    return {
        "message": "验证码验证成功",
        "valid": True,
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    重置密码

    - 通过邮箱和验证码验证账号，更新密码
    """
    success = user_service.reset_password_with_code(db, request.email, request.code, request.new_password)

    if not success:
        raise HTTPException(status_code=400, detail="验证码无效或已过期，请重新申请")

    return {"message": "密码重置成功"}


@router.get("/reset-password-redirect")
async def reset_password_redirect(token: str):
    """
    重置密码跳转（邮件链接用）
    
    用户点击邮件中的链接先到后端，后端再重定向到前端，
    绕过QQ邮箱等邮件客户端的安全检查
    """
    from fastapi.responses import RedirectResponse
    
    redirect_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    return RedirectResponse(url=redirect_url)


@router.get("/verify-email-redirect")
async def verify_email_redirect(token: str):
    """
    邮箱验证跳转（邮件链接用）
    
    用户点击邮件中的链接先到后端，后端再重定向到前端，
    绕过QQ邮箱等邮件客户端的安全检查
    """
    from fastapi.responses import RedirectResponse
    
    redirect_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    return RedirectResponse(url=redirect_url)


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

    - 上传至本地存储目录
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
    avatar_filename = f"{current_user.id}_{uuid.uuid4()}.{file_extension}"

    # 确保头像目录存在
    upload_dir = os.path.join(os.path.dirname(__file__), "../../uploads/avatars")
    os.makedirs(upload_dir, exist_ok=True)

    # 保存文件
    file_path = os.path.join(upload_dir, avatar_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # 构建头像 URL
    avatar_url = f"/uploads/avatars/{avatar_filename}"

    # 更新用户头像 URL
    user_service.update_avatar(db, current_user, avatar_url)

    return {"avatar_url": avatar_url}

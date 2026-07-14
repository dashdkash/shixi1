"""
智能对话 API 路由
- POST /api/chat/stream  流式对话接口
- POST /api/chat/upload  图片上传接口（对话附件用）
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from app.agent.detection_agent import detection_agent
from app.core.security import decode_access_token
from app.database.session import SessionLocal, get_db
from app.entity.db_models import ChatMessage, ChatSession
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["智能对话"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """从 JWT Token 中解析当前用户"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception
    return {"id": int(user_id_str)}


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    stream: bool = True
    image_path: Optional[str] = None
    session_id: Optional[int] = None  # 会话 ID，为空则自动创建新会话


async def get_current_user_optional(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """可选的用户认证，允许未认证访问"""
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is not None:
            return {"id": int(user_id_str)}
    except (JWTError, ValueError):
        pass
    return None


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    accept_language: str = Header(None),
    current_user=Depends(get_current_user_optional),
):
    """
    流式对话接口 — 调用真实的 DetectionAgent

    通过 SSE 返回 Agent 的思考过程、工具调用和最终结果
    同时持久化会话和消息到数据库
    """
    user_id = current_user["id"] if current_user else None

    # ── 创建或获取会话 ──
    db = SessionLocal()
    try:
        if request.session_id:
            session = db.query(ChatSession).filter(
                ChatSession.id == request.session_id,
                ChatSession.user_id == user_id,
            ).first()
        else:
            session = None

        if not session:
            session = ChatSession(
                user_id=user_id or 0,
                session_uuid=str(uuid.uuid4()),
                title=request.message[:50],  # 取前50个字符作为标题
                status="active",
                message_count=0,
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        # 保存用户消息
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=request.message,
            agent_used="detection",
        )
        db.add(user_msg)
        db.commit()
        session_id = session.id
    finally:
        db.close()

    async def event_stream():
        # 先发送 session_id，让前端知道当前会话
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

        full_content = ""
        async for event in detection_agent.chat_stream(
            message=request.message,
            image_path=request.image_path,
        ):
            if event.get("type") == "text_chunk":
                full_content += event.get("content", "")
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # 保存 AI 回复到数据库
        db2 = SessionLocal()
        try:
            ai_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=full_content or "[无响应]",
                agent_used="detection",
            )
            db2.add(ai_msg)
            # 更新会话统计
            chat_session = db2.query(ChatSession).filter(ChatSession.id == session_id).first()
            if chat_session:
                chat_session.message_count += 2  # user + assistant
                chat_session.last_message_at = datetime.now()
            db2.commit()
        except Exception as e:
            logger.error("保存对话消息失败: %s", str(e), exc_info=True)
        finally:
            db2.close()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/")
async def chat(
    request: ChatRequest,
    current_user=Depends(get_current_user),
):
    """
    非流式对话接口
    """
    result = await detection_agent.chat(
        message=request.message,
        image_path=request.image_path,
    )
    return {
        "content": result["output"],
        "intermediate_steps": result.get("intermediate_steps", []),
    }


@router.post("/upload")
async def upload_chat_image(
    file: UploadFile = File(..., description="图片文件"),
    current_user=Depends(get_current_user_optional),
):
    """
    上传对话附件图片，返回服务器端文件路径

    前端先将图片上传到此接口，获取 image_path 后再发起 /chat/stream 请求
    """
    # 创建上传目录
    upload_dir = os.path.join(os.getcwd(), "uploads", "chat")
    os.makedirs(upload_dir, exist_ok=True)

    # 保存文件
    filename = file.filename or "image.jpg"
    suffix = os.path.splitext(filename)[1] or ".jpg"
    save_path = os.path.join(upload_dir, f"{os.urandom(8).hex()}{suffix}")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    return {"image_path": save_path, "filename": filename}

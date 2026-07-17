"""
智能对话 API 路由
- POST /api/chat/sessions    创建新对话
- GET  /api/chat/sessions    获取对话列表
- DELETE /api/chat/sessions/{id}  删除对话
- POST /api/chat/stream      流式对话接口
- POST /api/chat/upload      图片上传接口（对话附件用）
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from app.agent.detection_agent import detection_agent
from app.agent.memory import conversation_memory
from app.core.security import decode_access_token
from app.database.session import SessionLocal, get_db
from app.entity.db_models import ChatMessage, ChatSession
from app.services.detection_service import current_user_id as user_id_ctx
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
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
    video_path: Optional[str] = None
    session_id: Optional[int] = None  # 会话 ID，为空则自动创建新会话


class CreateSessionRequest(BaseModel):
    """创建新对话请求"""
    title: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# 会话管理接口
# ══════════════════════════════════════════════════════════════


@router.post("/sessions", status_code=201)
async def create_session(
    request: CreateSessionRequest,
    current_user=Depends(get_current_user),
):
    """
    创建新对话会话

    前端点击“新对话”按钮时调用，返回新建会话的 ID 和基本信息。
    后续发消息时带上 session_id 即可在该会话中对话。
    """
    db = SessionLocal()
    try:
        session = ChatSession(
            user_id=current_user["id"],
            session_uuid=str(uuid.uuid4()),
            title=request.title or "新对话",
            status="active",
            message_count=0,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info("创建新对话: session_id=%d, user_id=%d", session.id, current_user["id"])

        return {
            "id": session.id,
            "session_uuid": session.session_uuid,
            "title": session.title,
            "status": session.status,
            "message_count": session.message_count,
            "created_at": session.created_at.isoformat(),
        }
    except Exception as e:
        logger.error("创建对话失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="创建对话失败")
    finally:
        db.close()


@router.get("/sessions")
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
):
    """
    获取当前用户的对话列表
    """
    from sqlalchemy import desc

    db = SessionLocal()
    try:
        query = db.query(ChatSession).filter(
            ChatSession.user_id == current_user["id"],
        ).order_by(
            desc(ChatSession.last_message_at).nulls_last(),
            desc(ChatSession.created_at),
        )

        total = query.count()
        sessions = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": [
                {
                    "id": s.id,
                    "session_uuid": s.session_uuid,
                    "title": s.title or "未命名对话",
                    "status": s.status,
                    "message_count": s.message_count,
                    "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
                    "created_at": s.created_at.isoformat(),
                }
                for s in sessions
            ],
        }
    finally:
        db.close()

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: int,
    current_user=Depends(get_current_user),
):
    """
    Get all messages for a session.
    """
    db = SessionLocal()
    try:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user["id"],
            )
            .first()
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

        return {
            "session_id": session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
        }

    finally:
        db.close()
@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user=Depends(get_current_user),
):
    """
    删除对话会话及其所有消息
    """
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user["id"],
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="对话不存在")

        # 删除该会话下的所有消息
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
        db.delete(session)
        db.commit()

        logger.info("删除对话: session_id=%d, user_id=%d", session_id, current_user["id"])

        return {"message": "对话已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除对话失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="删除对话失败")
    finally:
        db.close()


@router.post("/clear")
async def clear_session(
    session_id: int,
    current_user=Depends(get_current_user),
):
    """
    清空指定会话的 Redis 对话历史

    注意：DB 中的会话和消息记录不受影响，仅清除 Redis 中的 Agent 记忆。
    """
    user_id = current_user["id"]
    conversation_memory.clear_session(user_id, str(session_id))
    logger.info("清空会话历史: session_id=%d, user_id=%d", session_id, user_id)
    return {"message": f"会话 {session_id} 的对话记忆已清空"}


# ══════════════════════════════════════════════════════════════
# 对话消息接口
# ══════════════════════════════════════════════════════════════


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
        # 设置用户上下文变量，让 detection_service 能获取到 user_id
        user_id_ctx.set(user_id)

        # 先发送 session_id，让前端知道当前会话
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

        full_content = ""
        async for event in detection_agent.chat_stream(
            message=request.message,
            user_id=user_id or 0,
            session_id=str(session_id),
            image_path=request.image_path,
            video_path=request.video_path,
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
            "X-Accel-Buffering": "no",
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
    # 设置用户上下文变量，让 detection_service 能获取到 user_id
    user_id_ctx.set(current_user["id"])

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

    # 根据文件类型返回不同字段
    video_suffixes = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}
    if suffix.lower() in video_suffixes:
        return {"video_path": save_path, "filename": filename}
    return {"image_path": save_path, "filename": filename}

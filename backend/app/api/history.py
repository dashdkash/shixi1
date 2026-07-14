"""
历史记录 API 路由
- GET /api/history/detection  获取检测历史记录
- GET /api/history/detection/{id}  获取检测任务详情
- GET /api/history/chat  获取对话历史记录
- GET /api/history/chat/{id}  获取对话详情
"""

from datetime import datetime

from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.db_models import ChatMessage, ChatSession, DetectionResult, DetectionTask
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/history", tags=["历史记录"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
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


@router.get("/detection")
async def get_detection_history(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取检测历史记录

    Args:
        page: 页码
        page_size: 每页数量
    """
    query = db.query(DetectionTask).filter(
        DetectionTask.user_id == current_user["id"]
    ).order_by(DetectionTask.created_at.desc())

    total = query.count()
    tasks = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "total_images": task.total_images,
                "total_objects": task.total_objects,
                "total_inference_time": task.total_inference_time,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }
            for task in tasks
        ],
    }


@router.get("/detection/{task_id}")
async def get_detection_detail(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取检测任务详情

    Args:
        task_id: 任务 ID
    """
    task = db.query(DetectionTask).filter(
        DetectionTask.id == task_id,
        DetectionTask.user_id == current_user["id"],
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="检测任务不存在")

    results = db.query(DetectionResult).filter(
        DetectionResult.task_id == task_id
    ).all()

    results_by_image = {}
    for result in results:
        image_path = result.image_path
        if image_path not in results_by_image:
            results_by_image[image_path] = {
                "image_path": image_path,
                "inference_time": result.inference_time,
                "image_width": result.image_width,
                "image_height": result.image_height,
                "objects": [],
            }
        results_by_image[image_path]["objects"].append({
            "class_name": result.class_name,
            "class_name_cn": result.class_name_cn,
            "class_id": result.class_id,
            "confidence": result.confidence,
            "bbox": result.bbox,
        })

    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "total_images": task.total_images,
        "total_objects": task.total_objects,
        "total_inference_time": task.total_inference_time,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "images": list(results_by_image.values()),
    }


@router.get("/chat")
async def get_chat_history(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取对话历史记录

    Args:
        page: 页码
        page_size: 每页数量
    """
    from sqlalchemy import desc
    query = db.query(ChatSession).filter(
        ChatSession.user_id == current_user["id"]
    ).order_by(desc(ChatSession.last_message_at).nulls_last(), desc(ChatSession.created_at))

    total = query.count()
    sessions = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "id": session.id,
                "session_uuid": session.session_uuid,
                "title": session.title or "未命名对话",
                "message_count": session.message_count,
                "status": session.status,
                "last_message_at": session.last_message_at.isoformat() if session.last_message_at else None,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            }
            for session in sessions
        ],
    }


@router.get("/chat/{session_id}")
async def get_chat_detail(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取对话详情

    Args:
        session_id: 会话 ID
    """
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user["id"],
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="对话会话不存在")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()

    return {
        "id": session.id,
        "session_uuid": session.session_uuid,
        "title": session.title or "未命名对话",
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "agent_used": msg.agent_used,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }

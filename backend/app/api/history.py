"""
历史记录 API 路由
- GET /api/history/detection  获取检测历史记录
- GET /api/history/detection/{id}  获取检测任务详情
- GET /api/history/image-proxy/{result_id}  标注图片代理
- GET /api/history/chat  获取对话历史记录
- GET /api/history/chat/{id}  获取对话详情
"""

from datetime import datetime

from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.db_models import ChatMessage, ChatSession, DetectionResult, DetectionTask
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
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

    # 批量查询所有任务的检测结果（用于获取预览图和 top_classes）
    task_ids = [task.id for task in tasks]
    all_results = (
        db.query(DetectionResult)
        .filter(DetectionResult.task_id.in_(task_ids))
        .all()
    ) if task_ids else []

    # 按 task_id 分组
    results_map: dict = {}
    for r in all_results:
        results_map.setdefault(r.task_id, []).append(r)

    data = []
    for task in tasks:
        task_results = results_map.get(task.id, [])
        # 预览图：取第一张图的 annotated_image_url
        preview_image_url = None
        first_result_id = None
        if task_results:
            preview_image_url = task_results[0].annotated_image_url
            first_result_id = task_results[0].id
        # top_classes：去重取前 5 个中文名（过滤掉占位记录）
        class_names_cn = list(dict.fromkeys(
            r.class_name_cn or r.class_name
            for r in task_results
            if not (r.class_name == "no_detection" and r.class_id == -1)
        ))[:5]
        data.append({
            "id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "total_inference_time": round(task.total_inference_time, 2) if task.total_inference_time is not None else None,
            "preview_image_url": preview_image_url,
            "first_result_id": first_result_id,
            "top_classes": class_names_cn,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": data,
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
    first_result_id_by_image = {}
    for result in results:
        image_path = result.image_path
        if image_path not in results_by_image:
            results_by_image[image_path] = {
                "image_path": image_path,
                "annotated_image_url": result.annotated_image_url,
                "inference_time": round(result.inference_time, 2) if result.inference_time is not None else None,
                "image_width": result.image_width,
                "image_height": result.image_height,
                "objects": [],
            }
            first_result_id_by_image[image_path] = result.id
        # 跳过占位记录（no_detection），不在目标列表中显示
        if result.class_name == "no_detection" and result.class_id == -1:
            continue
        results_by_image[image_path]["objects"].append({
            "class_name": result.class_name,
            "class_name_cn": result.class_name_cn,
            "class_id": result.class_id,
            "confidence": result.confidence,
            "bbox": result.bbox,
        })

    images_list = list(results_by_image.values())
    # 为每张图片附加 result_id，用于图片代理接口
    for img, result_id in zip(images_list, first_result_id_by_image.values()):
        img["result_id"] = result_id

    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "total_images": task.total_images,
        "total_objects": task.total_objects,
        "total_inference_time": round(task.total_inference_time, 2) if task.total_inference_time is not None else None,
        "annotated_video_url": task.annotated_video_url,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "images": images_list,
    }


@router.get("/image-proxy/{result_id}")
async def get_detection_image_proxy(
    result_id: int,
    thumb: bool = False,
    db: Session = Depends(get_db),
):
    """通过 DetectionResult ID 代理访问标注图片（解决 MinIO 跨端口问题）

    Args:
        result_id: DetectionResult ID
        thumb: 是否返回缩略图（宽度 480px，JPEG 质量 80）
    """
    result = (
        db.query(DetectionResult)
        .filter(DetectionResult.id == result_id)
        .first()
    )
    if not result or not result.annotated_image_url:
        raise HTTPException(status_code=404, detail="标注图片不存在")

    try:
        from urllib.parse import urlparse, unquote
        from app.storage.minio_client import MinIOClient

        parsed = urlparse(result.annotated_image_url)
        path_parts = parsed.path.lstrip("/").split("/", 1)
        if len(path_parts) < 2:
            raise HTTPException(status_code=404, detail="无效的 MinIO 路径")
        object_name = unquote(path_parts[1])

        mc = MinIOClient()
        data = mc.client.get_object(mc.bucket_name, object_name)
        image_bytes = data.read()
        data.close()

        # 判断图片格式
        content_type = "image/jpeg"
        if object_name.lower().endswith(".png") and not thumb:
            content_type = "image/png"

        # 缩略图模式：缩放至宽度 480px，转为 JPEG
        if thumb:
            from io import BytesIO
            from PIL import Image

            img = Image.open(BytesIO(image_bytes))
            img = img.convert("RGB")
            max_width = 480
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=80, optimize=True)
            image_bytes = buf.getvalue()
            content_type = "image/jpeg"

        return Response(
            content=image_bytes,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片失败: {str(e)}")


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
                "tool_result": msg.tool_result,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }

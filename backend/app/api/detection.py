"""
检测 API 路由

接口列表：
  - POST /api/detection/upload    批量上传图片并检测（原有接口）
  - GET  /api/detection/tasks     获取检测任务列表（原有接口）
  - GET  /api/detection/tasks/{id} 获取检测任务详情（原有接口）
  - POST /api/detection/single    单图检测（快捷检测）
  - POST /api/detection/batch     批量检测（快捷检测）
  - POST /api/detection/zip       ZIP文件检测（快捷检测）
  - GET  /api/detection/status/{task_id} 查询任务状态（快捷检测）
"""

import json
import os
import tempfile
import uuid
from datetime import datetime
from typing import List

from app.core.security import decode_access_token
from app.database.session import get_db, SessionLocal
from app.entity.db_models import DetectionResult, DetectionTask, DetectionScene
from app.services.detection_service import detection_service
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
import random
from PIL import Image
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/detection", tags=["检测"])

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


def detect_image(image_path: str, scene_name: str = "weed_detection") -> dict:
    """
    模拟图像检测

    Args:
        image_path: 图像路径
        scene_name: 场景名称

    Returns:
        检测结果
    """
    try:
        img = Image.open(image_path)
        width, height = img.size

        results = []
        categories = ["杂草", "作物", "土壤", "石头"]
        categories_en = ["weed", "crop", "soil", "stone"]

        random.seed(hash(image_path))

        num_objects = random.randint(1, 5)
        for i in range(num_objects):
            x1 = random.randint(0, width - 100)
            y1 = random.randint(0, height - 100)
            x2 = x1 + random.randint(50, 150)
            y2 = y1 + random.randint(50, 150)

            class_idx = random.randint(0, len(categories) - 1)

            results.append({
                "class_name": categories_en[class_idx],
                "class_name_cn": categories[class_idx],
                "class_id": class_idx,
                "confidence": round(random.uniform(0.5, 0.99), 4),
                "bbox": [x1, y1, x2, y2],
            })

        return {
            "success": True,
            "width": width,
            "height": height,
            "objects": results,
            "inference_time": round(random.uniform(50, 200), 2),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/upload")
async def upload_and_detect(
    files: List[UploadFile] = File(...),
    scene_id: int = 1,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    accept_language: str = Header(None),
):
    """
    批量上传图片并检测

    Args:
        files: 图片文件列表
        scene_id: 检测场景 ID
        accept_language: 语言偏好

    Returns:
        检测任务结果
    """
    if not files:
        raise HTTPException(status_code=400, detail="请选择图片文件")

    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    lang = "zh"
    if accept_language and "en" in accept_language.lower():
        lang = "en"

    scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
    if not scene:
        scene = DetectionScene(
            id=scene_id,
            name="weed_detection",
            display_name="杂草检测",
            category="agriculture",
            class_names=["weed", "crop", "soil", "stone"],
            class_names_cn={"weed": "杂草", "crop": "作物", "soil": "土壤", "stone": "石头"},
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)
    scene_name = scene.name

    task = DetectionTask(
        user_id=current_user["id"],
        scene_id=scene_id,
        task_type="batch",
        status="processing",
        total_images=len(files),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    results = []
    total_objects = 0
    total_time = 0

    for file in files:
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
            results.append({
                "filename": file.filename,
                "success": False,
                "error": "不支持的文件格式" if lang == "zh" else "Unsupported file format",
            })
            continue

        file_ext = os.path.splitext(file.filename)[1]
        file_uuid = str(uuid.uuid4())
        file_path = os.path.join(upload_dir, f"{file_uuid}{file_ext}")

        with open(file_path, "wb") as f:
            f.write(await file.read())

        detect_result = detect_image(file_path, scene_name)

        if detect_result["success"]:
            results.append({
                "filename": file.filename,
                "success": True,
                "width": detect_result["width"],
                "height": detect_result["height"],
                "objects": detect_result["objects"],
                "inference_time": detect_result["inference_time"],
            })

            for obj in detect_result["objects"]:
                result = DetectionResult(
                    task_id=task.id,
                    image_path=file_path,
                    class_name=obj["class_name"],
                    class_name_cn=obj["class_name_cn"],
                    class_id=obj["class_id"],
                    confidence=obj["confidence"],
                    bbox=obj["bbox"],
                    inference_time=detect_result["inference_time"],
                    image_width=detect_result["width"],
                    image_height=detect_result["height"],
                )
                db.add(result)

            total_objects += len(detect_result["objects"])
            total_time += detect_result["inference_time"]
        else:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": detect_result["error"],
            })

        os.remove(file_path)

    task.status = "completed"
    task.total_objects = total_objects
    task.total_inference_time = total_time
    task.completed_at = datetime.now()
    db.commit()

    return {
        "task_id": task.id,
        "total_images": len(files),
        "success_count": sum(1 for r in results if r["success"]),
        "failed_count": sum(1 for r in results if not r["success"]),
        "total_objects": total_objects,
        "total_time": round(total_time, 2),
        "results": results,
    }


@router.get("/tasks")
async def get_detection_tasks(
    page: int = 1,
    page_size: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取检测任务列表

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


@router.get("/tasks/{task_id}")
async def get_detection_task_detail(
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

    return {
        "id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "total_images": task.total_images,
        "total_objects": task.total_objects,
        "total_inference_time": task.total_inference_time,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "results": [
            {
                "id": r.id,
                "image_path": r.image_path,
                "class_name": r.class_name,
                "class_name_cn": r.class_name_cn,
                "class_id": r.class_id,
                "confidence": r.confidence,
                "bbox": r.bbox,
                "inference_time": r.inference_time,
                "image_width": r.image_width,
                "image_height": r.image_height,
            }
            for r in results
        ],
    }


# ════════════════════════════════════════════════════════════════
# 快捷检测接口（跳过 LLM，直接调用检测服务）
# ════════════════════════════════════════════════════════════════


@router.post("/single", summary="单图检测")
async def detect_single_api(
    file: UploadFile = File(..., description="检测图片"),
    conf: float = Form(0.25, description="置信度阈值"),
    scene_id: int = Form(None, description="场景 ID"),
    current_user=Depends(get_current_user),
):
    """
    快捷单图检测（跳过 LLM，直接调用 YOLO）
    """
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = detection_service.detect_single(
            image_path=tmp_path,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user["id"],
        )
        result["filename"] = file.filename
        return result
    finally:
        os.unlink(tmp_path)


@router.post("/batch", summary="批量检测")
async def detect_batch_api(
    files: list[UploadFile] = File(..., description="多张图片"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    current_user=Depends(get_current_user),
):
    """
    快捷批量检测
    """
    temp_paths = []
    try:
        for file in files:
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                content = await file.read()
                tmp.write(content)
                temp_paths.append(tmp.name)

        result = detection_service.detect_batch(
            image_paths=temp_paths,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user["id"],
        )
        return result
    finally:
        for path in temp_paths:
            try:
                os.unlink(path)
            except Exception:
                pass


@router.post("/zip", summary="ZIP 文件检测")
async def detect_zip_api(
    file: UploadFile = File(..., description="ZIP 压缩包"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    current_user=Depends(get_current_user),
):
    """
    快捷 ZIP 检测：解压 ZIP 并批量检测其中所有图片
    """
    suffix = os.path.splitext(file.filename)[1] or ".zip"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = detection_service.detect_zip(
            zip_path=tmp_path,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user["id"],
        )
        return result
    finally:
        os.unlink(tmp_path)


@router.get("/status/{task_id}", summary="查询检测任务状态")
async def get_detection_status(
    task_id: int,
    current_user=Depends(get_current_user),
):
    """查询检测任务状态"""
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return JSONResponse(
                status_code=404,
                content={"error": "任务不存在"},
            )
        return {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
    finally:
        db.close()
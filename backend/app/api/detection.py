"""
<<<<<<< HEAD
检测 API 路由

接口列表：
  - POST /api/detection/upload    批量上传图片并检测（原有接口）
  - GET  /api/detection/tasks     获取检测任务列表（原有接口）
  - GET  /api/detection/tasks/{id} 获取检测任务详情（原有接口）
  - POST /api/detection/single    单图检测（快捷检测）
  - POST /api/detection/batch     批量检测（快捷检测）
  - POST /api/detection/zip       ZIP文件检测（快捷检测）
  - GET  /api/detection/status/{task_id} 查询任务状态（快捷检测）
=======
检测 API 路由 — 快捷检测接口（跳过 LLM，直接调用 YOLO）

接口列表：
  - POST /api/detection/single     单图检测
  - POST /api/detection/batch      批量检测
  - POST /api/detection/zip        ZIP 文件检测
  - GET  /api/detection/status/:id 查询任务状态
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
"""

import os
import tempfile
<<<<<<< HEAD
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
=======

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14

from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionTask
from app.services.detection_service import detection_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/detection", tags=["快捷检测"])


<<<<<<< HEAD
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
=======
@router.post("/single", summary="单图检测")
async def detect_single_api(
    file: UploadFile = File(..., description="检测图片"),
    conf: float = Form(0.25, description="置信度阈值"),
    scene_id: int = Form(None, description="场景 ID"),
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
    current_user=Depends(get_current_user),
):
    """
    快捷单图检测（跳过 LLM，直接调用 YOLO）
    """
    filename = file.filename or ""
    suffix = os.path.splitext(filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = detection_service.detect_single(
            image_path=tmp_path,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
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
            if file.filename is None:
                continue   # 跳过无文件名的上传
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                content = await file.read()
                tmp.write(content)
                temp_paths.append(tmp.name)

        result = detection_service.detect_batch(
            image_paths=temp_paths,
            conf=conf,
            scene_id=scene_id,
            user_id=current_user.id,
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
    if file.filename is None:
        raise ValueError("上传文件无文件名")
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
            user_id=current_user.id,
        )
        return result
    finally:
        os.unlink(tmp_path)


@router.get("/status/{task_id}", summary="查询检测任务状态")
async def get_detection_status(
    task_id: int,
    current_user=Depends(get_current_user),
):
<<<<<<< HEAD
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
=======
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return JSONResponse(
<<<<<<< HEAD
                status_code=404,
=======
                status_code=status.HTTP_404_NOT_FOUND,
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
                content={"error": "任务不存在"},
            )
        return {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "completed_at": (
<<<<<<< HEAD
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "created_at": task.created_at.isoformat() if task.created_at else None,
=======
                task.completed_at.isoformat() if task.completed_at is not None else None
            ),
            "created_at": (
                task.created_at.isoformat() if task.created_at is not None else None
            ),
>>>>>>> e6dc0a786441135febc780558d63e5c7da7b7b14
        }
    finally:
        db.close()
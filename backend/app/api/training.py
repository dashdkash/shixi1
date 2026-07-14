# backend/app/api/training.py
"""
训练相关 API 路由

接口列表：
- POST /api/training/start       启动训练任务
- GET  /api/training/tasks       获取训练任务列表
- GET  /api/training/status/{task_id}     获取训练状态（含最新指标）
- GET  /api/training/metrics/{task_id}    获取训练指标历史（所有epoch）
- POST /api/training/stop/{task_id}       停止训练任务
- GET  /api/training/results/{task_uuid}  获取 results.csv 原始数据
"""

import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import get_db
from app.entity.db_models import DetectionScene, ModelVersion, TrainingTask
from app.entity.schemas import TrainingTaskCreate
from app.training.training_service import training_service

logger = get_logger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

router = APIRouter(prefix="/api/training", tags=["模型训练"])


@router.post("/start")
async def start_training(
    request: TrainingTaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    启动模型训练任务

    - **scene_id**: 关联的检测场景 ID
    - **model_name**: 基础模型 (yolov11n/s/m/l/x)
    - **epochs**: 训练轮数 (10-500)
    - **batch_size**: 批次大小 (1-64)
    - **device**: 训练设备 (cpu / 0 / 1)
    - **optimizer**: 优化器 (SGD / Adam / AdamW)
    - **lr0**: 初始学习率
    - **augment_config**: 数据增强配置 (JSON)
    """
    # 构造训练配置
    config = {
        "model_name": request.model_name,
        "epochs": request.epochs,
        "img_size": request.img_size,
        "batch_size": request.batch_size,
        "device": request.device,
        "optimizer": request.optimizer,
        "lr0": request.lr0,
        "augment_config": request.augment_config,
    }

    # 从场景获取数据集路径
    scene = (
        db.query(DetectionScene).filter(DetectionScene.id == request.scene_id).first()
    )
    if not scene:
        raise HTTPException(status_code=404, detail="检测场景不存在")

    # 尝试查找数据集路径（约定：backend/datasets/{场景名}/yolo_dataset/）
    # backend/app/api/training.py -> 向上3层到达 backend/
    api_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(api_dir)
    backend_dir = os.path.dirname(app_dir)

    # 使用场景的 name 作为数据集目录名
    scene_name = str(scene.name)
    dataset_path = os.path.join(
        backend_dir,
        settings.DATASET_BASE_DIR,
        scene_name,
    )

    logger.info("backend目录: %s", backend_dir)
    logger.info("数据集路径: %s", dataset_path)

    config["dataset_path"] = dataset_path

    # 检查 data.yaml 是否存在
    data_yaml = os.path.join(dataset_path, "data.yaml")
    if os.path.exists(data_yaml):
        config["data_yaml"] = data_yaml
    else:
        raise HTTPException(
            status_code=400,
            detail=f"data.yaml 不存在: {data_yaml}，请先完成数据集准备",
        )

    # 启动训练
    try:
        task = training_service.start_training(
            db=db,
            user_id=current_user.id,
            scene_id=request.scene_id,
            config=config,
        )
    except Exception as e:
        logger.error("启动训练失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动训练失败: {str(e)}")

    logger.info(
        "用户 %s 启动训练任务: scene=%s, model=%s, epochs=%d",
        current_user.username,
        scene.name,
        request.model_name,
        request.epochs,
    )

    return {
        "id": task.id,
        "task_uuid": task.task_uuid,
        "status": task.status,
        "model_name": task.model_name,
        "epochs": task.epochs,
        "message": "训练任务已创建，正在后台启动",
    }


@router.get("/tasks")
async def list_training_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取当前用户的训练任务列表"""
    tasks = training_service.get_task_list(db, user_id=current_user.id)
    return {"total": len(tasks), "items": tasks}


@router.get("/status/{task_id}")
async def get_training_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    获取训练任务状态

    返回任务基本信息、当前进度和最新epoch指标
    前端可轮询此接口实现实时监控
    """
    status = training_service.get_training_status(db, task_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.get("/metrics/{task_id}")
async def get_training_metrics(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    获取训练任务的所有epoch指标

    用于绘制完整的训练曲线（loss、mAP、precision、recall）
    """
    metrics = training_service.get_training_metrics(db, task_id)
    return {"task_id": task_id, "total": len(metrics), "metrics": metrics}


@router.post("/stop/{task_id}")
async def stop_training(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """停止正在运行的训练任务"""
    result = training_service.stop_training(db, task_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/results/{task_uuid}")
async def get_results_csv(
    task_uuid: str,
    current_user=Depends(get_current_user),
):
    """
    获取 Ultralytics 生成的原始 results.csv 文件

    可用于离线分析或导出到其他工具
    """
    results_path = os.path.join(
        settings.TRAIN_OUTPUT_DIR,
        f"task_{task_uuid}",
        "results.csv",
    )

    if not os.path.exists(results_path):
        raise HTTPException(status_code=404, detail="results.csv 文件不存在")

    return FileResponse(
        path=results_path,
        media_type="text/csv",
        filename=f"training_results_{task_uuid}.csv",
    )


@router.post("/validate/{task_id}")
async def validate_model(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    对已完成训练的模型执行验证集评估
    """
    result = training_service.validate_model(db, task_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/export/{task_id}")
async def export_model(
    task_id: int,
    version: str | None = None,
    description: str | None = None,
    set_default: bool = False,
    upload_minio: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    导出训练好的模型为正式版本

    - 复制 best.pt 到 models/ 目录
    - 运行评估获取最终指标
    - 保存评估报告 JSON
    - 创建 ModelVersion 记录
    - 可选上传到 MinIO
    """
    result = training_service.export_model(
        db=db,
        task_id=task_id,
        version=version,
        description=description,
        set_default=set_default,
        upload_minio=upload_minio,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    logger.info(
        "用户 %s 导出模型: task_id=%d, version=%s",
        current_user.username,
        task_id,
        result.get("version"),
    )

    return result


@router.get("/download/{task_id}")
async def download_model(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    下载训练好的模型权重文件（best.pt）
    """
    result = training_service.get_model_download_path(db, task_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    logger.info(
        "用户 %s 下载模型: task_id=%d, file=%s",
        current_user.username,
        task_id,
        result["filename"],
    )

    return FileResponse(
        path=result["file_path"],
        media_type="application/octet-stream",
        filename=result["filename"],
    )


@router.post("/predict")
async def predict_test_image(
    file: UploadFile = File(..., description="测试图片"),
    task_id: int = Form(..., description="训练任务 ID"),
    conf: float = Form(0.25, description="置信度阈值"),
    iou: float = Form(0.45, description="NMS IoU 阈值"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    上传测试图片，使用训练好的模型进行预测

    用于快速验证模型训练效果：
    1. 上传一张不在训练集/验证集中的测试图片
    2. 使用 best.pt 进行推理
    3. 返回检测结果（标注图 + 检测统计）
    """
    import base64
    import tempfile

    import cv2
    from ultralytics import YOLO

    # 验证文件类型
    allowed_types = {"image/jpeg", "image/png", "image/bmp", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}，支持: {', '.join(allowed_types)}",
        )

    # 查找训练任务
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    if str(task.status) != "completed":
        raise HTTPException(status_code=400, detail="训练任务未完成，无法进行预测")

    # 定位 best.pt
    weights_path = os.path.join(
        BACKEND_DIR,
        settings.TRAIN_OUTPUT_DIR,
        f"task_{task.task_uuid}",
        "weights",
        "best.pt",
    )
    if not os.path.exists(weights_path):
        raise HTTPException(status_code=404, detail="模型权重文件不存在")

    # 保存上传文件到临时目录
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(
        suffix=ext,
        delete=False,
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 加载模型并推理
        model = YOLO(weights_path)
        results = model.predict(
            source=tmp_path,
            conf=conf,
            iou=iou,
            imgsz=task.img_size,
            device="cpu",
            save=False,
            verbose=False,
        )

        # 解析检测结果
        result = results[0]
        detections = []
        total_objects = 0

        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names.get(cls_id, f"class_{cls_id}")
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                detections.append(
                    {
                        "class_name": cls_name,
                        "class_id": cls_id,
                        "confidence": round(confidence, 4),
                        "bbox": [
                            round(x1, 1),
                            round(y1, 1),
                            round(x2, 1),
                            round(y2, 1),
                        ],
                    }
                )
                total_objects += 1

        # 生成标注图
        annotated_img = result.plot()
        _, buffer = cv2.imencode(".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        annotated_base64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

        # 统计各类别数量
        class_counts = {}
        for det in detections:
            name = det["class_name"]
            class_counts[name] = class_counts.get(name, 0) + 1

        inference_val = result.speed.get("inference", 0)
        inference_time = round(float(inference_val) if inference_val is not None else 0.0, 2)

        return {
            "task_id": task_id,
            "task_uuid": task.task_uuid,
            "filename": file.filename,
            "total_objects": total_objects,
            "detections": detections,
            "class_counts": class_counts,
            "annotated_image": annotated_base64,
            "inference_time": inference_time,
        }

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/models")
async def list_models(
    scene_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    获取模型版本列表
    """
    query = db.query(ModelVersion)
    if scene_id:
        query = query.filter(ModelVersion.scene_id == scene_id)

    models = query.order_by(ModelVersion.created_at.desc()).all()

    return {
        "total": len(models),
        "items": [
            {
                "id": m.id,
                "scene_id": m.scene_id,
                "version": m.version,
                "model_name": m.model_name,
                "model_type": m.model_type,
                "status": m.status,
                "model_path": m.model_path,
                "map50": m.map50,
                "map50_95": m.map50_95,
                "precision": m.precision,
                "recall": m.recall,
                "file_size": m.file_size,
                "is_default": m.is_default,
                "created_at": str(m.created_at),
            }
            for m in models
        ],
    }


@router.post("/resume/{task_id}")
async def resume_training(
    task_id: int,
    request: TrainingTaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    从已有训练任务继续训练（续训）

    在已有训练结果基础上继续训练，可以设置新的总轮数。
    例如：上次训练了100轮，现在设置epochs=200，将继续训练到200轮。

    - **task_id**: 要续训的源任务ID（必须是已完成状态）
    - **epochs**: 新的总训练轮数（不是追加轮数）
    """
    source_task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not source_task:
        raise HTTPException(status_code=404, detail="源训练任务不存在")

    task_status = str(getattr(source_task, 'status', ''))
    if task_status != "completed":
        raise HTTPException(status_code=400, detail="源训练任务未完成，无法续训")

    last_pt_path = os.path.join(
        BACKEND_DIR,
        settings.TRAIN_OUTPUT_DIR,
        f"task_{source_task.task_uuid}",
        "weights",
        "last.pt",
    )
    if not os.path.exists(last_pt_path):
        raise HTTPException(status_code=400, detail=f"源任务的 last.pt 文件不存在")

    scene = (
        db.query(DetectionScene).filter(DetectionScene.id == request.scene_id).first()
    )
    if not scene:
        raise HTTPException(status_code=404, detail="检测场景不存在")

    scene_name = str(scene.name)
    dataset_path = os.path.join(
        BACKEND_DIR,
        settings.DATASET_BASE_DIR,
        scene_name,
    )

    config = {
        "model_name": request.model_name or source_task.model_name,
        "epochs": request.epochs,
        "img_size": request.img_size or source_task.img_size,
        "batch_size": request.batch_size or source_task.batch_size,
        "device": request.device or source_task.device,
        "optimizer": request.optimizer or source_task.optimizer,
        "lr0": request.lr0 or source_task.lr0,
        "augment_config": request.augment_config,
        "dataset_path": dataset_path,
    }

    data_yaml = os.path.join(dataset_path, "data.yaml")
    if os.path.exists(data_yaml):
        config["data_yaml"] = data_yaml
    else:
        raise HTTPException(
            status_code=400,
            detail=f"data.yaml 不存在: {data_yaml}",
        )

    try:
        task = training_service.resume_training(
            db=db,
            user_id=current_user.id,
            scene_id=request.scene_id,
            config=config,
            resume_from_task_id=task_id,
        )
    except Exception as e:
        logger.error("启动续训失败: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动续训失败: {str(e)}")

    logger.info(
        "用户 %s 启动续训任务: source_task=%d, model=%s, epochs=%d",
        current_user.username,
        task_id,
        config["model_name"],
        config["epochs"],
    )

    return {
        "id": task.id,
        "task_uuid": task.task_uuid,
        "status": task.status,
        "model_name": task.model_name,
        "epochs": task.epochs,
        "message": f"续训任务已创建，将从任务 {task_id} 的训练结果继续训练",
    }


@router.get("/scenes")
async def list_scenes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    获取检测场景列表
    """
    scenes = db.query(DetectionScene).filter(DetectionScene.is_active == True).all()
    return {
        "total": len(scenes),
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
                "category": s.category,
                "class_names": s.class_names,
            }
            for s in scenes
        ],
    }

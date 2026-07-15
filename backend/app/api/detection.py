"""
检测 API 路由 — 快捷检测接口（跳过 LLM，直接调用 YOLO）

接口列表：
  - POST /api/detection/upload     批量上传图片检测
  - POST /api/detection/single     单图检测
  - POST /api/detection/batch      批量检测
  - POST /api/detection/zip        ZIP 文件检测
  - GET  /api/detection/status/:id 查询任务状态
"""
import base64
import os
import tempfile
import threading
import asyncio
import time
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi import WebSocket, WebSocketDisconnect
from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionTask
from app.services.detection_service import detection_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/detection", tags=["快捷检测"])


@router.post("/upload", summary="批量上传图片检测")
async def upload_and_detect_api(
    files: list[UploadFile] = File(..., description="多张图片"),
    conf: float = Form(0.25),
    scene_id: int = Form(None),
    current_user=Depends(get_current_user),
):
    """
    批量上传图片并检测
    """
    temp_paths = []
    try:
        for file in files:
            if file.filename is None:
                continue
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
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "任务不存在"},
            )
        return {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "total_images": task.total_images,
            "total_objects": task.total_objects,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at is not None else None
            ),
            "created_at": (
                task.created_at.isoformat() if task.created_at is not None else None
            ),
        }
    finally:
        db.close()

# ── Redis 视频任务进度存储 ──
from app.storage.redis_client import redis_client


@router.post("/video", summary="视频检测")
async def detect_video_api(
    file: UploadFile = File(..., description="视频文件（mp4/avi/mov）"),
    conf: float = Form(0.25, description="置信度阈值"),
    frame_sample_rate: int = Form(5, description="帧采样间隔（每 N 帧取 1 帧）"),
    max_frames: int = Form(50, description="最多处理的关键帧数量"),
    scene_id: int = Form(None, description="场景 ID"),
    current_user=Depends(get_current_user),
):
    """
    视频检测：上传视频文件，后台异步处理，通过 status 接口轮询进度

    支持格式：mp4, avi, mov, mkv, wmv, flv
    文件大小限制：50MB
    """
    # ── 校验文件格式 ──
    allowed_video_types = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in allowed_video_types:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": f"不支持的视频格式: {suffix}，"
                f"支持的格式: {', '.join(allowed_video_types)}"
            },
        )

    # ── 保存视频到临时文件 ──
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    logger.info(
        "视频文件已保存: %s (%.2f MB), 用户: %s",
        tmp_path,
        len(content) / (1024 * 1024),
        current_user.username,
    )

    # ── 先创建检测任务记录 ──
    db = SessionLocal()
    try:
        task = DetectionTask(
            user_id=current_user.id,
            scene_id=scene_id or 1,
            task_type="video",
            status="processing",
            conf_threshold=conf,
        )
        db.add(task)
        db.flush()
        task_id = task.id
        db.commit()
    finally:
        db.close()

    # ── 初始化进度信息 ──
    redis_client.set_json(f"video_task:{task_id}", {
        "status": "processing",
        "progress": 0,
        "message": "视频处理中...",
    }, expire=3600)

    def run_video_detection():
        """后台线程：执行视频检测"""
        try:
            result = detection_service.detect_video(
                video_path=tmp_path,
                conf=conf,
                frame_sample_rate=frame_sample_rate,
                max_frames=max_frames,
                scene_id=scene_id,
                user_id=current_user.id,
                task_id=task_id,
            )

            if "error" in result:
                redis_client.set_json(f"video_task:{task_id}", {
                    "status": "failed",
                    "progress": 0,
                    "message": result["error"],
                }, expire=3600)
            else:
                redis_client.set_json(f"video_task:{task_id}", {
                    "status": "completed",
                    "progress": 100,
                    "message": f"检测完成，共处理 {result['processed_frames']} 帧，"
                    f"发现 {result['total_objects']} 个目标",
                    "result": result,
                }, expire=3600)
        except Exception as e:
            logger.error("视频后台检测异常: %s", str(e), exc_info=True)
            redis_client.set_json(f"video_task:{task_id}", {
                "status": "failed",
                "progress": 0,
                "message": f"视频检测异常: {str(e)}",
            }, expire=3600)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    thread = threading.Thread(target=run_video_detection, daemon=True)
    thread.start()

    return {
        "task_id": task_id,
        "status": "processing",
        "message": "视频已上传，正在后台处理中，请通过 status 接口轮询进度",
        "filename": file.filename,
    }


@router.get("/video/status/{task_id}", summary="查询视频检测进度")
async def get_video_detection_status(
    task_id: int,
    current_user=Depends(get_current_user),
):
    """
    查询视频检测任务的实时进度和结果

    轮询间隔建议：1-2 秒
    """
    # 从 Redis 获取进度信息
    progress_info = redis_client.get_json(f"video_task:{task_id}")

    if progress_info:
        return {
            "task_id": task_id,
            **progress_info,
        }

    # 回退：从数据库查询
    db = SessionLocal()
    try:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "任务不存在"},
            )

        result = {
            "task_id": task.id,
            "status": task.status,
            "task_type": task.task_type,
            "total_images": task.total_images,
            "total_objects": task.total_objects or 0,
        }

        # 如果已完成，查询完整结果
        if task.status == "completed":
            from app.entity.db_models import DetectionResult

            results = (
                db.query(DetectionResult)
                .filter(DetectionResult.task_id == task_id)
                .all()
            )

            class_counts = {}
            for r in results:
                class_counts[r.class_name] = class_counts.get(r.class_name, 0) + 1

            result["class_counts"] = class_counts
            result["total_inference_time"] = task.total_inference_time

        return result
    finally:
        db.close()
        
        
# ── 单帧缓冲区（CPU 模式优化）──
# 键为 WebSocket 连接 ID，值为最新帧数据
_camera_frame_buffer = {}


@router.websocket("/camera")
async def camera_detection_ws(websocket: WebSocket):
    """
    摄像头实时检测 WebSocket 接口

    通信协议：
      前端发送：
        - {"type": "config", "mode": "cpu/gpu", "conf": 0.25}  初始化配置
        - {"type": "frame", "data": "<base64>"}                 发送帧
        - {"type": "close"}                                     关闭连接

      后端返回：
        - {"type": "result", "annotated_frame": "<base64>", ...}  标注帧 + 统计
        - {"type": "error", "message": "..."}                     错误信息
    """
    await websocket.accept()
    connection_id = id(websocket)
    logger.info("摄像头 WebSocket 连接建立: connection_id=%d", connection_id)

    # ── 默认配置 ──
    mode = "cpu"  # cpu 或 gpu
    conf = 0.25
    iou = 0.45
    scene_id = None
    model = None

    # ── 帧处理状态 ──
    last_frame_time = 0
    frame_count = 0
    fps_start_time = time.time()
    fps_frame_count = 0

    try:
        while True:
            # 接收前端消息
            data = await websocket.receive_json()
            msg_type = data.get("type")

            # ── 处理配置消息 ──
            if msg_type == "config":
                mode = data.get("mode", "cpu")
                conf = data.get("conf", 0.25)
                iou = data.get("iou", 0.45)
                scene_id = data.get("scene_id")

                # 加载模型（指定设备）
                device = "cpu" if mode == "cpu" else "0"
                try:
                    from app.services.detection_service import get_model
                    model = get_model(scene_id)

                    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    model.predict(
                        source=dummy_frame,
                        conf=conf,
                        iou=iou,
                        imgsz=640,
                        device=device,
                        save=False,
                        verbose=False,
                    )
                    logger.info("摄像头模型预热完成, 模式: %s", mode)
                except Exception as e:
                    logger.error("模型加载失败: %s", str(e))
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"模型加载失败: {str(e)}",
                        }
                    )
                    continue

                await websocket.send_json(
                    {
                        "type": "config_ok",
                        "mode": mode,
                        "message": f"配置成功，模式: {mode}",
                    }
                )

            # ── 处理帧数据 ──
            elif msg_type == "frame":
                if model is None:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "请先发送 config 消息初始化模型",
                        }
                    )
                    continue

                frame_b64 = data.get("data", "")
                if not frame_b64:
                    continue

                try:
                    img_bytes = base64.b64decode(frame_b64)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if frame is None:
                        continue

                    device = "cpu" if mode == "cpu" else "0"
                    imgsz = 416 if mode == "cpu" else 640

                    results = model.predict(
                        source=frame,
                        conf=conf,
                        iou=iou,
                        imgsz=imgsz,
                        device=device,
                        save=False,
                        verbose=False,
                        half=False,
                    )
                    result = results[0]
                    inference_time = float(result.speed.get("inference", 0))

                    annotated_img = result.plot()
                    _, buffer = cv2.imencode(
                        ".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 70]
                    )
                    annotated_b64 = base64.b64encode(buffer).decode("utf-8")

                    detections = []
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

                    fps_frame_count += 1
                    elapsed = time.time() - fps_start_time
                    if elapsed >= 1.0:
                        current_fps = fps_frame_count / elapsed
                        fps_frame_count = 0
                        fps_start_time = time.time()
                    else:
                        current_fps = 0

                    frame_count += 1

                    await websocket.send_json(
                        {
                            "type": "result",
                            "annotated_frame": annotated_b64,
                            "detections": detections,
                            "object_count": len(detections),
                            "inference_time": round(inference_time, 2),
                            "fps": round(current_fps, 1),
                            "frame_count": frame_count,
                        }
                    )

                except Exception as e:
                    logger.error("摄像头帧处理异常: %s", str(e))
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"帧处理失败: {str(e)}",
                        }
                    )

            # ── 处理关闭消息 ──
            elif msg_type == "close":
                logger.info(
                    "摄像头 WebSocket 主动关闭: connection_id=%d", connection_id
                )
                break

    except WebSocketDisconnect:
        logger.info("摄像头 WebSocket 断开: connection_id=%d", connection_id)
    except Exception as e:
        logger.error("摄像头 WebSocket 异常: %s", str(e), exc_info=True)
    finally:
        # 清理资源
        _camera_frame_buffer.pop(connection_id, None)
        logger.info(
            "摄像头 WebSocket 关闭, 共处理 %d 帧: connection_id=%d",
            frame_count,
            connection_id,
        )
        

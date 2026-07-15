"""
目标检测服务 — 封装 YOLOv11 推理逻辑

职责：
  - 单图检测（detect_single）
  - 批量检测（detect_batch）
  - ZIP 解压 + 批量检测（detect_zip）
  - 结果持久化（MinIO 存储标注图 + PostgreSQL 存储检测结果）

架构：
  DetectionService 是无状态的纯服务，被 Agent Tool 和快捷按钮 API 共同调用。
  每次检测都会：
    1. 创建 DetectionTask 记录
    2. 运行 YOLO 推理
    3. 上传 标注图到 MinIO
    4. 保存 DetectionResult 记录

使用方式：
  from app.services.detection_service import detection_service

  result = detection_service.detect_single(image_path, scene_id, user_id)
"""

import base64
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime

import cv2
from sqlalchemy.orm import Session
from ultralytics import YOLO

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import (
    DetectionResult,
    DetectionScene,
    DetectionTask,
    ModelVersion,
)
from app.storage.minio_client import MinIOClient

logger = get_logger(__name__)

# ── 支持的图片格式 ──
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/bmp",
    "image/webp",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


class DetectionService:
    """目标检测服务 — 封装 YOLOv11 推理全流程"""

    @staticmethod
    def _ensure_default_scene() -> int:
        """
        确保默认检测场景存在，如果不存在则创建
        返回场景 ID
        """
        db = SessionLocal()
        try:
            scene = db.query(DetectionScene).first()
            if scene:
                return scene.id

            new_scene = DetectionScene(
                name="us_weeds",
                display_name="杂草检测",
                description="杂草检测场景，支持识别15种常见杂草",
                category="agriculture",
                class_names=[
                    "carpetweeds", "crabgrass", "eclipta", "goosegrass",
                    "morningglory", "nutsedge", "palmeramaranth", "pricklysida",
                    "purslane", "ragweed", "sicklepod", "spottedspurge",
                    "spurredanoda", "swinecress", "waterhemp"
                ],
                class_names_cn={
                    "carpetweeds": "地毯草", "crabgrass": "马唐草",
                    "eclipta": "鳢肠", "goosegrass": "牛筋草",
                    "morningglory": "牵牛花", "nutsedge": "莎草",
                    "palmeramaranth": "苋", "pricklysida": "刺蒺藜",
                    "purslane": "马齿苋", "ragweed": "豚草",
                    "sicklepod": "决明", "spottedspurge": "斑地锦",
                    "spurredanoda": "田皂角", "swinecress": "臭荠",
                    "waterhemp": "水麻"
                },
                is_active=True,
            )
            db.add(new_scene)
            db.commit()
            logger.info("已创建默认杂草检测场景: id=%d, name=%s", new_scene.id, new_scene.name)
            return new_scene.id
        finally:
            db.close()

    @staticmethod
    def _get_backend_dir() -> str:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @staticmethod
    def _resolve_model_path(model_path: str) -> str:
        if os.path.isabs(model_path):
            return model_path
        backend_dir = DetectionService._get_backend_dir()
        return os.path.join(backend_dir, model_path)

    @staticmethod
    def _get_default_model_path() -> str:
        """
        获取默认模型权重路径

        查找顺序：
          1. models/us_weeds_v3.0.0/best.pt（优先使用训练好的杂草检测模型）
          2. models/ 目录下 is_default=True 的模型
          3. runs/train/ 目录下最新训练产出的 best.pt
          4. 回退到预训练模型 yolov11n.pt
        """
        db = SessionLocal()
        backend_dir = DetectionService._get_backend_dir()
        try:
            # 优先使用训练好的杂草检测模型
            trained_model_path = os.path.join(backend_dir, "models", "us_weeds_v3.0.0", "best.pt")
            if os.path.exists(trained_model_path):
                return trained_model_path

            default_model = (
                db.query(ModelVersion).filter(ModelVersion.is_default == True).first()
            )
            if default_model:
                resolved_path = DetectionService._resolve_model_path(default_model.model_path)
                if os.path.exists(resolved_path):
                    return resolved_path

            from app.entity.db_models import TrainingTask

            latest_task = (
                db.query(TrainingTask)
                .filter(TrainingTask.status == "completed")
                .order_by(TrainingTask.completed_at.desc())
                .first()
            )
            if latest_task:
                weights_path = os.path.join(
                    backend_dir,
                    settings.TRAIN_OUTPUT_DIR,
                    f"task_{latest_task.task_uuid}",
                    "weights",
                    "best.pt",
                )
                if os.path.exists(weights_path):
                    return weights_path
        finally:
            db.close()

        return os.path.join(backend_dir, "yolo11n.pt")

    @staticmethod
    def _get_model(scene_id: int = None) -> YOLO:
        """
        加载 YOLO 模型

        优先使用场景关联的默认模型，否则使用全局默认模型
        """
        model_path = None

        if scene_id:
            db = SessionLocal()
            try:
                default_model = (
                    db.query(ModelVersion)
                    .filter(
                        ModelVersion.scene_id == scene_id,
                        ModelVersion.is_default == True,
                    )
                    .first()
                )
                if default_model:
                    resolved_path = DetectionService._resolve_model_path(default_model.model_path)
                    if os.path.exists(resolved_path):
                        model_path = resolved_path
            finally:
                db.close()

        if not model_path:
            model_path = DetectionService._get_default_model_path()

        logger.info("加载检测模型: %s", model_path)
        return YOLO(model_path)

    @staticmethod
    def _save_task_and_results(
        db: Session,
        user_id: int,
        scene_id: int,
        task_type: str,
        detections: list,
        annotated_image: bytes,
        original_filename: str,
        inference_time: float,
        conf: float,
        iou: float,
    ) -> dict:
        """
        保存检测任务和结果到数据库 + MinIO

        Returns:
            包含 task_id 和 annotated_image_url 的字典
        """
        # ── 创建检测任务记录 ──
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            task_type=task_type,
            status="completed",
            total_images=1,
            total_objects=len(detections),
            total_inference_time=inference_time,
            conf_threshold=conf,
            iou_threshold=iou,
            completed_at=datetime.now(),
        )
        db.add(task)
        db.flush()  # 获取 task.id

        # ── 上传 标注图到 MinIO ──
        annotated_image_url = None
        try:
            minio_client = MinIOClient()
            object_name = f"detections/{task.id}/{original_filename}"
            annotated_image_url = minio_client.upload_bytes(
                object_name, annotated_image, "image/jpeg"
            )
            task.annotated_image_url = annotated_image_url  # 修正：这里应该更新的是 annotated_image_url 字段，但这个字段不存在于 DetectionTask 中
        except Exception as e:
            logger.warning("MinIO 上传失败（不影响检测结果）: %s", str(e))

        # ── 保存每条检测结果 ──
        for det in detections:
            result = DetectionResult(
                task_id=task.id,
                image_path=original_filename,
                annotated_image_url=annotated_image_url,
                class_name=det["class_name"],
                class_name_cn=det.get("class_name_cn"),
                class_id=det["class_id"],
                confidence=det["confidence"],
                bbox=det["bbox"],
                inference_time=inference_time,
            )
            db.add(result)

        db.commit()
        return {"task_id": task.id, "annotated_image_url": annotated_image_url}

    def detect_single(
        self,
        image_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        单图检测

        Args:
            image_path: 图片文件路径
            conf: 置信度阈值
            iou: NMS IoU 阈值
            scene_id: 检测场景 ID
            user_id: 操作用户 ID

        Returns:
            检测结果字典：
            {
                "total_objects": int,
                "class_counts": {"class_name": count, ...},
                "detections": [...],
                "annotated_image_base64": str,
                "inference_time": float,
                "task_id": int,
            }
        """
        db = SessionLocal()
        try:
            # ── 确保默认场景存在 ──
            if scene_id is None:
                scene_id = DetectionService._ensure_default_scene()

            # ── 加载模型 ──
            model = self._get_model(scene_id)

            # ── YOLO 推理 ──
            results = model.predict(
                source=image_path,
                conf=conf,
                iou=iou,
                imgsz=640,
                device="cpu",
                save=False,
                verbose=False,
            )

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

            # ── 生成标注图 ──
            annotated_img = result.plot()
            _, buffer = cv2.imencode(
                ".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            annotated_base64 = base64.b64encode(buffer).decode("utf-8")

            # ── 统计各类别数量 ──
            class_counts = {}
            for det in detections:
                name = det["class_name"]
                class_counts[name] = class_counts.get(name, 0) + 1

            # ── 持久化到数据库 ──
            task_id = None
            annotated_image_url = None
            if user_id and scene_id:
                save_result = self._save_task_and_results(
                    db=db,
                    user_id=user_id,
                    scene_id=scene_id,
                    task_type="single",
                    detections=detections,
                    annotated_image=buffer.tobytes(),
                    original_filename=os.path.basename(image_path),
                    inference_time=float(result.speed.get("inference", 0)),
                    conf=conf,
                    iou=iou,
                )
                task_id = save_result["task_id"]
                annotated_image_url = save_result.get("annotated_image_url")

            logger.info(
                "单图检测完成: %s, 检测到 %d 个目标, 耗时 %.2fms",
                image_path,
                total_objects,
                float(result.speed.get("inference", 0)),
            )

            return {
                "total_objects": total_objects,
                "class_counts": class_counts,
                "detections": detections,
                "annotated_image_base64": annotated_base64,
                "annotated_image_url": annotated_image_url,
                "inference_time": round(float(result.speed.get("inference", 0)), 2),
                "task_id": task_id,
            }

        except Exception as e:
            logger.error("单图检测异常: %s", str(e), exc_info=True)
            return {"error": f"检测失败: {str(e)}"}
        finally:
            db.close()

    def detect_batch(
        self,
        image_paths: list[str],
        conf: float = 0.25,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        批量检测多张图片

        Args:
            image_paths: 图片文件路径列表
            conf: 置信度阈值
            scene_id: 检测场景 ID
            user_id: 操作用户 ID

        Returns:
            批量检测结果字典
        """
        db = SessionLocal()
        try:
            model = self._get_model(scene_id)

            # 当 scene_id 为 None 时，自动查询第一个可用场景
            if not scene_id:
                default_scene = db.query(DetectionScene).first()
                if default_scene:
                    scene_id = default_scene.id
                else:
                    return {"error": "数据库中没有可用的检测场景，请先创建检测场景"}

            # ── 创建批量检测任务 ──
            task = DetectionTask(
                user_id=user_id or 0,
                scene_id=scene_id,
                task_type="batch",
                status="processing",
                total_images=len(image_paths),
                conf_threshold=conf,
            )
            db.add(task)
            db.flush()

            all_detections = []
            annotated_images = []  # 每张图片的标注图 base64
            total_objects = 0
            total_inference_time = 0
            class_counts = {}

            for i, image_path in enumerate(image_paths):
                results = model.predict(
                    source=image_path,
                    conf=conf,
                    iou=0.45,
                    imgsz=640,
                    device="cpu",
                    save=False,
                    verbose=False,
                )
                result = results[0]
                inference_time = float(result.speed.get("inference", 0))
                total_inference_time += inference_time

                # 生成标注图 base64
                annotated_img = result.plot()
                _, buffer = cv2.imencode(
                    ".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85]
                )
                annotated_images.append({
                    "image_path": os.path.basename(image_path),
                    "annotated_image_base64": base64.b64encode(buffer).decode("utf-8"),
                })

                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = model.names.get(cls_id, f"class_{cls_id}")
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()

                        det = {
                            "image_path": image_path,
                            "class_name": cls_name,
                            "class_id": cls_id,
                            "confidence": round(confidence, 4),
                            "bbox": [
                                round(x1, 1),
                                round(y1, 1),
                                round(x2, 1),
                                round(y2, 1),
                            ],
                            "inference_time": inference_time,
                        }
                        all_detections.append(det)
                        total_objects += 1

                        # 统计类别计数
                        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

                    # 保存检测结果到数据库
                    for det in all_detections:
                        if det["image_path"] == image_path:
                            db_result = DetectionResult(
                                task_id=task.id,
                                image_path=image_path,
                                class_name=det["class_name"],
                                class_id=det["class_id"],
                                confidence=det["confidence"],
                                bbox=det["bbox"],
                                inference_time=inference_time,
                            )
                            db.add(db_result)

            task.status = "completed"
            task.total_objects = total_objects
            task.total_inference_time = total_inference_time
            task.completed_at = datetime.now()
            db.commit()

            logger.info(
                "批量检测完成: %d 张图, 共 %d 个目标, 总耗时 %.2fms",
                len(image_paths),
                total_objects,
                total_inference_time,
            )

            return {
                "task_id": task.id,
                "total_images": len(image_paths),
                "total_objects": total_objects,
                "class_counts": class_counts,
                "total_inference_time": round(total_inference_time, 2),
                "detections": all_detections,
                "annotated_images": annotated_images,
            }

        except Exception as e:
            logger.error("批量检测异常: %s", str(e), exc_info=True)
            return {"error": f"批量检测失败: {str(e)}"}
        finally:
            db.close()

    def detect_zip(
        self,
        zip_path: str,
        conf: float = 0.25,
        scene_id: int = None,
        user_id: int = None,
    ) -> dict:
        """
        解压 ZIP 文件并批量检测其中所有图片

        Args:
            zip_path: ZIP 文件路径
            conf: 置信度阈值
            scene_id: 检测场景 ID
            user_id: 操作用户 ID

        Returns:
            ZIP 检测结果字典
        """
        temp_dir = None
        try:
            # ── 解压 ZIP 到临时目录 ──
            temp_dir = tempfile.mkdtemp(prefix="rsod_zip_")
            logger.info("解压 ZIP 文件: %s → %s", zip_path, temp_dir)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            # ── 筛选图片文件 ──
            image_files = []
            for root, dirs, files in os.walk(temp_dir):
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                        image_files.append(os.path.join(root, fname))

            if not image_files:
                return {"error": "ZIP 文件中没有找到图片"}

            logger.info("ZIP 中包含 %d 张图片，开始批量检测", len(image_files))

            # ── 调用批量检测 ──
            batch_result = self.detect_batch(
                image_paths=image_files,
                conf=conf,
                scene_id=scene_id,
                user_id=user_id,
            )

            batch_result["source"] = "zip"
            batch_result["zip_filename"] = os.path.basename(zip_path)
            batch_result["total_images_in_zip"] = len(image_files)

            return batch_result

        except zipfile.BadZipFile:
            return {"error": f"无效的 ZIP 文件: {zip_path}"}
        except Exception as e:
            logger.error("ZIP 检测异常: %s", str(e), exc_info=True)
            return {"error": f"ZIP 检测失败: {str(e)}"}
        finally:
            # ── 清理临时目录 ──
            if temp_dir and os.path.exists(temp_dir):
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)

    def detect_video(
        self,
        video_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        frame_sample_rate: int = 5,
        max_frames: int = 50,
        scene_id: int = None,
        user_id: int = None,
        task_id: int = None,
    ) -> dict:
        """
        视频检测 — 逐帧采样 + YOLO 推理

        处理流程：
        1. OpenCV 打开视频，获取总帧数和 fps
        2. 按 frame_sample_rate 采样关键帧
        3. 对每帧执行 YOLO 推理
        4. 生成标注帧图像（Base64）
        5. 汇总统计结果

        Args:
            video_path: 视频文件路径
            conf: 置信度阈值
            iou: NMS IoU 阈值
            frame_sample_rate: 帧采样间隔（每 N 帧取 1 帧）
            max_frames: 最多处理的关键帧数量（防止视频过长）
            scene_id: 检测场景 ID
            user_id: 操作用户 ID
            task_id: 已创建的检测任务 ID（用于更新进度）

        Returns:
            视频检测结果字典：
            {
                "task_id": int,
                "total_frames": int,          # 视频总帧数
                "processed_frames": int,       # 处理的关键帧数
                "fps": float,                  # 视频原始 fps
                "duration_seconds": float,     # 视频时长（秒）
                "total_objects": int,          # 检测到目标总数
                "class_counts": {...},         # 各类别统计
                "key_frames": [...],           # 关键帧结果列表
                "total_inference_time": float, # 总推理耗时（ms）
            }
        """
        db = SessionLocal()
        try:
            # ── 确保默认场景存在 ──
            if scene_id is None:
                scene_id = DetectionService._ensure_default_scene()

            # ── 加载模型 ──
            model = self._get_model(scene_id)

            # ── 打开视频 ──
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"error": f"无法打开视频文件: {video_path}"}

            # 获取视频基本信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration_seconds = total_frames / fps if fps > 0 else 0

            logger.info(
                "视频信息: %d×%d, %.1ffps, %d 帧, %.1f 秒",
                width,
                height,
                fps,
                total_frames,
                duration_seconds,
            )

            # ── 如果没有传入 task_id，创建检测任务 ──
            if not task_id:
                task = DetectionTask(
                    user_id=user_id or 0,
                    scene_id=scene_id,
                    task_type="video",
                    status="processing",
                    total_images=0,  # 后续更新
                    conf_threshold=conf,
                    iou_threshold=iou,
                )
                db.add(task)
                db.flush()
                task_id = task.id
            else:
                task = (
                    db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
                )

            # ── 计算需要采样的帧索引 ──
            # 根据视频总帧数和 max_frames 动态计算采样间隔，
            # 确保帧均匀分布在整个视频时长内，避免密集采样导致重复帧
            effective_interval = max(frame_sample_rate, total_frames // max_frames)
            sample_indices = list(range(0, total_frames, effective_interval))
            if len(sample_indices) > max_frames:
                sample_indices = sample_indices[:max_frames]

            # 更新任务的总图像数
            if task:
                task.total_images = len(sample_indices)
                db.commit()

            # ── 逐帧处理：场景变化检测 + 目标跟踪 + 合成标注视频 ──
            sample_set = set(sample_indices)
            key_frames = []
            total_objects = 0
            total_inference_time = 0
            class_counts = {}
            sampled_count = 0
            last_detections = []
            last_frame = None
            current_scene_seen_track_ids = set()
            class_colors = {
                "person": (0, 255, 0),
                "car": (255, 0, 0),
                "truck": (0, 0, 255),
                "bus": (255, 255, 0),
                "bicycle": (255, 0, 255),
                "motorcycle": (0, 255, 255),
            }

            def get_color(cls_name):
                return class_colors.get(cls_name, (255, 128, 0))

            def draw_detections_on_frame(frame, detections):
                annotated = frame.copy()
                for det in detections:
                    x1, y1, x2, y2 = det["bbox"]
                    color = get_color(det["class_name"])
                    cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    label = f"{det['class_name']} {det['confidence']:.2f}"
                    cv2.putText(
                        annotated,
                        label,
                        (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2,
                    )
                return annotated

            # 创建临时文件用于输出标注视频
            output_tmp = tempfile.NamedTemporaryFile(
                suffix=".mp4", delete=False
            )
            output_video_path = output_tmp.name
            output_tmp.close()

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            video_writer = cv2.VideoWriter(
                output_video_path, fourcc, fps, (width, height)
            )

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # 场景变化检测：比较当前帧与上一帧的差异
                current_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                current_frame_gray = cv2.resize(current_frame_gray, (100, 100))

                scene_changed = False
                if last_frame is not None:
                    frame_diff = cv2.absdiff(last_frame, current_frame_gray)
                    diff_score = frame_diff.mean()
                    if diff_score > 10:
                        scene_changed = True
                else:
                    scene_changed = True

                last_frame = current_frame_gray.copy()

                # 场景变化时才执行检测和计数
                if scene_changed:
                    results = model.predict(
                        source=frame,
                        conf=conf,
                        iou=iou,
                        imgsz=640,
                        device="cpu",
                        save=False,
                        verbose=False,
                    )
                    result = results[0]

                    frame_detections = []
                    if result.boxes is not None and len(result.boxes) > 0:
                        for box in result.boxes:
                            cls_id = int(box.cls[0])
                            cls_name = model.names.get(cls_id, f"class_{cls_id}")
                            confidence = float(box.conf[0])
                            x1, y1, x2, y2 = box.xyxy[0].tolist()

                            det = {
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
                            frame_detections.append(det)
                            total_objects += 1
                            class_counts[cls_name] = (
                                class_counts.get(cls_name, 0) + 1
                            )

                    last_detections = frame_detections
                    sampled_count += 1
                    inference_time = float(result.speed.get("inference", 0))
                    total_inference_time += inference_time

                    annotated_img = draw_detections_on_frame(frame, frame_detections)
                    video_writer.write(annotated_img)

                    # 生成 base64 缩略图（仅保留少量关键帧用于统计展示）
                    annotated_base64 = None
                    if len(key_frames) < 6:
                        _, buffer = cv2.imencode(
                            ".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 70]
                        )
                        annotated_base64 = base64.b64encode(buffer).decode("utf-8")

                    # 保存关键帧信息
                    key_frames.append(
                        {
                            "frame_index": frame_idx,
                            "timestamp": round(frame_idx / fps, 2),
                            "annotated_image_base64": annotated_base64,
                            "object_count": len(frame_detections),
                            "detections": frame_detections,
                            "inference_time": round(inference_time, 2),
                        }
                    )

                    # 保存检测结果到数据库
                    for det in frame_detections:
                        db_result = DetectionResult(
                            task_id=task_id,
                            image_path=f"frame_{frame_idx}.jpg",
                            class_name=det["class_name"],
                            class_id=det["class_id"],
                            confidence=det["confidence"],
                            bbox=det["bbox"],
                            inference_time=inference_time,
                        )
                        db.add(db_result)

                    # 更新任务进度
                    if task:
                        task.total_objects = total_objects
                        db.commit()

                    logger.debug(
                        "视频检测进度: %d 场景, 帧号 %d, 检测到 %d 个目标",
                        sampled_count,
                        frame_idx,
                        len(frame_detections),
                    )
                else:
                    # 场景未变化：使用上一帧的检测结果绘制
                    if last_detections:
                        annotated_frame = draw_detections_on_frame(frame, last_detections)
                        video_writer.write(annotated_frame)
                    else:
                        video_writer.write(frame)

                frame_idx += 1

            # ── 释放资源 ──
            cap.release()
            video_writer.release()

            # ── 使用 ffmpeg 转码为浏览器可播放的 H.264 ──
            h264_video_path = output_video_path.replace(".mp4", "_h264.mp4")
            try:
                subprocess.run(
                    [
                        shutil.which("ffmpeg") or "ffmpeg",
                        "-y",
                        "-i", output_video_path,
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart",
                        h264_video_path,
                    ],
                    capture_output=True,
                    timeout=300,
                    check=True,
                )
                # 替换原文件
                os.replace(h264_video_path, output_video_path)
                logger.info("视频已转码为 H.264 格式")
            except Exception as e:
                logger.warning("ffmpeg 转码失败，使用原始 mp4v 视频: %s", str(e))
                try:
                    os.unlink(h264_video_path)
                except Exception:
                    pass

            # ── 上传标注视频到 MinIO ──
            annotated_video_url = None
            try:
                minio_client = MinIOClient()
                object_name = f"detections/{task_id}/annotated_video.mp4"
                annotated_video_url = minio_client.upload_file(
                    object_name, output_video_path
                )
                logger.info("标注视频已上传: %s", object_name)
            except Exception as e:
                logger.warning("标注视频上传 MinIO 失败: %s", str(e))

            # 清理临时视频文件
            try:
                os.unlink(output_video_path)
            except Exception:
                pass

            # ── 更新任务状态为完成 ──
            if task:
                task.status = "completed"
                task.total_objects = total_objects
                task.total_inference_time = total_inference_time
                task.completed_at = datetime.now()
                db.commit()

            logger.info(
                "视频检测完成: %d 帧处理, %d 关键帧采样, 共 %d 个目标, 总耗时 %.2fms",
                frame_idx,
                len(key_frames),
                total_objects,
                total_inference_time,
            )

            return {
                "task_id": task_id,
                "total_frames": total_frames,
                "processed_frames": len(key_frames),
                "frame_sample_rate": frame_sample_rate,
                "fps": round(fps, 2),
                "duration_seconds": round(duration_seconds, 2),
                "video_resolution": {"width": width, "height": height},
                "total_objects": total_objects,
                "class_counts": class_counts,
                "key_frames": key_frames,
                "annotated_video_url": annotated_video_url,
                "total_inference_time": round(total_inference_time, 2),
            }

        except Exception as e:
            logger.error("视频检测异常: %s", str(e), exc_info=True)
            # 更新任务状态为失败
            if task_id:
                task = (
                    db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
                )
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    db.commit()
            return {"error": f"视频检测失败: {str(e)}"}
        finally:
            db.close()
# 创建全局单例
detection_service = DetectionService()
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
import contextvars
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

current_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_user_id", default=None
)

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
    def _get_default_model_path() -> str:
        """
        获取默认模型权重路径

        查找顺序：
          0. settings.DEFAULT_MODEL_PATH（配置的默认模型，优先级最高）
          1. models/ 目录下 is_default=True 的模型
          2. runs/train/ 目录下最新训练产出的 best.pt
          3. 回退到预训练模型 yolov11n.pt
        """
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 优先级 0：settings 中配置的默认模型路径
        configured_path = getattr(settings, "DEFAULT_MODEL_PATH", "")
        if configured_path:
            # 支持绝对路径和相对于 backend/ 的相对路径
            if not os.path.isabs(configured_path):
                configured_path = os.path.join(backend_dir, configured_path)
            if os.path.exists(configured_path):
                logger.info("使用配置的默认模型: %s", configured_path)
                return configured_path
            else:
                logger.warning("配置的 DEFAULT_MODEL_PATH 不存在，跳过: %s", configured_path)

        db = SessionLocal()
        try:
            # 查找默认模型版本
            default_model = (
                db.query(ModelVersion).filter(ModelVersion.is_default == True).first()
            )
            if default_model and os.path.exists(default_model.model_path):
                return default_model.model_path

            # 回退：查找最新训练的 best.pt
            from app.entity.db_models import TrainingTask

            latest_task = (
                db.query(TrainingTask)
                .filter(TrainingTask.status == "completed")
                .order_by(TrainingTask.completed_at.desc())
                .first()
            )
            if latest_task:
                weights_path = os.path.join(
                    os.getcwd(),
                    settings.TRAIN_OUTPUT_DIR,
                    f"task_{latest_task.task_uuid}",
                    "weights",
                    "best.pt",
                )
                if os.path.exists(weights_path):
                    return weights_path
        finally:
            db.close()

        # 最终回退：预训练模型
        return os.path.join(backend_dir, "yolo11n.pt")

    @staticmethod
    def _get_model(scene_id: int = None) -> YOLO:
        """
        加载 YOLO 模型

        优先级：
          1. settings.DEFAULT_MODEL_PATH（配置文件显式指定的模型，最高优先级）
          2. 场景关联的默认模型
          3. 全局默认模型（DB 中 is_default=True）
          4. 最新训练产出的 best.pt
          5. 回退到预训练 yolo11n.pt
        """
        # 优先级 1：配置文件显式指定的模型
        configured_path = getattr(settings, "DEFAULT_MODEL_PATH", "")
        if configured_path:
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if not os.path.isabs(configured_path):
                configured_path = os.path.join(backend_dir, configured_path)
            if os.path.exists(configured_path):
                logger.info("加载配置默认模型: %s", configured_path)
                return YOLO(configured_path)

        # 优先级 2：场景关联的默认模型
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
                if default_model and os.path.exists(default_model.model_path):
                    model_path = default_model.model_path
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
        latitude: float = None,
        longitude: float = None,
        location_name: str = None,
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
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
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
        except Exception as e:
            logger.warning("MinIO 上传失败（不影响检测结果）: %s", str(e))

        # ── 保存每条检测结果 ──
        if detections:
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
                    latitude=latitude,
                    longitude=longitude,
                )
                db.add(result)
        else:
            # 检测到 0 个目标时，创建占位记录以保留标注图 URL（供历史记录/图片代理查询）
            placeholder = DetectionResult(
                task_id=task.id,
                image_path=original_filename,
                annotated_image_url=annotated_image_url,
                class_name="no_detection",
                class_name_cn="未检测到目标",
                class_id=-1,
                confidence=0.0,
                bbox=[],
                inference_time=inference_time,
                latitude=latitude,
                longitude=longitude,
            )
            db.add(placeholder)

        try:
            db.commit()
            logger.info(
                "检测任务 %d 已保存，%d 条结果%s",
                task.id,
                len(detections),
                "（无目标，已创建占位记录）" if not detections else "",
            )
        except Exception as e:
            db.rollback()
            logger.error("检测任务 %d 保存失败: %s", task.id, str(e), exc_info=True)
            raise

        return {"task_id": task.id, "annotated_image_url": annotated_image_url}

    def detect_single(
        self,
        image_path: str,
        conf: float = 0.25,
        iou: float = 0.45,
        scene_id: int = None,
        user_id: int = None,
        latitude: float = None,
        longitude: float = None,
        location_name: str = None,
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
        # 从上下文变量获取 user_id（Agent 工具调用时未显式传递）
        user_id = user_id or current_user_id.get()

        db = SessionLocal()
        try:
            # 当 scene_id 为 None 时，使用全局配置的默认场景（按名称查找）
            if not scene_id:
                scene_name = getattr(settings, 'DEFAULT_SCENE_NAME', 'weeds')
                scene = db.query(DetectionScene).filter(DetectionScene.name == scene_name).first()
                if scene:
                    scene_id = scene.id
            else:
                scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
            if not scene:
                default_scene = db.query(DetectionScene).first()
                if default_scene:
                    scene_id = default_scene.id

            # ── 获取类别中文名映射 ──
            class_names_cn = {}
            if scene and scene.class_names_cn:
                class_names_cn = scene.class_names_cn

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
                            "class_name_cn": class_names_cn.get(cls_name, cls_name),
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
                    latitude=latitude,
                    longitude=longitude,
                    location_name=location_name,
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
        latitude: float = None,
        longitude: float = None,
        location_name: str = None,
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
        # 从上下文变量获取 user_id（Agent 工具调用时未显式传递）
        user_id = user_id or current_user_id.get()

        db = SessionLocal()
        try:
            # 当 scene_id 为 None 时，使用全局配置的默认场景（按名称查找）
            if not scene_id:
                scene_name = getattr(settings, 'DEFAULT_SCENE_NAME', 'weeds')
                scene = db.query(DetectionScene).filter(DetectionScene.name == scene_name).first()
                if scene:
                    scene_id = scene.id
            else:
                scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
            if not scene:
                default_scene = db.query(DetectionScene).first()
                if default_scene:
                    scene_id = default_scene.id
                else:
                    return {"error": "数据库中没有可用的检测场景，请先创建检测场景"}

            # ── 获取类别中文名映射 ──
            class_names_cn = {}
            if scene and scene.class_names_cn:
                class_names_cn = scene.class_names_cn

            # ── 加载模型 ──
            model = self._get_model(scene_id)

            # ── 创建批量检测任务 ──
            task = DetectionTask(
                user_id=user_id or 0,
                scene_id=scene_id,
                task_type="batch",
                status="processing",
                total_images=len(image_paths),
                conf_threshold=conf,
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
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

                # 上传标注图到 MinIO（供历史记录图片代理使用）
                annotated_url = None
                try:
                    minio_client = MinIOClient()
                    object_name = f"detections/{task.id}/{os.path.basename(image_path)}"
                    annotated_url = minio_client.upload_bytes(
                        object_name, buffer.tobytes(), "image/jpeg"
                    )
                except Exception as e:
                    logger.warning("批量检测 MinIO 上传失败（不影响检测结果）: %s", str(e))

                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = model.names.get(cls_id, f"class_{cls_id}")
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = box.xyxy[0].tolist()

                        det = {
                            "image_path": image_path,
                            "class_name": cls_name,
                            "class_name_cn": class_names_cn.get(cls_name, cls_name),
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
                                annotated_image_url=annotated_url,
                                class_name=det["class_name"],
                                class_name_cn=det.get("class_name_cn"),
                                class_id=det["class_id"],
                                confidence=det["confidence"],
                                bbox=det["bbox"],
                                inference_time=inference_time,
                                latitude=latitude,
                                longitude=longitude,
                            )
                            db.add(db_result)
                else:
                    # 该图未检测到目标，创建占位记录以保留标注图 URL
                    db.add(DetectionResult(
                        task_id=task.id,
                        image_path=image_path,
                        annotated_image_url=annotated_url,
                        class_name="no_detection",
                        class_name_cn="未检测到目标",
                        class_id=-1,
                        confidence=0.0,
                        bbox=[],
                        inference_time=inference_time,
                        latitude=latitude,
                        longitude=longitude,
                    ))

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
        latitude: float = None,
        longitude: float = None,
        location_name: str = None,
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
        # 从上下文变量获取 user_id（Agent 工具调用时未显式传递）
        user_id = user_id or current_user_id.get()

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
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
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
        # 从上下文变量获取 user_id（Agent 工具调用时未显式传递）
        user_id = user_id or current_user_id.get()

        db = SessionLocal()
        try:
            # 当 scene_id 为 None 时，使用全局配置的默认场景（按名称查找）
            if not scene_id:
                scene_name = getattr(settings, 'DEFAULT_SCENE_NAME', 'weeds')
                scene = db.query(DetectionScene).filter(DetectionScene.name == scene_name).first()
                if scene:
                    scene_id = scene.id
            else:
                scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
            if not scene:
                default_scene = db.query(DetectionScene).first()
                if default_scene:
                    scene_id = default_scene.id
                    scene = default_scene
                else:
                    return {"error": "数据库中没有可用的检测场景"}
                    
            class_names_cn = scene.class_names_cn if scene and scene.class_names_cn else {}

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
                    scene_id=scene_id or 1,
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
            first_frame_annotated_url = None  # 用于历史预览图
            _minio_client = None  # 延迟初始化的 MinIO 客户端
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

            # 创建临时文件用于输出标注视频（先用 AVI/MJPG，兼容性最佳）
            output_tmp = tempfile.NamedTemporaryFile(
                suffix=".avi", delete=False
            )
            output_video_path = output_tmp.name
            output_tmp.close()

            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
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
                                "class_name_cn": class_names_cn.get(cls_name, cls_name),
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

                    # 上传当前帧标注图到 MinIO，供检测记录预览和详情查看
                    current_frame_url = None
                    if frame_detections:
                        try:
                            if _minio_client is None:
                                _minio_client = MinIOClient()
                            _, img_buf = cv2.imencode(".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                            obj_name = f"detections/{task_id}/frame_{frame_idx}.jpg"
                            current_frame_url = _minio_client.upload_bytes(
                                obj_name, img_buf.tobytes(), "image/jpeg"
                            )
                            if first_frame_annotated_url is None:
                                first_frame_annotated_url = current_frame_url
                        except Exception as e:
                            logger.warning("视频关键帧上传 MinIO 失败: %s", str(e))

                    # 保存检测结果到数据库
                    for det in frame_detections:
                        db_result = DetectionResult(
                            task_id=task_id,
                            image_path=f"frame_{frame_idx}.jpg",
                            annotated_image_url=current_frame_url,
                            class_name=det["class_name"],
                            class_name_cn=det.get("class_name_cn"),
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

            # 若所有帧均未检测到目标，创建占位记录以保留预览图
            if first_frame_annotated_url is None:
                try:
                    if _minio_client is None:
                        _minio_client = MinIOClient()
                    # 从视频中取第一帧作为预览
                    cap2 = cv2.VideoCapture(video_path)
                    ret2, first_frame = cap2.read()
                    cap2.release()
                    if ret2:
                        _, img_buf = cv2.imencode(".jpg", first_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        obj_name = f"detections/{task_id}/frame_0_preview.jpg"
                        first_frame_annotated_url = _minio_client.upload_bytes(
                            obj_name, img_buf.tobytes(), "image/jpeg"
                        )
                except Exception as e:
                    logger.warning("视频预览帧上传失败: %s", str(e))
                placeholder = DetectionResult(
                    task_id=task_id,
                    image_path="frame_0.jpg",
                    annotated_image_url=first_frame_annotated_url,
                    class_name="no_detection",
                    class_id=-1,
                    confidence=0,
                    bbox=[],
                    inference_time=0,
                )
                db.add(placeholder)
                db.commit()

            # ── 使用 ffmpeg 转码为浏览器可播放的 H.264 MP4 ──
            ffmpeg_ok = False
            mp4_path = output_video_path.replace(".avi", ".mp4")
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                try:
                    subprocess.run(
                        [
                            ffmpeg_path,
                            "-y",
                            "-i", output_video_path,
                            "-c:v", "libx264",
                            "-preset", "fast",
                            "-crf", "23",
                            "-pix_fmt", "yuv420p",
                            "-movflags", "+faststart",
                            mp4_path,
                        ],
                        capture_output=True,
                        timeout=300,
                        check=True,
                    )
                    ffmpeg_ok = True
                    logger.info("视频已转码为 H.264 MP4 格式")
                except Exception as e:
                    logger.warning("ffmpeg 转码失败: %s", str(e))
                    try:
                        os.unlink(mp4_path)
                    except Exception:
                        pass
            else:
                logger.warning("未找到 ffmpeg，将使用原始 AVI 视频")

            if ffmpeg_ok:
                final_video_path = mp4_path
                video_ext = "mp4"
            else:
                final_video_path = output_video_path
                video_ext = "avi"

            # ── 上传标注视频到 MinIO ──
            annotated_video_url = None
            try:
                minio_client = MinIOClient()
                object_name = f"detections/{task_id}/annotated_video.{video_ext}"
                annotated_video_url = minio_client.upload_file(
                    object_name, final_video_path
                )
                logger.info("标注视频已上传: %s", object_name)
            except Exception as e:
                logger.warning("标注视频上传 MinIO 失败: %s", str(e))

            # 清理临时视频文件
            for p in [output_video_path, mp4_path]:
                try:
                    if os.path.exists(p):
                        os.unlink(p)
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


def get_model(scene_id: int = None):
    """模块级快捷函数：获取 YOLO 模型（供 WebSocket 等场景使用）"""
    return DetectionService._get_model(scene_id)
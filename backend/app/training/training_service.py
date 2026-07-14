# backend/app/training/training_service.py
"""
模型训练服务

职责：
- 封装 YOLOv11 训练启动、监控、停止逻辑
- 支持本地 CPU 训练和 GPU 训练
- 训练在后台线程中执行，不阻塞 API 请求
- 实时解析训练指标并写入数据库
- 解析 Ultralytics 生成的 results.csv 获取训练日志

使用方式：
    from app.training.training_service import training_service

    # 启动训练
    task = training_service.start_training(
        db=db,
        user_id=current_user.id,
        scene_id=scene.id,
        config={
            "model_name": "yolov11n",
            "epochs": 50,
            "batch_size": 8
        }
    )

    # 查询训练状态
    status = training_service.get_training_status(db, task_id)

    # 获取训练指标
    metrics = training_service.get_training_metrics(db, task_id)
"""

import csv
import os
import threading
import uuid
from datetime import datetime

from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import ModelVersion, TrainingMetric, TrainingTask

logger = get_logger(__name__)

BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

_running_tasks = {}
_running_lock = threading.Lock()


def _safe_float(value: str, default: float = 0.0) -> float:
    """安全地将字符串转换为浮点数"""
    if not value or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


class TrainingService:
    """模型训练服务类"""

    @staticmethod
    def start_training(
        db,
        user_id: int,
        scene_id: int,
        config: dict,
    ):
        """
        启动训练任务（异步，立即返回）

        Args:
            db: 数据库会话
            user_id: 用户ID
            scene_id: 检测场景ID
            config: 训练配置字典
                - model_name: 模型名称 (yolov11n/s/m/l/x)
                - epochs: 训练轮数
                - batch_size: 批次大小
                - img_size: 图像尺寸
                - device: 训练设备 (cpu / 0 / 1)
                - optimizer: 优化器 (SGD / Adam / AdamW)
                - lr0: 初始学习率
                - dataset_path: 数据集路径
                - data_yaml: data.yaml 文件路径
                - augment_config: 数据增强配置

        Returns:
            创建的 TrainingTask 对象
        """
        task_uuid = str(uuid.uuid4()).replace("-", "")[:16]

        # 获取数据集路径
        dataset_path = config.get("dataset_path", "")
        data_yaml = config.get("data_yaml", "")
        if not data_yaml and dataset_path:
            yaml_candidate = os.path.join(dataset_path, "data.yaml")
            if os.path.exists(yaml_candidate):
                data_yaml = yaml_candidate

        # 创建数据库记录
        task = TrainingTask(
            user_id=user_id,
            scene_id=scene_id,
            task_uuid=task_uuid,
            status="pending",
            model_name=config.get("model_name", "yolov11n"),
            epochs=config.get("epochs", 50),
            img_size=config.get("img_size", 640),
            batch_size=config.get("batch_size", 8),
            device=config.get("device", "cpu"),
            optimizer=config.get("optimizer", "SGD"),
            lr0=config.get("lr0", 0.01),
            augment_config=config.get("augment_config"),
            dataset_path=dataset_path,
            data_yaml=data_yaml,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # 启动后台训练线程
        thread = threading.Thread(
            target=TrainingService._run_training,
            args=(task.id, task.task_uuid, config),
            daemon=True,
            name=f"train-{task_uuid}",
        )
        thread.start()

        logger.info(
            "训练任务已启动: task_id=%d, uuid=%s, model=%s, epochs=%d",
            task.id,
            task.task_uuid,
            task.model_name,
            task.epochs,
        )
        return task

    @staticmethod
    def resume_training(
        db,
        user_id: int,
        scene_id: int,
        config: dict,
        resume_from_task_id: int,
    ):
        """
        从已有训练任务继续训练（续训）

        Args:
            db: 数据库会话
            user_id: 用户ID
            scene_id: 检测场景ID
            config: 训练配置字典
                - model_name: 模型名称 (yolov11n/s/m/l/x)
                - epochs: 新的总训练轮数（不是追加轮数）
                - batch_size: 批次大小
                - img_size: 图像尺寸
                - device: 训练设备 (cpu / 0 / 1)
                - optimizer: 优化器 (SGD / Adam / AdamW)
                - lr0: 初始学习率
                - dataset_path: 数据集路径
                - data_yaml: data.yaml 文件路径
            resume_from_task_id: 要续训的源任务ID

        Returns:
            创建的新 TrainingTask 对象
        """
        source_task = db.query(TrainingTask).filter(TrainingTask.id == resume_from_task_id).first()
        if not source_task:
            raise ValueError(f"源训练任务不存在: {resume_from_task_id}")

        if source_task.status != "completed":
            raise ValueError(f"源训练任务状态不是已完成: {source_task.status}")

        last_pt_path = os.path.join(
            BACKEND_DIR,
            settings.TRAIN_OUTPUT_DIR,
            f"task_{source_task.task_uuid}",
            "weights",
            "last.pt",
        )
        if not os.path.exists(last_pt_path):
            raise ValueError(f"源任务的 last.pt 文件不存在: {last_pt_path}")

        task_uuid = str(uuid.uuid4()).replace("-", "")[:16]

        dataset_path = config.get("dataset_path", "")
        data_yaml = config.get("data_yaml", "")
        if not data_yaml and dataset_path:
            yaml_candidate = os.path.join(dataset_path, "data.yaml")
            if os.path.exists(yaml_candidate):
                data_yaml = yaml_candidate

        task = TrainingTask(
            user_id=user_id,
            scene_id=scene_id,
            source_task_id=resume_from_task_id,
            task_uuid=task_uuid,
            status="pending",
            model_name=config.get("model_name", source_task.model_name),
            epochs=config.get("epochs", source_task.epochs),
            img_size=config.get("img_size", source_task.img_size),
            batch_size=config.get("batch_size", source_task.batch_size),
            device=config.get("device", source_task.device),
            optimizer=config.get("optimizer", source_task.optimizer),
            lr0=config.get("lr0", source_task.lr0),
            augment_config=config.get("augment_config", source_task.augment_config),
            dataset_path=dataset_path,
            data_yaml=data_yaml,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        resume_config = config.copy()
        resume_config["resume_from"] = last_pt_path
        resume_config["source_task_uuid"] = source_task.task_uuid
        resume_config["source_task_epochs"] = source_task.epochs

        thread = threading.Thread(
            target=TrainingService._run_training,
            args=(task.id, task.task_uuid, resume_config),
            daemon=True,
            name=f"train-{task_uuid}",
        )
        thread.start()

        logger.info(
            "续训任务已启动: task_id=%d, uuid=%s, resume_from=%d, epochs=%d",
            task.id,
            task.task_uuid,
            resume_from_task_id,
            task.epochs,
        )
        return task

    @staticmethod
    def _run_training(task_id: int, task_uuid: str, config: dict):
        """
        在后台线程中执行 YOLOv11 训练（内部方法）
        """
        # 创建独立的数据库会话（后台线程不能复用请求级会话）
        db = SessionLocal()
        original_content = ""
        data_yaml = ""
        original_cwd = os.getcwd()

        try:
            task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
            if not task:
                logger.error("训练任务不存在: task_id=%d", task_id)
                return

            # 更新状态为 running
            task.status = "running"  # type: ignore
            task.started_at = datetime.now()  # type: ignore
            db.commit()

            # 导入 ultralytics
            from ultralytics import YOLO

            model_name = config.get("model_name", "yolov11n")
            resume_from = config.get("resume_from", "")
            
            if resume_from and os.path.exists(resume_from):
                logger.info(
                    "续训模式: 加载已训练权重 %s",
                    resume_from,
                )
                model = YOLO(resume_from)
            else:
                yolo_model_name = (
                    model_name.replace("v11", "11")
                    if "yolov11" in model_name
                    else model_name
                )
                logger.info(
                    "加载预训练模型: %s -> %s (首次使用将自动下载)",
                    model_name,
                    yolo_model_name,
                )
                model = YOLO(f"{yolo_model_name}.pt")

            # 注册到运行中任务表（用于中途停止）
            with _running_lock:
                _running_tasks[task_uuid] = model

            # 确定 data.yaml 路径
            data_yaml = config.get("data_yaml", "")
            if not data_yaml:
                dataset_path = config.get("dataset_path", "")
                data_yaml = os.path.join(dataset_path, "data.yaml")

            if not os.path.exists(data_yaml):
                raise FileNotFoundError(f"data.yaml 不存在: {data_yaml}")

            # 临时修改 data.yaml 的 path 为绝对路径
            data_yaml_dir = os.path.dirname(os.path.abspath(data_yaml))
            with open(data_yaml, "r", encoding="utf-8") as f:
                original_content = f.read()

            # 替换 path 为绝对路径
            modified_content = original_content
            for line in original_content.split("\n"):
                if line.strip().startswith("path:"):
                    modified_content = modified_content.replace(
                        line.strip(), f"path: {data_yaml_dir}"
                    )
                    break

            with open(data_yaml, "w", encoding="utf-8") as f:
                f.write(modified_content)

            logger.info("临时修改 data.yaml path 为绝对路径: %s", data_yaml_dir)

            project_dir = os.path.join(BACKEND_DIR, settings.TRAIN_OUTPUT_DIR)

            source_task_uuid = config.get("source_task_uuid", "")
            epoch_offset = 0
            if resume_from and os.path.exists(resume_from) and source_task_uuid:
                source_dir = os.path.join(project_dir, f"task_{source_task_uuid}")
                source_last_pt = os.path.join(source_dir, "weights", "last.pt")
                import shutil
                if os.path.exists(source_dir):
                    train_dir = os.path.join(project_dir, f"task_{task_uuid}")
                    shutil.copytree(source_dir, train_dir)
                    logger.info(
                        "续训模式: 复制源任务目录 %s -> %s",
                        source_dir,
                        train_dir,
                    )
                else:
                    train_dir = os.path.join(project_dir, f"task_{task_uuid}")
                
                epoch_offset = config.get("source_task_epochs", 0)
                actual_epochs = config.get("epochs", 50) - epoch_offset
                if actual_epochs <= 0:
                    actual_epochs = config.get("epochs", 50)
                
                resume_lr0 = config.get("lr0", 0.01) * 0.1
                train_kwargs = {
                    "data": data_yaml,
                    "epochs": actual_epochs,
                    "imgsz": config.get("img_size", 640),
                    "batch": config.get("batch_size", 8),
                    "device": config.get("device", "cpu"),
                    "optimizer": config.get("optimizer", "SGD"),
                    "lr0": resume_lr0,
                    "warmup_epochs": 0,
                    "project": project_dir,
                    "name": f"task_{task_uuid}",
                    "exist_ok": True,
                    "verbose": True,
                    "save": True,
                    "plots": False,
                }
                logger.info(
                    "续训模式: 从 epoch %d 继续训练到 %d 轮, 实际训练 %d 轮, lr0=%.6f",
                    epoch_offset + 1,
                    config.get("epochs", 50),
                    actual_epochs,
                    resume_lr0,
                )
            else:
                train_dir = os.path.join(project_dir, f"task_{task_uuid}")
                train_kwargs = {
                    "data": data_yaml,
                    "epochs": config.get("epochs", 50),
                    "imgsz": config.get("img_size", 640),
                    "batch": config.get("batch_size", 8),
                    "device": config.get("device", "cpu"),
                    "optimizer": config.get("optimizer", "SGD"),
                    "lr0": config.get("lr0", 0.01),
                    "project": project_dir,
                    "name": f"task_{task_uuid}",
                    "exist_ok": True,
                    "verbose": True,
                    "save": True,
                    "plots": False,
                }

            # 注册训练回调：每个 epoch 结束时更新数据库
            def on_train_epoch_end(trainer):
                try:
                    epoch = trainer.epoch + 1 + epoch_offset
                    metrics = trainer.metrics or {}

                    metric_record = TrainingMetric(
                        task_id=task_id,
                        epoch=epoch,
                        box_loss=float(metrics.get("box_loss", 0.0)),
                        cls_loss=float(metrics.get("cls_loss", 0.0)),
                        dfl_loss=float(metrics.get("dfl_loss", 0.0)),
                        precision=float(metrics.get("precision", 0.0)),
                        recall=float(metrics.get("recall", 0.0)),
                        map50=float(metrics.get("mAP50", 0.0)),
                        map50_95=float(metrics.get("mAP50-95", 0.0)),
                    )
                    db.add(metric_record)

                    total_epochs = config.get("epochs", 50)
                    task.current_epoch = epoch  # type: ignore
                    task.progress = int((epoch / total_epochs) * 100)  # type: ignore
                    db.commit()

                    logger.debug(
                        "训练进度: task=%s epoch=%d/%d",
                        task_uuid,
                        epoch,
                        total_epochs,
                    )
                except Exception as e:
                    logger.warning("训练回调异常（不影响训练）: %s", str(e))
                    db.rollback()

            model.add_callback("on_train_epoch_end", on_train_epoch_end)

            # 开始训练（阻塞直到完成）
            logger.info(
                "开始训练: data=%s, epochs=%d",
                data_yaml,
                train_kwargs["epochs"],
            )
            model.train(**train_kwargs)

            # 训练完成
            task.status = "completed"  # type: ignore
            task.progress = 100  # type: ignore
            task.current_epoch = config.get("epochs", 50)  # type: ignore
            task.completed_at = datetime.now()  # type: ignore
            task.model_name = model_name  # type: ignore
            db.commit()

            # 从 results.csv 补充最终指标
            project_path = os.path.join(BACKEND_DIR, settings.TRAIN_OUTPUT_DIR)
            TrainingService._parse_final_results(
                db, task_id, task_uuid, config, project_path, epoch_offset
            )

            TrainingService._create_model_version(
                db, task_id, task_uuid, config, project_path
            )

            logger.info("训练完成: task_id=%d, uuid=%s", task_id, task_uuid)

        except FileNotFoundError as e:
            logger.error("训练文件缺失: task_id=%d, error=%s", task_id, str(e))
            task.status = "failed"  # type: ignore
            task.error_message = str(e)  # type: ignore
            db.commit()

        except Exception as e:
            logger.error(
                "训练异常: task_id=%d, error=%s",
                task_id,
                str(e),
                exc_info=True,
            )
            task.status = "failed"  # type: ignore
            task.error_message = str(e)[:2000]  # type: ignore
            db.commit()

        finally:
            # 恢复 data.yaml 原始内容
            try:
                if data_yaml and original_content:
                    with open(data_yaml, "w", encoding="utf-8") as f:
                        f.write(original_content)
                    logger.info("恢复 data.yaml 原始内容")
            except Exception:
                pass

            # 恢复工作目录
            try:
                os.chdir(original_cwd)
            except Exception:
                pass

            # 从运行中任务表中移除
            with _running_lock:
                _running_tasks.pop(task_uuid, None)

            db.close()

    @staticmethod
    def _parse_final_results(
        db,
        task_id: int,
        task_uuid: str,
        config: dict,
        project_path: str | None = None,
        epoch_offset: int = 0,
    ):
        """
        训练完成后从 results.csv 解析最终指标并补充到数据库

        Args:
            epoch_offset: 续训时的epoch偏移量，用于将YOLO内部epoch编号转换为真实epoch编号
        """
        if project_path is None:
            project_path = settings.TRAIN_OUTPUT_DIR

        results_csv = os.path.join(
            project_path,
            f"task_{task_uuid}",
            "results.csv",
        )

        if not os.path.exists(results_csv):
            logger.warning("results.csv 不存在: %s", results_csv)
            return

        try:
            db.query(TrainingMetric).filter(TrainingMetric.task_id == task_id).delete()
            db.commit()

            with open(results_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row = {k.strip(): v.strip() for k, v in row.items()}
                    epoch = int(row.get("epoch", 0)) + epoch_offset

                    metric = TrainingMetric(
                        task_id=task_id,
                        epoch=epoch,
                        box_loss=_safe_float(row.get("train/box_loss", "")),
                        cls_loss=_safe_float(row.get("train/cls_loss", "")),
                        dfl_loss=_safe_float(row.get("train/dfl_loss", "")),
                        precision=_safe_float(row.get("metrics/precision(B)", "")),
                        recall=_safe_float(row.get("metrics/recall(B)", "")),
                        map50=_safe_float(row.get("metrics/mAP50(B)", "")),
                        map50_95=_safe_float(row.get("metrics/mAP50-95(B)", "")),
                        lr=_safe_float(row.get("lr/pg0", "")),
                    )
                    db.add(metric)
                db.commit()

            logger.info("results.csv 解析完成，指标已补充到数据库 (epoch_offset=%d)", epoch_offset)

        except Exception as e:
            logger.warning("results.csv 解析异常（不影响训练结果）: %s", str(e))
            db.rollback()

    @staticmethod
    def get_training_status(db, task_id: int) -> dict:
        """获取训练任务状态"""
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            return {"error": "训练任务不存在"}

        # 获取最新一条指标记录
        latest_metric = (
            db.query(TrainingMetric)
            .filter(TrainingMetric.task_id == task_id)
            .order_by(TrainingMetric.epoch.desc())
            .first()
        )

        # 检查是否在运行中
        with _running_lock:
            is_running = task.task_uuid in _running_tasks

        # 如果状态是 running 但实际没有运行中，尝试自动修复
        if task.status == "running" and not is_running:
            best_model_path = os.path.join(
                settings.TRAIN_OUTPUT_DIR,
                f"task_{task.task_uuid}",
                "weights",
                "best.pt",
            )
            if os.path.exists(best_model_path):
                results_csv = os.path.join(
                    settings.TRAIN_OUTPUT_DIR,
                    f"task_{task.task_uuid}",
                    "results.csv",
                )
                if os.path.exists(results_csv):
                    try:
                        with open(results_csv, "r", encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            epochs = []
                            for row in reader:
                                row = {k.strip(): v.strip() for k, v in row.items()}
                                epochs.append(int(row.get("epoch", 0)) + 1)
                            last_epoch = max(epochs) if epochs else task.current_epoch
                            task.current_epoch = last_epoch
                            task.progress = int((last_epoch / task.epochs) * 100)
                    except Exception:
                        pass

                if task.current_epoch >= task.epochs:
                    task.status = "completed"
                    task.progress = 100
                else:
                    task.status = "completed"
                task.completed_at = datetime.now()
                db.commit()
                logger.info(f"自动修复任务状态: task_id={task.id}, status=completed")

        return {
            "task": {
                "id": task.id,
                "task_uuid": task.task_uuid,
                "status": task.status,
                "model_name": task.model_name,
                "epochs": task.epochs,
                "current_epoch": task.current_epoch,
                "progress": task.progress,
                "device": task.device,
                "batch_size": task.batch_size,
                "img_size": task.img_size,
                "started_at": str(task.started_at) if task.started_at else None,
                "completed_at": str(task.completed_at) if task.completed_at else None,
                "error_message": task.error_message,
            },
            "latest_metric": {
                "epoch": latest_metric.epoch,
                "box_loss": latest_metric.box_loss,
                "cls_loss": latest_metric.cls_loss,
                "dfl_loss": latest_metric.dfl_loss,
                "precision": latest_metric.precision,
                "recall": latest_metric.recall,
                "map50": latest_metric.map50,
                "map50_95": latest_metric.map50_95,
                "lr": latest_metric.lr,
            }
            if latest_metric
            else None,
            "is_running": is_running,
        }

    @staticmethod
    def get_training_metrics(db, task_id: int) -> list:
        """获取训练任务的所有epoch指标（包含续训来源任务的指标）"""
        all_metrics = []

        def collect_metrics(t_id):
            task = db.query(TrainingTask).filter(TrainingTask.id == t_id).first()
            if not task:
                return

            if task.source_task_id:
                collect_metrics(task.source_task_id)

            metrics = (
                db.query(TrainingMetric)
                .filter(TrainingMetric.task_id == t_id)
                .order_by(TrainingMetric.epoch.asc())
                .all()
            )

            for m in metrics:
                all_metrics.append({
                    "epoch": m.epoch,
                    "box_loss": m.box_loss,
                    "cls_loss": m.cls_loss,
                    "dfl_loss": m.dfl_loss,
                    "precision": m.precision,
                    "recall": m.recall,
                    "map50": m.map50,
                    "map50_95": m.map50_95,
                    "lr": m.lr,
                })

        collect_metrics(task_id)
        all_metrics.sort(key=lambda x: x["epoch"])

        return all_metrics

    @staticmethod
    def stop_training(db, task_id: int) -> dict:
        """停止正在运行的训练任务"""
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            return {"error": "训练任务不存在"}

        if task.status != "running":
            return {"error": f"任务当前状态为 {task.status}，无法停止"}

        with _running_lock:
            model = _running_tasks.get(task.task_uuid)
            if model:
                try:
                    model.trainer.stop()
                except Exception as e:
                    logger.warning("停止训练异常: %s", str(e))

        task.status = "cancelled"
        task.completed_at = datetime.now()
        db.commit()

        logger.info("训练任务已停止: task_id=%d", task_id)
        return {"message": "训练任务已停止", "task_id": task_id}

    @staticmethod
    def get_task_list(db, user_id: int | None = None, limit: int = 20) -> list:
        """获取训练任务列表"""
        query = db.query(TrainingTask)
        if user_id:
            query = query.filter(TrainingTask.user_id == user_id)

        tasks = query.order_by(TrainingTask.created_at.desc()).limit(limit).all()

        return [
            {
                "id": t.id,
                "task_uuid": t.task_uuid,
                "status": t.status,
                "model_name": t.model_name,
                "epochs": t.epochs,
                "current_epoch": t.current_epoch,
                "progress": t.progress,
                "device": t.device,
                "scene_id": t.scene_id,
                "img_size": t.img_size,
                "batch_size": t.batch_size,
                "optimizer": t.optimizer,
                "lr0": t.lr0,
                "created_at": str(t.created_at),
                "started_at": str(t.started_at) if t.started_at else None,
                "completed_at": str(t.completed_at) if t.completed_at else None,
            }
            for t in tasks
        ]

    @staticmethod
    def validate_model(
        db,
        task_id: int,
        split: str = "val",
        conf: float = 0.001,
        iou: float = 0.6,
    ) -> dict:
        """
        对已完成训练的模型执行验证集评估

        流程：
          1. 查找训练任务对应的 best.pt 路径
          2. 加载模型并运行 model.val()
          3. 解析评估结果
          4. 将评估指标写入 ModelVersion 表
          5. 返回结构化评估报告

        Args:
            db: 数据库会话
            task_id: 训练任务 ID
            split: 评估数据集划分（val / test）
            conf: 置信度阈值
            iou: NMS IoU 阈值

        Returns:
            评估报告字典
        """
        from ultralytics import YOLO

        # 查找训练任务
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            return {"error": "训练任务不存在"}

        if task.status != "completed":
            return {"error": f"训练任务状态为 {task.status}，只有已完成的任务才能评估"}

        weights_path = os.path.join(
            BACKEND_DIR,
            settings.TRAIN_OUTPUT_DIR,
            f"task_{task.task_uuid}",
            "weights",
            "best.pt",
        )

        if not os.path.exists(weights_path):
            return {"error": f"模型权重不存在: {weights_path}"}

        # 定位 data.yaml
        data_yaml = task.data_yaml
        if not data_yaml or not os.path.exists(data_yaml):
            if task.dataset_path:
                data_yaml = os.path.join(task.dataset_path, "data.yaml")
            if not os.path.exists(data_yaml):
                return {"error": "data.yaml 不存在"}

        logger.info(
            "开始模型评估: task_id=%d, weights=%s, split=%s",
            task_id,
            weights_path,
            split,
        )

        try:
            model = YOLO(weights_path)
            results = model.val(
                data=data_yaml,
                split=split,
                conf=conf,
                iou=iou,
                imgsz=task.img_size,
                device="cpu",
                save_json=True,
                plots=True,
                project=os.path.join(BACKEND_DIR, settings.TRAIN_OUTPUT_DIR),
                name=f"task_{task.task_uuid}",
                exist_ok=True,
                verbose=False,
            )

            # 解析评估结果
            overall = {
                "precision": float(results.box.mp),
                "recall": float(results.box.mr),
                "map50": float(results.box.map50),
                "map50_95": float(results.box.map),
            }

            per_class = {}
            if (
                hasattr(results.box, "ap")
                and results.box.ap is not None
                and len(results.box.ap) > 0
            ):
                for i, ap50 in enumerate(results.box.ap50):
                    class_name = model.names.get(i, f"class_{i}")
                    ap50_95 = results.box.ap[i] if i < len(results.box.ap) else 0.0
                    per_class[class_name] = {
                        "ap50": round(float(ap50), 4),
                        "ap50_95": round(float(ap50_95), 4),
                    }

            report = {
                "task_id": task_id,
                "task_uuid": task.task_uuid,
                "split": split,
                "overall": overall,
                "per_class": per_class,
            }

            # 更新或创建 ModelVersion 记录
            from app.entity.db_models import DetectionScene, ModelVersion

            scene = (
                db.query(DetectionScene)
                .filter(DetectionScene.id == task.scene_id)
                .first()
            )

            model_version = (
                db.query(ModelVersion)
                .filter(ModelVersion.training_task_id == task_id)
                .first()
            )

            if not model_version:
                existing_count = (
                    db.query(ModelVersion)
                    .filter(ModelVersion.scene_id == task.scene_id)
                    .count()
                )
                version = f"v{existing_count + 1}.0.0"

                rel_model_path = os.path.relpath(weights_path, BACKEND_DIR)

                model_version = ModelVersion(
                    scene_id=task.scene_id,
                    training_task_id=task_id,
                    version=version,
                    model_name=f"{task.model_name}_{scene.name}_{version}"
                    if scene
                    else f"{task.model_name}_{task_id}",
                    model_type=task.model_name,
                    model_path=rel_model_path,
                    map50=overall["map50"],
                    map50_95=overall["map50_95"],
                    precision=overall["precision"],
                    recall=overall["recall"],
                    per_class_ap=per_class,
                    file_size=os.path.getsize(weights_path),
                    description=f"训练任务 {task.task_uuid} 自动产出",
                )
                db.add(model_version)
            else:
                model_version.map50 = overall["map50"]
                model_version.map50_95 = overall["map50_95"]
                model_version.precision = overall["precision"]
                model_version.recall = overall["recall"]
                model_version.per_class_ap = per_class

            db.commit()
            report["model_version_id"] = model_version.id
            report["model_version"] = model_version.version

            logger.info(
                "模型评估完成: task_id=%d, mAP50=%.4f, mAP50-95=%.4f",
                task_id,
                overall["map50"],
                overall["map50_95"],
            )

            return report

        except Exception as e:
            logger.error(
                "模型评估异常: task_id=%d, error=%s", task_id, str(e), exc_info=True
            )
            return {"error": f"评估失败: {str(e)}"}

    @staticmethod
    def export_model(
        db,
        task_id: int,
        version: str | None = None,
        description: str | None = None,
        set_default: bool = False,
        upload_minio: bool = True,
    ) -> dict:
        """
        导出训练好的模型为正式版本

        流程：
          1. 复制 best.pt 到 models/ 目录
          2. 运行评估获取最终指标
          3. 保存评估报告 JSON
          4. 创建 ModelVersion 记录
          5. 可选上传到 MinIO

        Args:
            db: 数据库会话
            task_id: 训练任务 ID
            version: 版本号（如 v1.0.0，不传则自动生成）
            description: 版本描述/变更说明
            set_default: 是否设为该场景的默认模型
            upload_minio: 是否上传到 MinIO

        Returns:
            导出结果字典
        """
        import shutil
        import json
        from app.entity.db_models import ModelVersion, DetectionScene

        # 查找训练任务
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            return {"error": "训练任务不存在"}

        if task.status != "completed":
            return {"error": f"训练任务状态为 {task.status}，只有已完成的任务才能导出"}

        # 定位 best.pt
        weights_path = os.path.join(
            BACKEND_DIR,
            settings.TRAIN_OUTPUT_DIR,
            f"task_{task.task_uuid}",
            "weights",
            "best.pt",
        )

        if not os.path.exists(weights_path):
            return {"error": f"模型权重不存在: {weights_path}"}

        # 获取场景信息
        scene = (
            db.query(DetectionScene)
            .filter(DetectionScene.id == task.scene_id)
            .first()
        )
        if not scene:
            return {"error": "关联场景不存在"}

        # 生成版本号
        if not version:
            existing_count = (
                db.query(ModelVersion)
                .filter(ModelVersion.scene_id == task.scene_id)
                .count()
            )
            version = f"v{existing_count + 1}.0.0"

        # 创建导出目录
        export_dir = os.path.join(
            BACKEND_DIR,
            "models",
            f"{scene.name}_{version}",
        )
        os.makedirs(export_dir, exist_ok=True)

        # 复制模型文件
        exported_weight = os.path.join(export_dir, "best.pt")
        shutil.copy2(weights_path, exported_weight)
        logger.info("模型文件已复制: %s → %s", weights_path, exported_weight)

        # 复制评估图表（如果存在）
        task_output_dir = os.path.join(
            BACKEND_DIR,
            settings.TRAIN_OUTPUT_DIR,
            f"task_{task.task_uuid}",
        )
        eval_plots = [
            "confusion_matrix.png",
            "PR_curve.png",
            "F1_curve.png",
            "results.png",
        ]
        for plot_name in eval_plots:
            src = os.path.join(task_output_dir, plot_name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(export_dir, plot_name))

        # 运行评估（获取最终指标）
        eval_result = TrainingService.validate_model(db, task_id, split="val")
        overall = eval_result.get("overall", {})
        per_class = eval_result.get("per_class", {})

        # 保存评估报告 JSON
        report = {
            "version": version,
            "model_name": task.model_name,
            "scene": scene.name,
            "training_task": task.task_uuid,
            "evaluation": {
                "split": "val",
                "overall": overall,
                "per_class": per_class,
            },
            "training_config": {
                "epochs": task.epochs,
                "batch_size": task.batch_size,
                "img_size": task.img_size,
                "optimizer": task.optimizer,
                "lr0": task.lr0,
                "device": task.device,
            },
            "exported_at": datetime.now().isoformat(),
        }
        report_path = os.path.join(export_dir, "eval_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # 上传到 MinIO
        minio_url = None
        if upload_minio:
            try:
                from app.storage.minio_client import MinIOClient
                minio_client = MinIOClient()
                object_name = f"models/{scene.name}/{version}/best.pt"
                minio_url = minio_client.upload_file(object_name, exported_weight)
                logger.info("模型已上传 MinIO: %s", minio_url)
            except Exception as e:
                logger.warning("MinIO 上传失败（不影响导出）: %s", str(e))

        # 创建/更新 ModelVersion 记录
        model_version = (
            db.query(ModelVersion)
            .filter(ModelVersion.training_task_id == task_id)
            .first()
        )

        rel_model_path = os.path.relpath(exported_weight, BACKEND_DIR)

        if model_version:
            model_version.version = version
            model_version.model_path = rel_model_path
            model_version.minio_url = minio_url
            model_version.map50 = overall.get("map50")
            model_version.map50_95 = overall.get("map50_95")
            model_version.precision = overall.get("precision")
            model_version.recall = overall.get("recall")
            model_version.per_class_ap = per_class
            model_version.file_size = os.path.getsize(exported_weight)
            model_version.description = description or f"训练任务 {task.task_uuid} 导出"
        else:
            model_version = ModelVersion(
                scene_id=task.scene_id,
                training_task_id=task_id,
                version=version,
                model_name=f"{task.model_name}_{scene.name}_{version}",
                model_type=task.model_name,
                model_path=rel_model_path,
                minio_url=minio_url,
                map50=overall.get("map50"),
                map50_95=overall.get("map50_95"),
                precision=overall.get("precision"),
                recall=overall.get("recall"),
                per_class_ap=per_class,
                file_size=os.path.getsize(exported_weight),
                description=description or f"训练任务 {task.task_uuid} 导出",
            )
            db.add(model_version)

        # 设置默认模型
        if set_default:
            db.query(ModelVersion).filter(
                ModelVersion.scene_id == task.scene_id,
                ModelVersion.id != model_version.id,
            ).update({"is_default": False})
            db.query(ModelVersion).filter(
                ModelVersion.id == model_version.id,
            ).update({"is_default": True})

        db.commit()
        db.refresh(model_version)

        logger.info(
            "模型导出完成: scene=%s, version=%s, mAP50=%.4f",
            scene.name, version, overall.get("map50", 0),
        )

        return {
            "model_version_id": model_version.id,
            "version": version,
            "model_name": model_version.model_name,
            "model_path": exported_weight,
            "export_dir": export_dir,
            "minio_url": minio_url,
            "file_size": model_version.file_size,
            "evaluation": {
                "map50": overall.get("map50"),
                "map50_95": overall.get("map50_95"),
                "precision": overall.get("precision"),
                "recall": overall.get("recall"),
                "per_class": per_class,
            },
            "is_default": model_version.is_default,
            "message": f"模型已导出为版本 {version}",
        }

    @staticmethod
    def get_model_download_path(db, task_id: int) -> dict:
        """
        获取训练任务的模型权重文件路径（用于下载）

        Args:
            db: 数据库会话
            task_id: 训练任务 ID

        Returns:
            包含文件路径和文件名的字典
        """
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            return {"error": "训练任务不存在"}

        weights_path = os.path.join(
            BACKEND_DIR,
            settings.TRAIN_OUTPUT_DIR,
            f"task_{task.task_uuid}",
            "weights",
            "best.pt",
        )

        if os.path.exists(weights_path):
            return {
                "file_path": weights_path,
                "filename": f"best_{task.task_uuid}.pt",
                "file_size": os.path.getsize(weights_path),
            }

        # 备选 last.pt
        last_path = os.path.join(
            BACKEND_DIR,
            settings.TRAIN_OUTPUT_DIR,
            f"task_{task.task_uuid}",
            "weights",
            "last.pt",
        )

        if os.path.exists(last_path):
            return {
                "file_path": last_path,
                "filename": f"last_{task.task_uuid}.pt",
                "file_size": os.path.getsize(last_path),
            }

        return {"error": "模型权重文件不存在"}

    @staticmethod
    def parse_results_csv(results_csv_path: str) -> list:
        """独立解析 results.csv 文件（工具方法）"""
        metrics = []
        if not os.path.exists(results_csv_path):
            return metrics

        with open(results_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = {k.strip(): v.strip() for k, v in row.items()}
                metrics.append(
                    {
                        "epoch": int(row.get("epoch", 0)) + 1,
                        "box_loss": _safe_float(row.get("train/box_loss", "")),
                        "cls_loss": _safe_float(row.get("train/cls_loss", "")),
                        "dfl_loss": _safe_float(row.get("train/dfl_loss", "")),
                        "precision": _safe_float(row.get("metrics/precision(B)", "")),
                        "recall": _safe_float(row.get("metrics/recall(B)", "")),
                        "map50": _safe_float(row.get("metrics/mAP50(B)", "")),
                        "map50_95": _safe_float(row.get("metrics/mAP50-95(B)", "")),
                        "lr": _safe_float(row.get("lr/pg0", "")),
                    }
                )

        return metrics

    @staticmethod
    def _create_model_version(
        db,
        task_id: int,
        task_uuid: str,
        config: dict,
        project_path: str,
    ):
        """
        训练完成后创建模型版本记录
        """
        task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
        if not task:
            logger.warning("创建模型版本失败：训练任务不存在")
            return

        best_model_path = os.path.join(
            project_path,
            f"task_{task_uuid}",
            "weights",
            "best.pt",
        )

        if not os.path.exists(best_model_path):
            logger.warning("best.pt 模型文件不存在: %s", best_model_path)
            return

        latest_metric = (
            db.query(TrainingMetric)
            .filter(TrainingMetric.task_id == task_id)
            .order_by(TrainingMetric.epoch.desc())
            .first()
        )

        file_size = os.path.getsize(best_model_path)

        rel_model_path = os.path.relpath(best_model_path, BACKEND_DIR)

        version_count = (
            db.query(ModelVersion)
            .filter(ModelVersion.scene_id == task.scene_id)
            .count()
        )
        version_number = f"v{version_count + 1}.0.0"

        model_version = ModelVersion(
            scene_id=task.scene_id,
            training_task_id=task.id,
            version=version_number,
            model_name=f"{task.model_name}_trained",
            model_type=task.model_name,
            status="active",
            model_path=rel_model_path,
            map50=latest_metric.map50 if latest_metric else None,
            map50_95=latest_metric.map50_95 if latest_metric else None,
            precision=latest_metric.precision if latest_metric else None,
            recall=latest_metric.recall if latest_metric else None,
            file_size=file_size,
            is_default=True,
        )

        db.add(model_version)
        db.commit()

        logger.info(
            "模型版本已创建: id=%d, name=%s, version=%s, path=%s",
            model_version.id,
            model_version.model_name,
            model_version.version,
            model_version.model_path,
        )


# 全局单例
training_service = TrainingService()

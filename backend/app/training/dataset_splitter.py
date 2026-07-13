"""
数据集划分与目录组织工具

职责：
  - 将图像和标注文件按指定比例划分到 train/val/test 目录
  - 自动创建目录结构
  - 验证图像与标注的配对完整性

使用方式：
  from app.training.dataset_splitter import DatasetSplitter

  splitter = DatasetSplitter()
  splitter.organize_dataset(
      image_dir="datasets/rsod/raw/images",
      label_dir="datasets/rsod/raw/annotations",
      output_dir="datasets/rsod/yolo_dataset",
      train_ratio=0.8,
      val_ratio=0.1,
      test_ratio=0.1
  )
"""

import os
import random
import shutil
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


class DatasetSplitter:
    """数据集划分与目录组织工具"""

    @staticmethod
    def organize_dataset(
        image_dir: str,
        label_dir: str,
        output_dir: str,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> dict:
        """
        将图像和标注文件按比例划分到 train/val/test 目录

        支持两种模式：
        模式1（推荐）：从原始目录划分，image_dir 直接包含图片文件
        模式2：从已划分目录整理，image_dir 包含 train/val/test 子目录

        Args:
            image_dir: 图像目录（原始目录或已划分目录）
            label_dir: 标注目录（原始目录或已划分目录）
            output_dir: 输出目录（将创建标准 YOLO 目录结构）
            train_ratio: 训练集比例
            val_ratio: 验证集比例
            test_ratio: 测试集比例
            seed: 随机种子（确保可重复）

        Returns:
            划分统计信息（始终包含 train/val/test 键）
        """
        random.seed(seed)

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        image_dir_path = Path(image_dir)

        # 检测模式：检查是否包含 train/val/test 子目录
        subdirs = {d.name for d in image_dir_path.iterdir() if d.is_dir()}
        has_split_subdirs = {"train", "val", "test"}.issubset(subdirs)

        if has_split_subdirs:
            # 模式2：从已划分目录整理
            logger.info("检测到已划分目录结构，直接整理...")
            return DatasetSplitter._organize_from_split_dirs(
                image_dir, label_dir, output_dir
            )
        else:
            # 模式1：从原始目录划分
            image_files = sorted(
                [
                    f
                    for f in image_dir_path.iterdir()
                    if f.suffix.lower() in image_extensions
                ]
            )

            if not image_files:
                logger.error("图像目录 %s 下未找到图像文件", image_dir)
                return {
                    "train": 0,
                    "val": 0,
                    "test": 0,
                    "missing_labels": [],
                    "error": "未找到图像文件",
                }

            logger.info("找到 %d 张图像，开始划分...", len(image_files))

            random.shuffle(image_files)

            total = len(image_files)
            train_end = int(total * train_ratio)
            val_end = train_end + int(total * val_ratio)

            splits = {
                "train": image_files[:train_end],
                "val": image_files[train_end:val_end],
                "test": image_files[val_end:],
            }

            stats = {"train": 0, "val": 0, "test": 0, "missing_labels": []}

            for split_name, files in splits.items():
                img_out = Path(output_dir) / "images" / split_name
                lbl_out = Path(output_dir) / "labels" / split_name
                img_out.mkdir(parents=True, exist_ok=True)
                lbl_out.mkdir(parents=True, exist_ok=True)

                for img_file in files:
                    shutil.copy2(img_file, img_out / img_file.name)

                    label_file = Path(label_dir) / f"{img_file.stem}.txt"
                    if label_file.exists():
                        shutil.copy2(label_file, lbl_out / label_file.name)
                        stats[split_name] += 1
                    else:
                        empty_label = lbl_out / f"{img_file.stem}.txt"
                        empty_label.touch()
                        stats["missing_labels"].append(img_file.name)
                        stats[split_name] += 1
                        logger.warning(
                            "图像 %s 无对应标注文件，已创建空标注", img_file.name
                        )

            logger.info(
                "数据集划分完成：train=%d, val=%d, test=%d, 缺失标注=%d",
                stats["train"],
                stats["val"],
                stats["test"],
                len(stats["missing_labels"]),
            )
            return stats

    @staticmethod
    def _organize_from_split_dirs(
        image_dir: str, label_dir: str, output_dir: str
    ) -> dict:
        """
        从已划分的目录结构中整理数据
        """
        stats = {"train": 0, "val": 0, "test": 0, "missing_labels": []}
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

        for split_name in ["train", "val", "test"]:
            src_img_dir = Path(image_dir) / split_name
            src_lbl_dir = Path(label_dir) / split_name
            dst_img_dir = Path(output_dir) / "images" / split_name
            dst_lbl_dir = Path(output_dir) / "labels" / split_name

            dst_img_dir.mkdir(parents=True, exist_ok=True)
            dst_lbl_dir.mkdir(parents=True, exist_ok=True)

            if not src_img_dir.exists():
                logger.warning("源目录 %s 不存在，跳过", src_img_dir)
                continue

            image_files = [
                f for f in src_img_dir.iterdir() if f.suffix.lower() in image_extensions
            ]

            for img_file in image_files:
                shutil.copy2(img_file, dst_img_dir / img_file.name)

                label_file = src_lbl_dir / f"{img_file.stem}.txt"
                if label_file.exists():
                    shutil.copy2(label_file, dst_lbl_dir / label_file.name)
                    stats[split_name] += 1
                else:
                    empty_label = dst_lbl_dir / f"{img_file.stem}.txt"
                    empty_label.touch()
                    stats["missing_labels"].append(img_file.name)
                    stats[split_name] += 1
                    logger.warning(
                        "图像 %s 无对应标注文件，已创建空标注", img_file.name
                    )

        logger.info(
            "数据集整理完成：train=%d, val=%d, test=%d, 缺失标注=%d",
            stats["train"],
            stats["val"],
            stats["test"],
            len(stats["missing_labels"]),
        )
        return stats

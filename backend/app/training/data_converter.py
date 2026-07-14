# backend/app/training/data_converter.py
"""
数据集格式转换器

职责：
- 将 VOC XML 格式转换为 YOLO TXT 格式
- 将 COCO JSON 格式转换为 YOLO TXT 格式
- 将 LabelMe JSON 格式转换为 YOLO TXT 格式
- 所有转换均输出 YOLO 归一化坐标格式

使用方式：
    from app.training.data_converter import DataConverter

    # VOC 转换
    converter = DataConverter()
    converter.voc_to_yolo(
        xml_dir="datasets/rsod/raw/annotations",
        output_dir="datasets/rsod/yolo_dataset/labels/train",
        class_mapping={"aircraft": 0, "oiltank": 1, "overpass": 2, "playground": 3}
    )

    # COCO 转换
    converter.coco_to_yolo(
        json_file="datasets/rsod/raw/annotations/instances_train.json",
        output_dir="datasets/rsod/yolo_dataset/labels/train",
        class_mapping={"aircraft": 0, "oiltank": 1, "overpass": 2, "playground": 3}
    )

    # LabelMe 转换
    converter.labelme_to_yolo(
        json_dir="datasets/rsod/raw/annotations",
        output_dir="datasets/rsod/yolo_dataset/labels/train",
        class_mapping={"aircraft": 0, "oiltank": 1, "overpass": 2, "playground": 3}
    )
"""

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


class DataConverter:
    """数据集格式转换器 - 将各种标注格式统一转换为 YOLO TXT 格式"""

    # ============================================================
    # 1. VOC XML -> YOLO TXT
    # ============================================================

    @staticmethod
    def voc_to_yolo(xml_dir: str, output_dir: str, class_mapping: dict) -> dict:
        """
        VOC XML 格式 -> YOLO TXT 格式

        转换逻辑：
        1. 遍历 xml_dir 下所有 .xml 文件
        2. 解析每个 XML 获取图像尺寸和目标边界框
        3. 将像素坐标转换为 YOLO 归一化坐标
        4. 输出到 output_dir，每张图一个 .txt 文件

        Args:
            xml_dir: VOC XML 标注文件目录
            output_dir: YOLO TXT 输出目录
            class_mapping: 类别映射字典 {类名字符串: 类别ID整数}
                例如 {"airplane": 0, "storage-tank": 1}

        Returns:
            转换统计信息字典 {"total": 总数, "converted": 成功数, "skipped": 跳过数, "errors": 错误列表}
        """
        os.makedirs(output_dir, exist_ok=True)
        stats = {"total": 0, "converted": 0, "skipped": 0, "errors": []}

        xml_files = list(Path(xml_dir).glob("*.xml"))

        if not xml_files:
            logger.warning("VOC 转换: 目录 %s 下未找到 .xml 文件", xml_dir)
            return stats

        logger.info("VOC 转换开始: %d 个 XML 文件 -> %s", len(xml_files), output_dir)

        for xml_file in xml_files:
            stats["total"] += 1

            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                # 获取图像尺寸
                size = root.find("size")
                if size is None:
                    logger.warning("XML %s 缺少 <size> 标签, 跳过", xml_file.name)
                    stats["skipped"] += 1
                    continue

                width_elem = size.find("width")
                height_elem = size.find("height")
                if width_elem is None or height_elem is None:
                    logger.warning(
                        "XML %s 缺少 width 或 height 标签, 跳过", xml_file.name
                    )
                    stats["skipped"] += 1
                    continue

                if width_elem.text is None or height_elem.text is None:
                    logger.warning(
                        "XML %s 的 width 或 height 文本为空, 跳过", xml_file.name
                    )
                    stats["skipped"] += 1
                    continue

                img_width = int(width_elem.text)
                img_height = int(height_elem.text)

                if img_width <= 0 or img_height <= 0:
                    logger.warning(
                        "XML %s 图像尺寸无效 (%d, %d), 跳过",
                        xml_file.name,
                        img_width,
                        img_height,
                    )
                    stats["skipped"] += 1
                    continue

                # 解析所有目标
                yolo_lines = []

                for obj in root.findall("object"):
                    name_elem = obj.find("name")
                    if name_elem is None or name_elem.text is None:
                        continue

                    class_name = name_elem.text.strip()
                    if class_name not in class_mapping:
                        logger.warning(
                            "XML %s 中类别 '%s' 不在映射表中，跳过该目标",
                            xml_file.name,
                            class_name,
                        )
                        continue

                    class_id = class_mapping[class_name]
                    bbox = obj.find("bndbox")
                    if bbox is None:
                        continue

                    xmin_elem = bbox.find("xmin")
                    ymin_elem = bbox.find("ymin")
                    xmax_elem = bbox.find("xmax")
                    ymax_elem = bbox.find("ymax")

                    if (
                        xmin_elem is None
                        or ymin_elem is None
                        or xmax_elem is None
                        or ymax_elem is None
                    ):
                        continue

                    if (
                        xmin_elem.text is None
                        or ymin_elem.text is None
                        or xmax_elem.text is None
                        or ymax_elem.text is None
                    ):
                        continue

                    xmin = float(xmin_elem.text)
                    ymin = float(ymin_elem.text)
                    xmax = float(xmax_elem.text)
                    ymax = float(ymax_elem.text)

                    # 边界值裁剪：确保坐标不超出图像范围
                    xmin = max(0, min(xmin, img_width))
                    ymin = max(0, min(ymin, img_height))
                    xmax = max(0, min(xmax, img_width))
                    ymax = max(0, min(ymax, img_height))

                    # 过滤无效框（宽或高为0）
                    if xmax <= xmin or ymax <= ymin:
                        logger.warning(
                            "XML %s 中目标 '%s' 边界框无效，跳过",
                            xml_file.name,
                            class_name,
                        )
                        continue

                    # 像素坐标 -> YOLO 归一化坐标
                    x_center = (xmin + xmax) / 2.0 / img_width
                    y_center = (ymin + ymax) / 2.0 / img_height
                    width = (xmax - xmin) / img_width
                    height = (ymax - ymin) / img_height

                    yolo_lines.append(
                        f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                    )

                # 保存 YOLO 标注文件
                txt_file = Path(output_dir) / f"{xml_file.stem}.txt"
                with open(txt_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(yolo_lines))

                stats["converted"] += 1

            except ET.ParseError as e:
                logger.error("XML 解析失败 %s: %s", xml_file.name, str(e))
                stats["errors"].append(str(xml_file.name))
                stats["skipped"] += 1
            except Exception as e:
                logger.error("VOC 转换异常 %s: %s", xml_file.name, str(e))
                stats["errors"].append(str(xml_file.name))
                stats["skipped"] += 1

        logger.info(
            "VOC 转换完成：总计 %d，成功 %d，跳过 %d",
            stats["total"],
            stats["converted"],
            stats["skipped"],
        )

        return stats

    # ============================================================
    # 2. COCO JSON -> YOLO TXT
    # ============================================================

    @staticmethod
    def coco_to_yolo(
        json_file: str, output_dir: str, class_mapping: dict | None = None
    ) -> dict:
        """
        COCO JSON 格式 -> YOLO TXT 格式

        转换逻辑：
        1. 读取整个 COCO JSON 文件
        2. 构建 category_id -> class_id 映射
        3. 按 image_id 分组所有标注
        4. 遍历每张图像，将 COCO bbox 转换为 YOLO 归一化坐标
        5. 每张图像输出一个 .txt 文件

        Args:
            json_file: COCO 标注 JSON 文件路径
            output_dir: YOLO TXT 输出目录
            class_mapping: 可选的类别重映射
                如果为 None，则按 categories 中的顺序自动编号（从 0 开始）
                如果提供，格式为 {category_name: class_id}

        Returns:
            转换统计信息字典
        """
        os.makedirs(output_dir, exist_ok=True)
        stats = {"total": 0, "converted": 0, "skipped": 0, "errors": []}

        # 读取 COCO JSON
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                coco_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error("COCO JSON 读取失败 %s: %s", json_file, str(e))
            stats["errors"].append(str(e))
            return stats

        # 构建类别映射
        if class_mapping is None:
            # 自动按 categories 顺序编号（从 0 开始）
            category_mapping = {
                cat["id"]: idx
                for idx, cat in enumerate(coco_data.get("categories", []))
            }
            logger.info("COCO 自动类别映射: %s", category_mapping)
        else:
            # 使用用户提供的映射
            cat_name_to_id = {
                cat["name"]: cat["id"] for cat in coco_data.get("categories", [])
            }
            category_mapping = {}
            for cat_name, class_id in class_mapping.items():
                if cat_name in cat_name_to_id:
                    category_mapping[cat_name_to_id[cat_name]] = class_id
                else:
                    logger.warning("COCO categories 中未找到类别 '%s'", cat_name)

        # 按 image_id 分组标注
        image_annotations = {}
        for ann in coco_data.get("annotations", []):
            img_id = ann["image_id"]
            if img_id not in image_annotations:
                image_annotations[img_id] = []
            image_annotations[img_id].append(ann)

        # 遍历每张图像
        images = coco_data.get("images", [])
        stats["total"] = len(images)
        logger.info("COCO 转换开始: %d 张图像 -> %s", len(images), output_dir)

        for img_info in images:
            img_id = img_info["id"]
            img_width = img_info["width"]
            img_height = img_info["height"]
            file_name = img_info["file_name"]

            if img_width <= 0 or img_height <= 0:
                logger.warning("图像 %s 尺寸无效，跳过", file_name)
                stats["skipped"] += 1
                continue

            yolo_lines = []

            for ann in image_annotations.get(img_id, []):
                # 检查类别是否在映射中
                cat_id = ann["category_id"]
                if cat_id not in category_mapping:
                    continue

                class_id = category_mapping[cat_id]

                # COCO bbox: [x_min, y_min, width, height]（像素坐标）
                x_min, y_min, bbox_w, bbox_h = ann["bbox"]

                # 过滤无效框
                if bbox_w <= 0 or bbox_h <= 0:
                    continue

                # 边界值裁剪
                x_min = max(0, min(x_min, img_width))
                y_min = max(0, min(y_min, img_height))
                bbox_w = min(bbox_w, img_width - x_min)
                bbox_h = min(bbox_h, img_height - y_min)

                # COCO [x_min, y_min, w, h] -> YOLO [x_center, y_center, w, h]
                x_center = (x_min + bbox_w / 2.0) / img_width
                y_center = (y_min + bbox_h / 2.0) / img_height
                width = bbox_w / img_width
                height = bbox_h / img_height

                yolo_lines.append(
                    f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                )

            # 保存 YOLO 标注文件
            img_stem = Path(file_name).stem
            txt_file = Path(output_dir) / f"{img_stem}.txt"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write("\n".join(yolo_lines))

            stats["converted"] += 1

        logger.info(
            "COCO 转换完成：总计 %d，成功 %d，跳过 %d",
            stats["total"],
            stats["converted"],
            stats["skipped"],
        )

        return stats

    # ============================================================
    # 3. LabelMe JSON -> YOLO TXT
    # ============================================================

    @staticmethod
    def labelme_to_yolo(json_dir: str, output_dir: str, class_mapping: dict) -> dict:
        """
        LabelMe JSON 格式 -> YOLO TXT 格式

        转换逻辑：
        1. 遍历 json_dir 下所有 .json 文件
        2. 解析每个 JSON 获取图像尺寸和标注形状
        3. 只处理 shape_type 为 "rectangle" 的标注
        4. 从 points 中提取边界框，转换为 YOLO 归一化坐标
        5. 每张图像输出一个 .txt 文件

        Args:
            json_dir: LabelMe JSON 文件目录
            output_dir: YOLO TXT 输出目录
            class_mapping: 类别映射 {类别名: 类别ID}

        Returns:
            转换统计信息字典
        """
        os.makedirs(output_dir, exist_ok=True)
        stats = {"total": 0, "converted": 0, "skipped": 0, "errors": []}

        json_files = list(Path(json_dir).glob("*.json"))

        if not json_files:
            logger.warning("LabelMe 转换: 目录 %s 下未找到 .json 文件", json_dir)
            return stats

        logger.info(
            "LabelMe 转换开始: %d 个 JSON 文件 -> %s", len(json_files), output_dir
        )

        for json_file in json_files:
            stats["total"] += 1

            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    labelme_data = json.load(f)

                img_width = labelme_data.get("imageWidth", 0)
                img_height = labelme_data.get("imageHeight", 0)

                if img_width <= 0 or img_height <= 0:
                    logger.warning("JSON %s 图像尺寸无效, 跳过", json_file.name)
                    stats["skipped"] += 1
                    continue

                yolo_lines = []

                for shape in labelme_data.get("shapes", []):
                    # 只处理矩形标注
                    if shape.get("shape_type") != "rectangle":
                        continue

                    class_name = shape.get("label", "").strip()
                    if class_name not in class_mapping:
                        logger.warning(
                            "JSON %s 中类别 '%s' 不在映射表中, 跳过该目标",
                            json_file.name,
                            class_name,
                        )
                        continue

                    class_id = class_mapping[class_name]
                    points = shape.get("points", [])

                    if len(points) < 2:
                        continue

                    # 取最小外接矩形
                    all_x = [p[0] for p in points]
                    all_y = [p[1] for p in points]
                    xmin = min(all_x)
                    ymin = min(all_y)
                    xmax = max(all_x)
                    ymax = max(all_y)

                    # 边界值裁剪
                    xmin = max(0, min(xmin, img_width))
                    ymin = max(0, min(ymin, img_height))
                    xmax = max(0, min(xmax, img_width))
                    ymax = max(0, min(ymax, img_height))

                    # 过滤无效框
                    if xmax <= xmin or ymax <= ymin:
                        continue

                    # 像素坐标 -> YOLO 归一化坐标
                    x_center = (xmin + xmax) / 2.0 / img_width
                    y_center = (ymin + ymax) / 2.0 / img_height
                    width = (xmax - xmin) / img_width
                    height = (ymax - ymin) / img_height

                    yolo_lines.append(
                        f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                    )

                # 保存 YOLO 标注文件
                txt_file = Path(output_dir) / f"{json_file.stem}.txt"
                with open(txt_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(yolo_lines))

                stats["converted"] += 1

            except json.JSONDecodeError as e:
                logger.error("JSON 解析失败 %s: %s", json_file.name, str(e))
                stats["errors"].append(str(json_file.name))
                stats["skipped"] += 1
            except Exception as e:
                logger.error("LabelMe 转换异常 %s: %s", json_file.name, str(e))
                stats["errors"].append(str(json_file.name))
                stats["skipped"] += 1

        logger.info(
            "LabelMe 转换完成：总计 %d，成功 %d，跳过 %d",
            stats["total"],
            stats["converted"],
            stats["skipped"],
        )

        return stats

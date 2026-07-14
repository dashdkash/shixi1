#!/usr/bin/env python3
# backend/tools/convert_labelme.py
"""
LabelMe JSON -> YOLO TXT 数据集格式转换脚本

功能：
1. 将 LabelMe 格式的 JSON 标注文件转换为 YOLO 格式的 TXT 标注文件
2. 按 8:1:1 比例划分训练集/验证集/测试集
3. 生成 YOLO 训练所需的 data.yaml 配置文件

使用方式：
    cd rsod-agent-platform/backend
    python tools/convert_labelme.py
"""

import json
import os
import random
import shutil
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ========== 配置区域（根据你的数据集修改） ==========

# LabelMe JSON 文件目录
LABELME_JSON_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/raw/annotations")

# 原始图片目录
RAW_IMAGE_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/raw/images")

# YOLO 格式输出目录
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/yolo_dataset")

# 类别映射
CLASS_MAPPING = {
    "aircraft": 0,
    "oiltank": 1,
    "overpass": 2,
    "playground": 3,
}

# 数据集划分比例
TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1

# 随机种子
RANDOM_SEED = 42

# 支持的图片扩展名
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# ===================================================


def labelme_to_yolo(json_dir: str, output_dir: str, class_mapping: dict) -> dict:
    """将 LabelMe JSON 格式转换为 YOLO TXT 格式"""
    os.makedirs(output_dir, exist_ok=True)
    stats = {"total": 0, "converted": 0, "skipped": 0, "errors": [], "image_files": []}

    json_files = list(Path(json_dir).glob("*.json"))

    if not json_files:
        print(f"  [警告] 目录 {json_dir} 下未找到 .json 文件")
        return stats

    print(f"  LabelMe 转换开始: {len(json_files)} 个 JSON 文件")

    for json_file in json_files:
        stats["total"] += 1

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                labelme_data = json.load(f)

            img_width = labelme_data.get("imageWidth", 0)
            img_height = labelme_data.get("imageHeight", 0)

            if img_width <= 0 or img_height <= 0:
                print(f"  [警告] JSON {json_file.name} 图像尺寸无效, 跳过")
                stats["skipped"] += 1
                continue

            image_path = labelme_data.get("imagePath", "")
            image_filename = os.path.basename(image_path)
            stats["image_files"].append(image_filename)

            yolo_lines = []

            for shape in labelme_data.get("shapes", []):
                if shape.get("shape_type") != "rectangle":
                    continue

                class_name = shape.get("label", "").strip()
                if class_name not in class_mapping:
                    print(
                        f"  [警告] JSON {json_file.name} 中类别 '{class_name}' 不在映射表中, 跳过"
                    )
                    continue

                class_id = class_mapping[class_name]
                points = shape.get("points", [])

                if len(points) < 2:
                    continue

                all_x = [p[0] for p in points]
                all_y = [p[1] for p in points]
                xmin = min(all_x)
                ymin = min(all_y)
                xmax = max(all_x)
                ymax = max(all_y)

                xmin = max(0, min(xmin, img_width))
                ymin = max(0, min(ymin, img_height))
                xmax = max(0, min(xmax, img_width))
                ymax = max(0, min(ymax, img_height))

                if xmax <= xmin or ymax <= ymin:
                    continue

                x_center = (xmin + xmax) / 2.0 / img_width
                y_center = (ymin + ymax) / 2.0 / img_height
                width = (xmax - xmin) / img_width
                height = (ymax - ymin) / img_height

                yolo_lines.append(
                    f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                )

            txt_file = Path(output_dir) / f"{json_file.stem}.txt"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write("\n".join(yolo_lines))

            stats["converted"] += 1

        except json.JSONDecodeError as e:
            print(f"  [错误] JSON 解析失败 {json_file.name}: {str(e)}")
            stats["errors"].append(str(json_file.name))
            stats["skipped"] += 1
        except Exception as e:
            print(f"  [错误] LabelMe 转换异常 {json_file.name}: {str(e)}")
            stats["errors"].append(str(json_file.name))
            stats["skipped"] += 1

    print(
        f"  转换结果: 总计 {stats['total']}, 成功 {stats['converted']}, 跳过 {stats['skipped']}"
    )
    return stats


def split_dataset(image_files, temp_label_dir):
    """按比例划分数据集"""
    random.seed(RANDOM_SEED)
    random.shuffle(image_files)

    total = len(image_files)
    train_end = int(total * TRAIN_RATIO)
    val_end = train_end + int(total * VAL_RATIO)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:],
    }

    for split_name, files in splits.items():
        img_out = os.path.join(OUTPUT_DIR, "images", split_name)
        lbl_out = os.path.join(OUTPUT_DIR, "labels", split_name)
        os.makedirs(img_out, exist_ok=True)
        os.makedirs(lbl_out, exist_ok=True)

        for filename in files:
            src_image = os.path.join(RAW_IMAGE_DIR, filename)
            if os.path.exists(src_image):
                shutil.copy2(src_image, os.path.join(img_out, filename))

            basename = os.path.splitext(filename)[0]
            label_file = os.path.join(temp_label_dir, f"{basename}.txt")
            if os.path.exists(label_file):
                shutil.copy2(label_file, os.path.join(lbl_out, f"{basename}.txt"))
            else:
                open(os.path.join(lbl_out, f"{basename}.txt"), "w").close()

        print(f"  {split_name}: {len(files)} 个")

    return splits


def generate_yaml():
    """生成 YOLO 数据集配置文件"""
    class_names = sorted(CLASS_MAPPING.keys(), key=lambda x: CLASS_MAPPING[x])

    yaml_content = f"""path: ./{os.path.basename(OUTPUT_DIR)}
train: images/train
val: images/val
test: images/test
nc: {len(class_names)}
names:
"""

    for i, name in enumerate(class_names):
        yaml_content += f"  {i}: {name}\n"

    yaml_path = os.path.join(OUTPUT_DIR, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"  配置文件已生成: {yaml_path}")


def main():
    """主函数"""
    print("=" * 70)
    print(" LabelMe JSON -> YOLO TXT 数据集转换流程")
    print("=" * 70)

    if not os.path.exists(LABELME_JSON_DIR):
        print(f"\n[错误] LabelMe JSON 目录不存在: {LABELME_JSON_DIR}")
        return

    if not os.path.exists(RAW_IMAGE_DIR):
        print(f"\n[错误] 原始图片目录不存在: {RAW_IMAGE_DIR}")
        return

    print("\n[1] LabelMe 转 YOLO 格式")
    temp_label_dir = os.path.join(OUTPUT_DIR, "temp_labels")
    os.makedirs(temp_label_dir, exist_ok=True)

    stats = labelme_to_yolo(LABELME_JSON_DIR, temp_label_dir, CLASS_MAPPING)
    if stats["total"] == 0:
        print("\n[错误] 未找到任何 JSON 文件")
        shutil.rmtree(temp_label_dir, ignore_errors=True)
        return

    print("\n[2] 划分数据集")
    split_dataset(stats["image_files"], temp_label_dir)

    print("\n[3] 生成 data.yaml")
    generate_yaml()

    shutil.rmtree(temp_label_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print(f" 处理完成! 输出目录: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()

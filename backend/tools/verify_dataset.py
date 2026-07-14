#!/usr/bin/env python3
# backend/tools/verify_dataset.py
"""
YOLO 数据集验证脚本

功能：
1. 目录结构是否符合 YOLO 规范 (images/train、images/val、labels/train、labels/val)
2. 图像与标注文件是否一一对应（文件名匹配检查）
3. 标注文件格式是否正确（每行必须为 5 个值：class_id x_center y_center width height）
4. 类别 ID 是否有效（必须为整数）
5. 归一化坐标是否在 [0, 1] 范围内
6. 统计各类别的标注数量和占比
7. 类别不平衡检测和警告（比例 > 10:1 视为严重不平衡）
8. 边界框统计（平均尺寸、最小/最大尺寸、小目标占比）
9. 每个 split (train/val/test) 的详细统计

使用方式：
    cd rsod-agent-platform/backend
    python tools/verify_dataset.py

或指定数据集目录：
    python tools/verify_dataset.py /path/to/dataset
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 支持的图片扩展名集合
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def load_yaml_classes(dataset_dir: Path) -> dict:
    """
    加载 data.yaml 中的类别定义（纯文本解析，不依赖 yaml 库）
    """
    yaml_path = dataset_dir / "data.yaml"
    if not yaml_path.exists():
        return {}

    try:
        names = {}
        with open(yaml_path, "r", encoding="utf-8") as f:
            in_names = False
            for line in f:
                line = line.strip()
                if line.startswith("names:"):
                    in_names = True
                    continue
                if in_names and line:
                    if line[0].isdigit():
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            class_id = int(parts[0].strip())
                            class_name = parts[1].strip()
                            names[class_id] = class_name
                elif in_names and not line:
                    break
        return names
    except Exception:
        return {}


def verify_dataset(dataset_dir: str) -> dict:
    """
    验证 YOLO 数据集完整性，返回详细的验证结果
    """
    results = {
        "total_images": 0,
        "total_labels": 0,
        "total_annotations": 0,
        "missing_labels": [],
        "missing_images": [],
        "empty_labels": 0,
        "invalid_format": [],
        "out_of_range": [],
        "class_distribution": {},
        "class_names": {},
        "bbox_stats": {
            "total": 0,
            "avg_width": 0,
            "avg_height": 0,
            "max_width": 0,
            "max_height": 0,
            "min_width": float("inf"),
            "min_height": float("inf"),
            "small_boxes": 0,
            "large_boxes": 0,
        },
        "split_stats": {},
        "has_warnings": False,
    }

    dataset_path = Path(dataset_dir)
    class_names = load_yaml_classes(dataset_path)
    results["class_names"] = class_names

    for split in ["train", "val", "test"]:
        img_dir = dataset_path / "images" / split
        lbl_dir = dataset_path / "labels" / split

        split_result = {
            "images": 0,
            "labels": 0,
            "annotations": 0,
            "missing_labels": 0,
            "missing_images": 0,
            "class_distribution": {},
        }

        if not img_dir.exists():
            if split != "test":
                print(f"  [警告] 缺少目录: {img_dir}")
            results["split_stats"][split] = split_result
            continue

        if not lbl_dir.exists():
            print(f"  [警告] 缺少目录: {lbl_dir}")
            results["split_stats"][split] = split_result
            continue

        image_files = {
            f.stem for f in img_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS
        }
        label_files = {f.stem for f in lbl_dir.iterdir() if f.suffix == ".txt"}

        missing_labels = image_files - label_files
        missing_images = label_files - image_files

        split_result["images"] = len(image_files)
        split_result["labels"] = len(label_files)
        split_result["missing_labels"] = len(missing_labels)
        split_result["missing_images"] = len(missing_images)

        results["missing_labels"].extend([f"{split}/{name}" for name in missing_labels])
        results["missing_images"].extend([f"{split}/{name}" for name in missing_images])
        results["total_images"] += len(image_files)
        results["total_labels"] += len(label_files)

        bbox_widths = []
        bbox_heights = []

        for label_file in lbl_dir.glob("*.txt"):
            content = label_file.read_text(encoding="utf-8").strip()

            if not content:
                results["empty_labels"] += 1
                continue

            for line_num, line in enumerate(content.split("\n"), 1):
                parts = line.strip().split()

                if len(parts) != 5:
                    results["invalid_format"].append(
                        f"{split}/{label_file.name}:{line_num}（期望5个值，实际{len(parts)}）"
                    )
                    continue

                try:
                    class_id = int(parts[0])
                except ValueError:
                    results["invalid_format"].append(
                        f"{split}/{label_file.name}:{line_num}（class_id 非整数）"
                    )
                    continue

                results["class_distribution"][class_id] = (
                    results["class_distribution"].get(class_id, 0) + 1
                )
                split_result["class_distribution"][class_id] = (
                    split_result["class_distribution"].get(class_id, 0) + 1
                )

                results["total_annotations"] += 1
                split_result["annotations"] += 1

                try:
                    coords = [float(v) for v in parts[1:]]
                    x_center, y_center, width, height = coords

                    field_names = ["x_center", "y_center", "width", "height"]
                    for i, v in enumerate(coords):
                        if v < 0 or v > 1:
                            results["out_of_range"].append(
                                f"{split}/{label_file.name}:{line_num} {field_names[i]}={v:.6f}"
                            )
                            break

                    bbox_widths.append(width)
                    bbox_heights.append(height)

                except ValueError:
                    results["invalid_format"].append(
                        f"{split}/{label_file.name}:{line_num}（坐标值非浮点数）"
                    )

        if bbox_widths:
            results["bbox_stats"]["total"] += len(bbox_widths)
            results["bbox_stats"]["avg_width"] += sum(bbox_widths)
            results["bbox_stats"]["avg_height"] += sum(bbox_heights)
            results["bbox_stats"]["max_width"] = max(
                results["bbox_stats"]["max_width"], max(bbox_widths)
            )
            results["bbox_stats"]["max_height"] = max(
                results["bbox_stats"]["max_height"], max(bbox_heights)
            )
            results["bbox_stats"]["min_width"] = min(
                results["bbox_stats"]["min_width"], min(bbox_widths)
            )
            results["bbox_stats"]["min_height"] = min(
                results["bbox_stats"]["min_height"], min(bbox_heights)
            )
            results["bbox_stats"]["small_boxes"] += sum(
                1 for w, h in zip(bbox_widths, bbox_heights) if w * h < 0.001
            )
            results["bbox_stats"]["large_boxes"] += sum(
                1 for w, h in zip(bbox_widths, bbox_heights) if w * h > 0.5
            )

        results["split_stats"][split] = split_result

    if results["bbox_stats"]["total"] > 0:
        results["bbox_stats"]["avg_width"] /= results["bbox_stats"]["total"]
        results["bbox_stats"]["avg_height"] /= results["bbox_stats"]["total"]

    return results


def print_report(results: dict):
    """打印格式化的验证报告"""
    print("\n" + "=" * 70)
    print(" YOLO 数据集验证报告")
    print("=" * 70)

    print("\n [总体统计]")
    print(f"  图像总数：{results['total_images']}")
    print(f"  标注文件数：{results['total_labels']}")
    print(f"  标注目标数：{results['total_annotations']}")
    print(f"  空标注文件：{results['empty_labels']}")
    if results["total_images"] > 0:
        print(
            f"  平均每图标注：{results['total_annotations'] / results['total_images']:.2f}"
        )

    print("\n [Split 统计]")
    for split in ["train", "val", "test"]:
        stats = results["split_stats"].get(split, {})
        print(
            f"  {split}: {stats.get('images', 0)} 图像, {stats.get('labels', 0)} 标注, "
            f"{stats.get('annotations', 0)} 目标"
        )

    if results["missing_labels"]:
        print(f"\n [警告] 缺少标注文件 ({len(results['missing_labels'])} 个):")
        for name in results["missing_labels"][:5]:
            print(f"   - {name}")
        if len(results["missing_labels"]) > 5:
            print(f"   ... 还有 {len(results['missing_labels']) - 5} 个")
        results["has_warnings"] = True

    if results["missing_images"]:
        print(f"\n [警告] 缺少图像文件 ({len(results['missing_images'])} 个):")
        for name in results["missing_images"][:5]:
            print(f"   - {name}")
        if len(results["missing_images"]) > 5:
            print(f"   ... 还有 {len(results['missing_images']) - 5} 个")
        results["has_warnings"] = True

    if results["invalid_format"]:
        print(f"\n [错误] 格式错误 ({len(results['invalid_format'])} 处):")
        for item in results["invalid_format"][:5]:
            print(f"   - {item}")
        if len(results["invalid_format"]) > 5:
            print(f"   ... 还有 {len(results['invalid_format']) - 5} 处")
        results["has_warnings"] = True

    if results["out_of_range"]:
        print(f"\n [警告] 坐标越界 ({len(results['out_of_range'])} 处):")
        for item in results["out_of_range"][:5]:
            print(f"   - {item}")
        if len(results["out_of_range"]) > 5:
            print(f"   ... 还有 {len(results['out_of_range']) - 5} 处")
        results["has_warnings"] = True

    print("\n [类别分布]")
    class_names = results["class_names"]
    total = results["total_annotations"] or 1

    if results["class_distribution"]:
        max_count = max(results["class_distribution"].values())
        min_count = min(results["class_distribution"].values())
        imbalance_ratio = max_count / min_count if min_count > 0 else float("inf")

        for class_id in sorted(results["class_distribution"].keys()):
            count = results["class_distribution"][class_id]
            percentage = (count / total) * 100
            class_name = class_names.get(class_id, f"class_{class_id}")
            bar_length = int((count / max_count) * 40) if max_count > 0 else 0
            bar = "*" * bar_length + " " * (40 - bar_length)
            print(
                f"  {class_id:2d}. {class_name:12s} {count:6d} 个 {percentage:5.2f}%  [{bar}]"
            )

        if imbalance_ratio > 10:
            print(
                f"\n [警告] 类别严重不平衡! 最大/最小类别比例 = {imbalance_ratio:.1f}:1"
            )
            print("   建议: 增加少数类样本或使用数据增强技术")
            results["has_warnings"] = True
        elif imbalance_ratio > 5:
            print(f"\n [提示] 类别存在一定不平衡, 比例 = {imbalance_ratio:.1f}:1")

    print("\n [边界框统计]")
    bbox = results["bbox_stats"]
    if bbox["total"] > 0:
        print(f"  边界框总数: {bbox['total']}")
        print(f"  平均宽度: {bbox['avg_width']:.4f}")
        print(f"  平均高度: {bbox['avg_height']:.4f}")
        print(f"  最小宽度: {bbox['min_width']:.4f}")
        print(f"  最小高度: {bbox['min_height']:.4f}")
        print(f"  最大宽度: {bbox['max_width']:.4f}")
        print(f"  最大高度: {bbox['max_height']:.4f}")
        print(
            f"  小目标(面积<0.001): {bbox['small_boxes']} 个 ({bbox['small_boxes'] / bbox['total'] * 100:.1f}%)"
        )
        print(
            f"  大目标(面积>0.5): {bbox['large_boxes']} 个 ({bbox['large_boxes'] / bbox['total'] * 100:.1f}%)"
        )

        if bbox["small_boxes"] / bbox["total"] > 0.3:
            print("\n [提示] 小目标占比较高 (>30%), 建议使用合适的锚框配置")

    print("\n" + "-" * 70)
    if results["has_warnings"]:
        print(" 结果: △ 数据集存在问题或警告, 请根据上述信息修复")
    else:
        print(" 结果: ✓ 数据集验证通过, 可以开始训练")
    print("-" * 70 + "\n")


if __name__ == "__main__":
    # 默认数据集目录
    DATASET_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/yolo_dataset")

    if len(sys.argv) > 1:
        DATASET_DIR = sys.argv[1]

    if not os.path.exists(DATASET_DIR):
        print(f"[错误] 数据集目录不存在: {DATASET_DIR}")
        sys.exit(1)

    results = verify_dataset(DATASET_DIR)
    print_report(results)

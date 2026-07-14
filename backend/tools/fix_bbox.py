#!/usr/bin/env python3
# backend/tools/fix_bbox.py
"""
修复 YOLO 标注文件中的越界边界框

功能：
1. 遍历所有标注文件，检查坐标是否在 [0, 1] 范围内
2. 将越界坐标裁剪到有效范围
3. 删除无效边界框（宽或高 <= 0）
4. 输出修复统计报告

使用方式：
    cd rsod-agent-platform/backend
    python tools/fix_bbox.py
"""

import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(PROJECT_ROOT, "datasets/rsod/yolo_dataset")


def fix_bbox_coordinates(label_dir: str) -> dict:
    """修复单个目录下的标注文件"""
    stats = {"fixed": 0, "deleted": 0, "total": 0, "files_affected": 0}

    if not os.path.exists(label_dir):
        return stats

    for filename in os.listdir(label_dir):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(label_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        file_fixed = 0
        file_deleted = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) != 5:
                file_deleted += 1
                continue

            try:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
            except ValueError:
                file_deleted += 1
                continue

            # 裁剪超界坐标到 [0, 1]
            orig = (x_center, y_center, width, height)
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            width = max(0.0, min(1.0, width))
            height = max(0.0, min(1.0, height))

            if orig != (x_center, y_center, width, height):
                file_fixed += 1

            if width <= 0 or height <= 0:
                file_deleted += 1
                continue

            new_lines.append(
                f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
            )

        if file_fixed > 0 or file_deleted > 0 or len(new_lines) != len(lines):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))

            stats["fixed"] += file_fixed
            stats["deleted"] += file_deleted
            stats["total"] += len(lines)
            stats["files_affected"] += 1

    return stats


def main():
    print("=" * 70)
    print(" 修复 YOLO 标注文件中的越界边界框")
    print("=" * 70)

    total_stats = {"fixed": 0, "deleted": 0, "total": 0, "files_affected": 0}

    for split in ["train", "val", "test"]:
        label_dir = os.path.join(DATASET_DIR, "labels", split)
        print(f"\n[处理 {split}]")
        if not os.path.exists(label_dir):
            print("  目录不存在，跳过")
            continue

        stats = fix_bbox_coordinates(label_dir)
        print(f"  修复: {stats['fixed']} 个边界框")
        print(f"  删除: {stats['deleted']} 个无效边界框")
        print(f"  影响文件: {stats['files_affected']} 个")

        for key in total_stats:
            total_stats[key] += stats[key]

    print("\n" + "=" * 70)
    print(" 修复完成!")
    print(f"  总计边界框: {total_stats['total']}")
    print(f"  修复越界: {total_stats['fixed']} 个")
    print(f"  删除无效: {total_stats['deleted']} 个")
    print(f"  影响文件: {total_stats['files_affected']} 个")
    print("=" * 70)


if __name__ == "__main__":
    main()

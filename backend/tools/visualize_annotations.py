#!/usr/bin/env python3
# backend/tools/visualize_annotations.py
"""
YOLO数据集标注可视化工具

功能：
1. 在图像上绘制YOLO格式标注框和类别标签
2. 支持随机抽样或指定文件查看
3. 支持单张查看和批量导出
4. 不同类别使用不同颜色，方便区分
5. 标注框旁显示类别名称

使用方式：
    cd rsod-agent-platform/backend
    # 随机抽样5张可视化
    python tools/visualize_annotations.py
    # 指定抽样数量
    python tools/visualize_annotations.py --count 10
    # 导出到指定目录
    python tools/visualize_annotations.py --output datasets/rsod/vis_output --count 10
    # 查看指定图片
    python tools/visualize_annotations.py --image train/aircraft_4.jpg
    # 生成网格概览图
    python tools/visualize_annotations.py --grid --output datasets/rsod/vis_output/overview.jpg
"""

import argparse
import os
import random
import sys
from pathlib import Path

import cv2
import numpy as np

# ========== 默认路径配置 ==========
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATASET_DIR = os.path.join(PROJECT_ROOT, "datasets", "rsod")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "datasets", "rsod", "vis_output")

# ========== 颜色调色板（BGR格式，最多支持20种类别） ==========
COLORS = [
    (0, 255, 0),  # 绿色
    (255, 0, 0),  # 蓝色
    (0, 0, 255),  # 红色
    (255, 255, 0),  # 青色
    (0, 255, 255),  # 黄色
    (255, 0, 255),  # 品红
    (128, 255, 0),  # 草绿
    (255, 128, 0),  # 天蓝
    (0, 128, 255),  # 橙色
    (128, 0, 255),  # 紫罗兰
    (255, 255, 128),  # 浅蓝
    (128, 255, 255),  # 浅黄
    (255, 128, 255),  # 浅粉
    (0, 128, 128),  # 暗黄
    (128, 0, 128),  # 暗紫
    (128, 128, 0),  # 暗青
    (64, 255, 64),  # 亮绿
    (255, 64, 64),  # 亮蓝
    (64, 64, 255),  # 亮红
    (255, 200, 0),  # 深蓝
]


def load_class_names(dataset_dir: str) -> dict:
    """
    从 data.yaml 加载类别名称（纯文本解析，不依赖 yaml 库）
    """
    yaml_path = os.path.join(dataset_dir, "data.yaml")
    if not os.path.exists(yaml_path):
        return {}

    names = {}
    try:
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
    except Exception:
        pass
    return names


def draw_yolo_annotations(
    image: np.ndarray,
    label_file: str,
    class_names: dict,
    thickness: int = 2,
    font_scale: float = 0.6,
) -> np.ndarray:
    """
    在图像上绘制 YOLO 格式标注框
    """
    img_h, img_w = image.shape[:2]

    if not os.path.exists(label_file):
        return image

    with open(label_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) != 5:
            continue

        try:
            class_id = int(parts[0])
            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])
        except ValueError:
            continue

        # 归一化坐标 -> 像素坐标
        x1 = int((x_center - width / 2) * img_w)
        y1 = int((y_center - height / 2) * img_h)
        x2 = int((x_center + width / 2) * img_w)
        y2 = int((y_center + height / 2) * img_h)

        # 限制在图像范围内
        x1 = max(0, min(x1, img_w - 1))
        y1 = max(0, min(y1, img_h - 1))
        x2 = max(0, min(x2, img_w - 1))
        y2 = max(0, min(y2, img_h - 1))

        # 获取类别颜色和名称
        color = COLORS[class_id % len(COLORS)]
        class_name = class_names.get(class_id, f"class_{class_id}")

        # 绘制边界框
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

        # 绘制标签背景
        (text_w, text_h), baseline = cv2.getTextSize(
            class_name, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
        )
        label_y = max(y1, text_h + 10)
        cv2.rectangle(
            image,
            (x1, label_y - text_h - 10),
            (x1 + text_w, label_y),
            color,
            -1,  # 填充
        )

        # 绘制标签文字（白色）
        cv2.putText(
            image,
            class_name,
            (x1, label_y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    return image


def collect_image_label_pairs(dataset_dir: str, splits: list | None = None) -> list:
    """
    收集所有图像-标注配对文件
    """
    if splits is None:
        splits = ["train", "val", "test"]

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    pairs = []

    for split in splits:
        img_dir = os.path.join(dataset_dir, "images", split)
        lbl_dir = os.path.join(dataset_dir, "labels", split)

        if not os.path.exists(img_dir):
            continue

        for fname in sorted(os.listdir(img_dir)):
            stem = Path(fname).stem
            ext = Path(fname).suffix.lower()
            if ext not in image_exts:
                continue
            img_path = os.path.join(img_dir, fname)
            lbl_path = os.path.join(lbl_dir, f"{stem}.txt")
            pairs.append((img_path, lbl_path, split, fname))

    return pairs


def visualize_random_samples(
    dataset_dir: str,
    output_dir: str | None = None,
    count: int = 5,
    splits: list | None = None,
    class_names: dict | None = None,
):
    """随机抽样并可视化标注"""
    if class_names is None:
        class_names = load_class_names(dataset_dir)

    pairs = collect_image_label_pairs(dataset_dir, splits)
    if not pairs:
        print("[错误] 未找到任何图像-标注配对文件")
        return

    samples = random.sample(pairs, min(count, len(pairs)))
    print(f"\n共找到 {len(pairs)} 张图像，随机抽样 {len(samples)} 张进行可视化\n")

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    for img_path, lbl_path, split, fname in samples:
        image = cv2.imread(img_path)
        if image is None:
            print(f" [跳过] 无法读取图像: {img_path}")
            continue

        annotated = draw_yolo_annotations(image, lbl_path, class_names)

        # 在图像顶部添加 split 信息
        cv2.putText(
            annotated,
            f"split: {split} | file: {fname}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

        if output_dir:
            out_path = os.path.join(output_dir, f"vis_{split}_{fname}")
            cv2.imwrite(out_path, annotated)
            print(f" [保存] {out_path}")
        else:
            window_name = f"{split} {fname}"
            cv2.imshow(window_name, annotated)
            print(f" [显示] {fname} - 按任意键继续, 按 q 退出")
            key = cv2.waitKey(0) & 0xFF
            cv2.destroyAllWindows()
            if key == ord("q"):
                print(" 用户退出")
                break

    if output_dir:
        print(f"\n可视化完成, 结果保存到: {output_dir}")


def visualize_single_image(
    dataset_dir: str,
    image_relpath: str,
    output_path: str | None = None,
    class_names: dict | None = None,
):
    """可视化单张指定图像的标注"""
    if class_names is None:
        class_names = load_class_names(dataset_dir)

    parts = image_relpath.replace("\\", "/").split("/")
    if len(parts) == 2:
        split = parts[0]
        fname = parts[-1]
    else:
        print("[错误] 请指定包含split名称的路径，如 train/000001.jpg")
        return

    img_path = os.path.join(dataset_dir, "images", split, fname)
    stem = Path(fname).stem
    lbl_path = os.path.join(dataset_dir, "labels", split, f"{stem}.txt")

    if not os.path.exists(img_path):
        print(f"[错误] 图像不存在：{img_path}")
        return

    image = cv2.imread(img_path)
    if image is None:
        print(f"[错误] 无法读取图像：{img_path}")
        return

    annotated = draw_yolo_annotations(image, lbl_path, class_names)

    if output_path:
        cv2.imwrite(output_path, annotated)
        print(f"[已保存到：{output_path}")
    else:
        cv2.imshow(f"[{split}] {fname}", annotated)
        print(f"[显示] {fname} - 按任意键关闭")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def generate_overview_grid(
    dataset_dir: str,
    output_path: str,
    grid_size: tuple = (4, 4),
    splits: list | None = None,
    class_names: dict | None = None,
):
    """生成标注概览网格图"""
    if class_names is None:
        class_names = load_class_names(dataset_dir)

    pairs = collect_image_label_pairs(dataset_dir, splits)
    if not pairs:
        print("[错误] 未找到任何图像-标注配对文件")
        return

    rows, cols = grid_size
    total_cells = rows * cols
    samples = random.sample(pairs, min(total_cells, len(pairs)))

    thumb_w, thumb_h = 400, 300
    grid_img = np.zeros((rows * thumb_h, cols * thumb_w, 3), dtype=np.uint8)

    for idx, (img_path, lbl_path, split, fname) in enumerate(samples):
        row = idx // cols
        col = idx % cols

        image = cv2.imread(img_path)
        if image is None:
            continue

        annotated = draw_yolo_annotations(
            image, lbl_path, class_names, thickness=1, font_scale=0.4
        )
        thumb = cv2.resize(annotated, (thumb_w, thumb_h))

        cv2.putText(
            thumb,
            f"{split}/{fname[:15]}",
            (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

        y_start = row * thumb_h
        x_start = col * thumb_w
        grid_img[y_start : y_start + thumb_h, x_start : x_start + thumb_w] = thumb

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cv2.imwrite(output_path, grid_img)
    print(f"概览网格图已保存到: {output_path}")
    print(f"网格大小: {rows} x {cols} = {len(samples)} 张图像")


def main():
    """主函数: 解析命令行参数并执行可视化"""
    parser = argparse.ArgumentParser(
        description="YOLO 数据集标注可视化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  随机抽样 5 张弹窗查看
    python tools/visualize_annotations.py
  随机抽样 10 张保存到文件
    python tools/visualize_annotations.py --output datasets/rsod/vis_output --count 10
  查看指定图片
    python tools/visualize_annotations.py --image train/000001.jpg
  生成 4x4 概览网格图
    python tools/visualize_annotations.py --grid --output datasets/rsod/vis_output/overview.jpg
        """,
    )

    parser.add_argument(
        "--dataset",
        "-d",
        type=str,
        default=DEFAULT_DATASET_DIR,
        help=f"数据集目录(默认: {DEFAULT_DATASET_DIR})",
    )
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=5,
        help="随机抽样数量(默认: 5)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="输出目录(不指定则弹窗显示)",
    )
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        default=None,
        help="查看指定图像的相对路径（如 train/000001.jpg）",
    )
    parser.add_argument(
        "--grid",
        action="store_true",
        help="生成概览网格图（4x4）",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "val"],
        help="要可视化的 split（默认：train val）",
    )

    args = parser.parse_args()

    if not os.path.exists(args.dataset):
        print(f"[错误] 数据集目录不存在: {args.dataset}")
        sys.exit(1)

    class_names = load_class_names(args.dataset)
    if class_names:
        print(f"加载类别: {class_names}")
    else:
        print("[警告] 未找到 data.yaml, 将使用 class_id 作为类别名")

    if args.grid:
        output_path = args.output or os.path.join(DEFAULT_OUTPUT_DIR, "overview.jpg")
        generate_overview_grid(
            args.dataset,
            output_path,
            grid_size=(4, 4),
            splits=args.splits,
            class_names=class_names,
        )
    elif args.image:
        visualize_single_image(
            args.dataset,
            args.image,
            output_path=args.output,
            class_names=class_names,
        )
    else:
        visualize_random_samples(
            args.dataset,
            output_dir=args.output,
            count=args.count,
            splits=args.splits,
            class_names=class_names,
        )


if __name__ == "__main__":
    main()

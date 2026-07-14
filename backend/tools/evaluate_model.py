"""
模型评估工具 — 对训练完成的模型进行全面评估

功能：
    1. 在验证集或测试集上运行 model.val()
    2. 输出 mAP、Precision、Recall 等核心指标
    3. 输出每类 AP 分析（找出弱势类别）
    4. 生成混淆矩阵、PR 曲线、F1 曲线
    5. 将评估报告保存为 JSON 文件

使用方式：
    cd rsod-agent-platform/backend

    # 评估训练好的 best.pt（默认验证集）
    python tools/evaluate_model.py --weights runs/train/task_xxxxxxxx/weights/best.pt

    # 指定数据集和测试集
    python tools/evaluate_model.py \
        --weights runs/train/task_xxxxxxxx/weights/best.pt \
        --data datasets/weed_detection/data.yaml \
        --split test

    # 调整置信度阈值和 IoU 阈值
    python tools/evaluate_model.py \
        --weights runs/train/task_xxxxxxxx/weights/best.pt \
        --conf 0.25 --iou 0.45

    # 保存评估报告到指定目录
    python tools/evaluate_model.py \
        --weights runs/train/task_xxxxxxxx/weights/best.pt \
        --output models/eval_report
"""

import argparse
import json
import os
import sys

# ── 项目路径 ──────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_data_yaml(weights_path: str) -> str:
    """
    根据权重路径自动查找 data.yaml
    """
    # 从权重路径向上查找
    task_dir = os.path.dirname(os.path.dirname(weights_path))

    # 尝试读取 args.yaml
    args_yaml = os.path.join(task_dir, "args.yaml")
    if os.path.exists(args_yaml):
        with open(args_yaml, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("data:"):
                    data_path = line.split(":", 1)[1].strip()
                    if os.path.exists(data_path):
                        return data_path

    # 在 datasets/ 目录下查找
    datasets_dir = os.path.join(PROJECT_ROOT, "datasets")
    if os.path.exists(datasets_dir):
        for scene_dir in os.listdir(datasets_dir):
            yaml_path = os.path.join(datasets_dir, scene_dir, "data.yaml")
            if os.path.exists(yaml_path):
                return yaml_path
            yaml_path2 = os.path.join(
                datasets_dir, scene_dir, "yolo_dataset", "data.yaml"
            )
            if os.path.exists(yaml_path2):
                return yaml_path2

    return ""


def run_evaluation(
    weights_path: str,
    data_yaml: str,
    split: str = "val",
    conf: float = 0.001,
    iou: float = 0.6,
    img_size: int = 640,
    device: str = "cpu",
    save_output: bool = True,
    output_dir: str | None = None,
) -> dict:
    """运行模型评估"""
    from ultralytics import YOLO

    print(f"\n{'=' * 60}")
    print("  模型评估")
    print(f"  权重文件: {weights_path}")
    print(f"  数据集:   {data_yaml}")
    print(f"  评估集:   {split}")
    print(f"  置信度:   {conf}")
    print(f"  IoU:      {iou}")
    print(f"  设备:     {device}")
    print(f"{'=' * 60}\n")

    model = YOLO(weights_path)

    if output_dir is None:
        output_dir = os.path.dirname(os.path.dirname(weights_path))

    results = model.val(
        data=data_yaml,
        split=split,
        conf=conf,
        iou=iou,
        imgsz=img_size,
        device=device,
        save_json=True,
        save_txt=True,
        save_conf=True,
        plots=save_output,
        project=output_dir,
        name="eval",
        exist_ok=True,
        verbose=True,
    )

    report = parse_evaluation_results(results, model.names)

    print_report(report)

    if save_output:
        report_path = os.path.join(output_dir, "eval", "eval_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n评估报告已保存到: {report_path}")

    return report


def parse_evaluation_results(results, class_names: dict) -> dict:
    """解析 Ultralytics val() 返回结果"""
    report = {
        "overall": {
            "precision": float(results.box.mp),
            "recall": float(results.box.mr),
            "map50": float(results.box.map50),
            "map50_95": float(results.box.map),
            "map75": float(results.box.map75)
            if hasattr(results.box, "map75")
            else None,
        },
        "per_class": {},
    }

    # 检查是否有每类 AP 数据（results.box.ap 是 NumPy 数组）
    if (
        hasattr(results.box, "ap")
        and results.box.ap is not None
        and len(results.box.ap) > 0
    ):
        for i, ap50 in enumerate(results.box.ap50):
            class_name = class_names.get(i, f"class_{i}")
            ap50_95 = results.box.ap[i] if i < len(results.box.ap) else 0.0

            instances = None
            if (
                hasattr(results.box, "np")
                and results.box.np is not None
                and i < len(results.box.np)
            ):
                instances = int(results.box.np[i])

            report["per_class"][class_name] = {
                "ap50": float(ap50),
                "ap50_95": float(ap50_95),
                "instances": instances,
            }

    return report


def print_report(report: dict):
    """打印格式化的评估报告"""
    overall = report["overall"]

    print(f"\n{'=' * 60}")
    print("  📊 评估报告")
    print(f"{'=' * 60}")
    print("\n  ▸ 整体指标:")
    print(f"    {'指标':<16} {'值':>10}")
    print(f"    {'─' * 26}")
    print(f"    {'Precision':<16} {overall['precision']:>10.4f}")
    print(f"    {'Recall':<16} {overall['recall']:>10.4f}")
    print(f"    {'mAP@50':<16} {overall['map50']:>10.4f}")
    print(f"    {'mAP@50-95':<16} {overall['map50_95']:>10.4f}")

    per_class = report["per_class"]
    if per_class:
        print("\n  ▸ 每类 AP（按 mAP50 降序）:")
        print(f"    {'类别':<20} {'AP@50':>8} {'AP@50-95':>10}")
        print(f"    {'─' * 38}")

        sorted_classes = sorted(
            per_class.items(),
            key=lambda x: x[1]["ap50"],
            reverse=True,
        )

        for class_name, metrics in sorted_classes:
            print(
                f"    {class_name:<20} {metrics['ap50']:>8.4f} {metrics['ap50_95']:>10.4f}"
            )

        weak_classes = [name for name, m in sorted_classes if m["ap50"] < 0.5]
        if weak_classes:
            print(f"\n  ⚠ 弱势类别（AP@50 < 0.5）: {', '.join(weak_classes)}")
            print("    建议: 增加这些类别的训练样本，或检查标注质量")

    print(f"\n{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="YOLOv11 模型评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 评估 best.pt（自动查找 data.yaml）
  python tools/evaluate_model.py --weights runs/train/weed_test/weights/best.pt

  # 在测试集上评估
  python tools/evaluate_model.py --weights path/to/best.pt --split test

  # 自定义阈值
  python tools/evaluate_model.py --weights path/to/best.pt --conf 0.25 --iou 0.45

  # 保存评估报告
  python tools/evaluate_model.py --weights path/to/best.pt --output models/eval_report
        """,
    )

    parser.add_argument(
        "--weights",
        "-w",
        type=str,
        required=True,
        help="模型权重路径（best.pt）",
    )
    parser.add_argument(
        "--data",
        "-d",
        type=str,
        default=None,
        help="data.yaml 路径（默认自动查找）",
    )
    parser.add_argument(
        "--split",
        "-s",
        type=str,
        default="val",
        choices=["train", "val", "test"],
        help="评估数据集划分（默认: val）",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.001,
        help="置信度阈值（默认: 0.001）",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.6,
        help="NMS IoU 阈值（默认: 0.6）",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="图像尺寸（默认: 640）",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="评估设备（cpu / 0）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="评估报告输出目录",
    )

    args = parser.parse_args()

    if not os.path.exists(args.weights):
        print(f"[错误] 权重文件不存在: {args.weights}")
        sys.exit(1)

    data_yaml = args.data
    if not data_yaml:
        data_yaml = find_data_yaml(args.weights)
    if not data_yaml or not os.path.exists(data_yaml):
        print("[错误] 未找到 data.yaml，请使用 --data 参数指定")
        sys.exit(1)

    run_evaluation(
        weights_path=args.weights,
        data_yaml=data_yaml,
        split=args.split,
        conf=args.conf,
        iou=args.iou,
        img_size=args.imgsz,
        device=args.device,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()

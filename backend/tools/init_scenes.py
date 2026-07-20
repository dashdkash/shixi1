"""
初始化检测场景数据

运行方式：
  cd backend
  python tools/init_scenes.py

会在 detection_scenes 表中创建默认场景（若已存在则跳过）。
"""

import sys
import os

# 确保能导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal
from app.entity.db_models import DetectionScene

# ── 预置场景列表 ──────────────────────────────────────

SCENES = [
    {
        "name": "weeds",
        "display_name": "农田杂草检测",
        "description": "基于 Roboflow 杂草数据集，包含 15 类常见农田杂草",
        "category": "agriculture",
        "class_names": [
            "carpetweeds", "crabgrass", "eclipta", "goosegrass",
            "morningglory", "nutsedge", "palmeramaranth", "pricklysida",
            "purslane", "ragweed", "sicklepod", "spottedspurge",
            "spurredanoda", "swinecress", "waterhemp",
        ],
        "class_names_cn": {
            "carpetweeds": "地毯草",
            "crabgrass": "马唐",
            "eclipta": "鳢肠",
            "goosegrass": "牛筋草",
            "morningglory": "牵牛花",
            "nutsedge": "莎草",
            "palmeramaranth": "帕尔默苋",
            "pricklysida": "刺黄花稔",
            "purslane": "马齿苋",
            "ragweed": "豚草",
            "sicklepod": "镰刀豆",
            "spottedspurge": "斑点大戟",
            "spurredanoda": "距花苋",
            "swinecress": "猪草",
            "waterhemp": "水苋",
        },
    },
    {
        "name": "remote_sensing",
        "display_name": "遥感目标检测",
        "description": "卫星/无人机遥感图像中的目标检测",
        "category": "remote_sensing",
        "class_names": [
            "airplane", "bridge", "storage-tank", "swimming-pool",
            "roundabout", "ship", "vehicle", "harbor",
        ],
        "class_names_cn": {
            "airplane": "飞机",
            "bridge": "桥梁",
            "storage-tank": "储罐",
            "swimming-pool": "游泳池",
            "roundabout": "环岛",
            "ship": "船舶",
            "vehicle": "车辆",
            "harbor": "港口",
        },
    },
    {
        "name": "traffic",
        "display_name": "交通目标检测",
        "description": "道路交通场景中的车辆、行人、交通标志检测",
        "category": "traffic",
        "class_names": ["car", "truck", "bus", "motorcycle", "bicycle", "pedestrian", "traffic_light", "stop_sign"],
        "class_names_cn": {
            "car": "轿车",
            "truck": "卡车",
            "bus": "公交车",
            "motorcycle": "摩托车",
            "bicycle": "自行车",
            "pedestrian": "行人",
            "traffic_light": "红绿灯",
            "stop_sign": "停车标志",
        },
    },
    {
        "name": "general",
        "display_name": "通用目标检测",
        "description": "COCO 格式通用目标检测场景",
        "category": "industry",
        "class_names": [
            "person", "bicycle", "car", "motorcycle", "airplane",
            "bus", "train", "truck", "boat", "traffic light",
            "fire hydrant", "stop sign", "parking meter", "bench",
            "bird", "cat", "dog", "horse", "sheep", "cow",
        ],
        "class_names_cn": {
            "person": "人", "bicycle": "自行车", "car": "轿车",
            "motorcycle": "摩托车", "airplane": "飞机", "bus": "公交车",
            "train": "火车", "truck": "卡车", "boat": "船",
            "traffic light": "红绿灯", "fire hydrant": "消防栓",
            "stop sign": "停车标志", "parking meter": "停车计时器",
            "bench": "长椅", "bird": "鸟", "cat": "猫",
            "dog": "狗", "horse": "马", "sheep": "羊", "cow": "牛",
        },
    },
]


def main():
    db = SessionLocal()
    try:
        created = 0
        for scene_data in SCENES:
            exists = (
                db.query(DetectionScene)
                .filter(DetectionScene.name == scene_data["name"])
                .first()
            )
            if exists:
                print(f"  跳过（已存在）: {scene_data['name']}")
                continue

            scene = DetectionScene(**scene_data, is_active=True)
            db.add(scene)
            created += 1
            print(f"  创建: {scene_data['name']} - {scene_data['display_name']}")

        db.commit()
        print(f"\n完成！新增 {created} 个场景，共 {len(SCENES)} 个场景。")
    except Exception as e:
        db.rollback()
        print(f"初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

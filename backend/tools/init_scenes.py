"""
初始化检测场景脚本

基于防治手册.md中的15种杂草创建检测场景配置，包括类别中文名映射

python ./tools/init_scenes.py
"""

import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

try:
    from app.database.session import get_db, Base, engine
    from app.entity.db_models import DetectionScene, DetectionTask, DetectionResult, TrainingTask, ModelVersion
    
    print("=" * 50)
    print("杂草识别智能体 - 初始化检测场景")
    print("=" * 50)
    
    Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    
    try:
        scene_count = db.query(DetectionScene).count()
        task_count = db.query(DetectionTask).count()
        training_count = db.query(TrainingTask).count()
        model_count = db.query(ModelVersion).count()

        if scene_count > 0 or task_count > 0 or training_count > 0 or model_count > 0:
            print(f"\n⚠️  检测到数据库中已有数据:")
            print(f"   - 检测场景: {scene_count} 条")
            print(f"   - 检测任务: {task_count} 条")
            print(f"   - 训练任务: {training_count} 条")
            print(f"   - 模型版本: {model_count} 条")
            print(f"\n⚠️  删除后将无法恢复！")
            
            confirm = input("\n是否删除原有数据并重新初始化？(y/N): ").strip().lower()
            if confirm != 'y':
                print("\n✓ 已取消操作，退出脚本")
                sys.exit(0)

            print("\n✓ 正在删除原有数据...")
            db.query(DetectionResult).delete()
            db.query(ModelVersion).delete()
            db.query(DetectionTask).delete()
            db.query(TrainingTask).delete()
            db.query(DetectionScene).delete()
            db.commit()
            print("✓ 已清空所有相关数据")

        default_scenes = [
            {
                "name": "weeds",
                "display_name": "农田杂草识别",
                "description": "基于防治手册的15种常见农田杂草检测与识别场景",
                "category": "agriculture",
                "class_names": [
                    "carpetweeds",
                    "crabgrass",
                    "eclipta",
                    "goosegrass",
                    "morningglory",
                    "nutsedge",
                    "palmeramaranth",
                    "pricklysida",
                    "purslane",
                    "ragweed",
                    "sicklepod",
                    "spottedspurge",
                    "spurredanoda",
                    "swinecress",
                    "waterhemp",
                    "crop",
                ],
                "class_names_cn": {
                    "carpetweeds": "粟米草",
                    "crabgrass": "马唐",
                    "eclipta": "鳢肠",
                    "goosegrass": "牛筋草",
                    "morningglory": "牵牛花",
                    "nutsedge": "香附子",
                    "palmeramaranth": "长芒苋",
                    "pricklysida": "刺黄花稔",
                    "purslane": "马齿苋",
                    "ragweed": "豚草",
                    "sicklepod": "决明",
                    "spottedspurge": "斑地锦",
                    "spurredanoda": "刺黄菊",
                    "swinecress": "臭荠",
                    "waterhemp": "水蓼",
                    "crop": "作物",
                },
            },
            {
                "name": "remote_sensing",
                "display_name": "遥感目标检测",
                "description": "遥感图像目标检测场景，支持飞机、车辆、建筑等目标",
                "category": "remote_sensing",
                "class_names": ["airplane", "car", "building", "road", "water"],
                "class_names_cn": {
                    "airplane": "飞机",
                    "car": "车辆",
                    "building": "建筑",
                    "road": "道路",
                    "water": "水域",
                },
            },
            {
                "name": "traffic",
                "display_name": "交通目标检测",
                "description": "交通场景目标检测，支持车辆、行人、红绿灯等",
                "category": "traffic",
                "class_names": ["car", "person", "bike", "traffic_light", "bus"],
                "class_names_cn": {
                    "car": "车辆",
                    "person": "行人",
                    "bike": "自行车",
                    "traffic_light": "红绿灯",
                    "bus": "公交车",
                },
            },
            {
                "name": "general",
                "display_name": "通用目标检测",
                "description": "COCO 数据集通用目标检测，支持80种常见物体",
                "category": "industry",
                "class_names": [
                    "person", "bicycle", "car", "motorcycle", "airplane",
                    "bus", "train", "truck", "boat", "traffic_light",
                    "fire_hydrant", "stop_sign", "parking_meter", "bench",
                    "bird", "cat", "dog", "horse", "sheep", "cow",
                    "elephant", "bear", "zebra", "giraffe", "backpack",
                    "umbrella", "handbag", "tie", "suitcase", "frisbee",
                    "skis", "snowboard", "sports_ball", "kite", "baseball_bat",
                    "baseball_glove", "skateboard", "surfboard", "tennis_racket",
                    "bottle", "wine_glass", "cup", "fork", "knife", "spoon",
                    "bowl", "banana", "apple", "sandwich", "orange",
                    "broccoli", "carrot", "hot_dog", "pizza", "donut", "cake",
                    "chair", "couch", "potted_plant", "bed", "dining_table",
                    "toilet", "tv", "laptop", "mouse", "remote", "keyboard",
                    "cell_phone", "microwave", "oven", "toaster", "sink",
                    "refrigerator", "book", "clock", "vase", "scissors",
                    "teddy_bear", "hair_drier", "toothbrush",
                ],
                "class_names_cn": {
                    "person": "人", "bicycle": "自行车", "car": "汽车",
                    "motorcycle": "摩托车", "airplane": "飞机", "bus": "公交车",
                    "train": "火车", "truck": "卡车", "boat": "船",
                    "traffic_light": "红绿灯", "fire_hydrant": "消防栓",
                    "stop_sign": "停止标志", "parking_meter": "停车计时器",
                    "bench": "长椅", "bird": "鸟", "cat": "猫", "dog": "狗",
                    "horse": "马", "sheep": "羊", "cow": "牛", "elephant": "大象",
                    "bear": "熊", "zebra": "斑马", "giraffe": "长颈鹿",
                    "backpack": "背包", "umbrella": "雨伞", "handbag": "手提包",
                    "tie": "领带", "suitcase": "行李箱", "frisbee": "飞盘",
                    "skis": "滑雪板", "snowboard": "滑雪板", "sports_ball": "运动球",
                    "kite": "风筝", "baseball_bat": "棒球棒", "baseball_glove": "棒球手套",
                    "skateboard": "滑板", "surfboard": "冲浪板", "tennis_racket": "网球拍",
                    "bottle": "瓶子", "wine_glass": "酒杯", "cup": "杯子",
                    "fork": "叉子", "knife": "刀", "spoon": "勺子", "bowl": "碗",
                    "banana": "香蕉", "apple": "苹果", "sandwich": "三明治",
                    "orange": "橙子", "broccoli": "西兰花", "carrot": "胡萝卜",
                    "hot_dog": "热狗", "pizza": "披萨", "donut": "甜甜圈",
                    "cake": "蛋糕", "chair": "椅子", "couch": "沙发",
                    "potted_plant": "盆栽植物", "bed": "床", "dining_table": "餐桌",
                    "toilet": "厕所", "tv": "电视", "laptop": "笔记本电脑",
                    "mouse": "鼠标", "remote": "遥控器", "keyboard": "键盘",
                    "cell_phone": "手机", "microwave": "微波炉", "oven": "烤箱",
                    "toaster": "烤面包机", "sink": "水槽", "refrigerator": "冰箱",
                    "book": "书", "clock": "时钟", "vase": "花瓶", "scissors": "剪刀",
                    "teddy_bear": "泰迪熊", "hair_drier": "吹风机",
                    "toothbrush": "牙刷",
                },
            },
        ]
        
        for scene_data in default_scenes:
            existing = db.query(DetectionScene).filter(
                DetectionScene.name == scene_data["name"]
            ).first()
            
            if existing:
                if existing.class_names_cn is None:
                    existing.class_names_cn = scene_data["class_names_cn"]
                    existing.class_names = scene_data["class_names"]
                    db.commit()
                    print(f"✓ 更新 {scene_data['name']} 场景的类别中文名")
                else:
                    print(f"✓ {scene_data['name']} 场景已存在")
            else:
                scene = DetectionScene(
                    name=scene_data["name"],
                    display_name=scene_data["display_name"],
                    description=scene_data["description"],
                    category=scene_data["category"],
                    class_names=scene_data["class_names"],
                    class_names_cn=scene_data["class_names_cn"],
                    is_active=True,
                )
                db.add(scene)
                db.commit()
                print(f"✓ 创建 {scene_data['display_name']} 场景")
        
        print("\n✓ 检测场景初始化完成")
        
    except Exception as e:
        db.rollback()
        print(f"✗ 初始化失败: {e}")
        raise
    finally:
        db.close()
        
    print("=" * 50)
    
except Exception as e:
    print(f"初始化失败: {e}")

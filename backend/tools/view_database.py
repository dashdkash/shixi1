"""
通用数据库查看脚本

支持查看项目中所有数据表的数据
"""

import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

os.chdir(backend_dir)

from app.database.session import get_db, engine
from app.entity.db_models import (
    User, Role, Permission, UserRole, RolePermission,
    DetectionScene, DetectionTask, DetectionResult,
    TrainingTask, TrainingMetric, ModelVersion,
    ChatSession, ChatMessage, OperationLog,
    KnowledgeDocument, KnowledgeChunk,
)


TABLE_MODELS = {
    "users": User,
    "roles": Role,
    "permissions": Permission,
    "user_roles": UserRole,
    "role_permissions": RolePermission,
    "detection_scenes": DetectionScene,
    "detection_tasks": DetectionTask,
    "detection_results": DetectionResult,
    "training_tasks": TrainingTask,
    "training_metrics": TrainingMetric,
    "model_versions": ModelVersion,
    "chat_sessions": ChatSession,
    "chat_messages": ChatMessage,
    "operation_logs": OperationLog,
    "knowledge_documents": KnowledgeDocument,
    "knowledge_chunks": KnowledgeChunk,
}


def print_table_summary(table_name, model):
    """打印单个表的摘要信息"""
    db = next(get_db())
    try:
        total = db.query(model).count()
        print(f"├── {table_name}: {total} 条记录")
        
        if total > 0 and total <= 5:
            records = db.query(model).all()
            for i, record in enumerate(records, 1):
                print(f"│   └── #{i}: {format_record(record)}")
        elif total > 5:
            records = db.query(model).limit(3).all()
            for i, record in enumerate(records, 1):
                print(f"│   ├── #{i}: {format_record(record)}")
            print(f"│   └── ... 还有 {total - 3} 条记录")
    finally:
        db.close()


def format_record(record):
    """格式化记录输出"""
    result = []
    for col in record.__table__.columns:
        value = getattr(record, col.name)
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        elif isinstance(value, str) and len(value) > 50:
            value_str = value[:50] + "..."
        else:
            value_str = str(value)
        result.append(f"{col.name}={value_str}")
    return ", ".join(result)


def print_detection_scenes_detail():
    """打印检测场景详细信息"""
    print("\n" + "=" * 70)
    print("检测场景详情")
    print("=" * 70)
    
    db = next(get_db())
    try:
        scenes = db.query(DetectionScene).all()
        
        if not scenes:
            print("暂无检测场景数据")
            return
            
        for i, scene in enumerate(scenes, 1):
            print(f"\n┌──────────────────────────────────────────────────────────────┐")
            print(f"│ 场景 #{i}")
            print(f"├──────────────────────────────────────────────────────────────┤")
            print(f"│ ID:           {scene.id}")
            print(f"│ 名称:         {scene.name}")
            print(f"│ 显示名:       {scene.display_name}")
            print(f"│ 分类:         {scene.category}")
            print(f"│ 描述:         {scene.description or '无'}")
            print(f"│ 启用状态:     {'启用' if scene.is_active else '禁用'}")
            print(f"│ 创建时间:     {scene.created_at.strftime('%Y-%m-%d %H:%M:%S') if scene.created_at else '无'}")
            print(f"├──────────────────────────────────────────────────────────────┤")
            print(f"│ 类别列表 ({len(scene.class_names)} 个):")
            if scene.class_names_cn:
                for cn in scene.class_names:
                    cn_cn = scene.class_names_cn.get(cn, cn)
                    print(f"│   - {cn} ({cn_cn})")
            else:
                for cn in scene.class_names:
                    print(f"│   - {cn}")
            print(f"└──────────────────────────────────────────────────────────────┘")
            
    finally:
        db.close()


def print_detection_tasks_detail():
    """打印检测任务详情"""
    print("\n" + "=" * 70)
    print("检测任务详情")
    print("=" * 70)
    
    db = next(get_db())
    try:
        tasks = db.query(DetectionTask).order_by(DetectionTask.created_at.desc()).limit(10).all()
        
        if not tasks:
            print("暂无检测任务数据")
            return
            
        for i, task in enumerate(tasks, 1):
            scene_name = ""
            if task.scene:
                scene_name = task.scene.display_name
            
            print(f"\n┌──────────────────────────────────────────────────────────────┐")
            print(f"│ 任务 #{i}")
            print(f"├──────────────────────────────────────────────────────────────┤")
            print(f"│ ID:           {task.id}")
            print(f"│ 用户ID:       {task.user_id}")
            print(f"│ 场景:         {scene_name} (ID:{task.scene_id})")
            print(f"│ 类型:         {task.task_type}")
            print(f"│ 状态:         {task.status}")
            print(f"│ 图片数:       {task.total_images}")
            print(f"│ 目标数:       {task.total_objects}")
            print(f"│ 推理耗时:     {task.total_inference_time:.2f}ms" if task.total_inference_time else "│ 推理耗时:     无")
            print(f"│ 创建时间:     {task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '无'}")
            print(f"└──────────────────────────────────────────────────────────────┘")
            
    finally:
        db.close()


def print_detection_results_detail():
    """打印检测结果详情"""
    print("\n" + "=" * 70)
    print("检测结果详情（最近20条）")
    print("=" * 70)
    
    db = next(get_db())
    try:
        results = db.query(DetectionResult).order_by(DetectionResult.created_at.desc()).limit(20).all()
        
        if not results:
            print("暂无检测结果数据")
            return
            
        for i, result in enumerate(results, 1):
            print(f"\n┌──────────────────────────────────────────────────────────────┐")
            print(f"│ 结果 #{i}")
            print(f"├──────────────────────────────────────────────────────────────┤")
            print(f"│ ID:           {result.id}")
            print(f"│ 任务ID:       {result.task_id}")
            print(f"│ 图片路径:     {result.image_path}")
            print(f"│ 类别:         {result.class_name_cn or result.class_name}")
            print(f"│ 置信度:       {result.confidence * 100:.1f}%")
            print(f"│ 推理耗时:     {result.inference_time:.2f}ms" if result.inference_time else "│ 推理耗时:     无")
            print(f"└──────────────────────────────────────────────────────────────┘")
            
    finally:
        db.close()


def main():
    print("=" * 70)
    print("杂草识别智能体 - 数据库查看工具")
    print("=" * 70)
    
    print("\n1. 所有表数据概览:")
    print("─" * 70)
    
    for table_name, model in TABLE_MODELS.items():
        print_table_summary(table_name, model)
    
    print_detection_scenes_detail()
    print_detection_tasks_detail()
    print_detection_results_detail()
    
    print("\n" + "=" * 70)
    print("数据库查看完成")
    print("=" * 70)


if __name__ == "__main__":
    main()

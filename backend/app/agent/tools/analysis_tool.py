"""
统计分析工具 — Agent 可调用的数据查询工具

工具列表：
  - query_detection_stats: 查询检测统计数据
  - query_detection_history: 查询检测历史记录
  - query_latest_detection: 查询最近一次检测的详细结果
  - query_detection_geo_summary: 查询检测地理分布摘要
"""

import json

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionResult, DetectionTask
from app.services.detection_service import current_user_id as user_id_ctx

logger = get_logger(__name__)


def _get_current_user_id():
    """从上下文变量获取当前用户 ID"""
    return user_id_ctx.get()


@tool
def query_detection_stats(days: int = 30) -> str:
    """查询用户的检测统计数据。

    当用户询问"今天检测了多少次"、"最近检测了多少目标"、"检测统计"等统计类问题时使用此工具。

    Args:
        days: 统计最近 N 天的数据，默认 30 天

    Returns:
        JSON 字符串，包含总任务数、总目标数、各类型任务数等统计信息
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func

        user_id = _get_current_user_id()
        db = SessionLocal()
        try:
            start_date = datetime.now() - timedelta(days=days)

            query = (
                db.query(
                    func.count(DetectionTask.id).label("total_tasks"),
                    func.coalesce(func.sum(DetectionTask.total_objects), 0).label("total_objects"),
                    func.coalesce(func.sum(DetectionTask.total_images), 0).label("total_images"),
                    func.coalesce(func.avg(DetectionTask.total_inference_time), 0).label("avg_time"),
                )
                .filter(DetectionTask.created_at >= start_date)
            )
            if user_id:
                query = query.filter(DetectionTask.user_id == user_id)
            stats = query.first()

            result = {
                "period": f"最近 {days} 天",
                "total_tasks": stats.total_tasks,
                "total_objects": int(stats.total_objects),
                "total_images": int(stats.total_images),
                "avg_inference_time": round(float(stats.avg_time), 2),
            }

            # 追加类别分布（中文名优先）
            class_stats = (
                db.query(
                    DetectionResult.class_name,
                    DetectionResult.class_name_cn,
                    func.count(DetectionResult.id).label("count"),
                )
                .join(DetectionTask, DetectionResult.task_id == DetectionTask.id)
                .filter(
                    DetectionTask.created_at >= start_date,
                    DetectionResult.class_name != "no_detection",
                )
            )
            if user_id:
                class_stats = class_stats.filter(DetectionTask.user_id == user_id)
            class_stats = (
                class_stats
                .group_by(DetectionResult.class_name, DetectionResult.class_name_cn)
                .order_by(func.count(DetectionResult.id).desc())
                .all()
            )
            result["class_distribution"] = [
                {"name": row.class_name_cn or row.class_name, "count": row.count}
                for row in class_stats
            ]

            # 追加有位置信息的任务列表
            geo_tasks_query = (
                db.query(
                    DetectionTask.id,
                    DetectionTask.location_name,
                    DetectionTask.latitude,
                    DetectionTask.longitude,
                    DetectionTask.total_objects,
                )
                .filter(
                    DetectionTask.created_at >= start_date,
                    DetectionTask.latitude.isnot(None),
                    DetectionTask.longitude.isnot(None),
                )
            )
            if user_id:
                geo_tasks_query = geo_tasks_query.filter(DetectionTask.user_id == user_id)
            geo_tasks = geo_tasks_query.order_by(DetectionTask.created_at.desc()).limit(50).all()
            result["geo_tasks"] = [
                {
                    "task_id": t.id,
                    "location_name": t.location_name,
                    "latitude": t.latitude,
                    "longitude": t.longitude,
                    "total_objects": t.total_objects or 0,
                }
                for t in geo_tasks
            ]

            return json.dumps(result, ensure_ascii=False)
        finally:
            db.close()
    except Exception as e:
        logger.error("查询统计失败: %s", str(e))
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)


@tool
def query_detection_history(limit: int = 10) -> str:
    """查询最近的检测历史记录。

    当用户询问"最近的检测结果"、"上次检测了什么"、"检测历史"等问题时使用此工具。

    Args:
        limit: 返回最近 N 条记录，默认 10 条

    Returns:
        JSON 字符串，包含最近的检测任务列表（类型、状态、目标数、时间）
    """
    try:
        user_id = _get_current_user_id()
        db = SessionLocal()
        try:
            query = db.query(DetectionTask)
            if user_id:
                query = query.filter(DetectionTask.user_id == user_id)
            tasks = (
                query
                .order_by(DetectionTask.created_at.desc())
                .limit(limit)
                .all()
            )

            items = []
            for t in tasks:
                items.append({
                    "id": t.id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "total_objects": t.total_objects or 0,
                    "total_images": t.total_images or 0,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                })

            return json.dumps({"history": items, "count": len(items)}, ensure_ascii=False)
        finally:
            db.close()
    except Exception as e:
        logger.error("查询历史失败: %s", str(e))
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)


@tool
def query_latest_detection() -> str:
    """查询当前用户最近一次检测任务的详细结果。

    当用户询问"刚刚检测了什么""最近一次检测了什么""上次检测的具体结果""最后一次检测的类别和数量"等问题时使用此工具。
    注意：此工具只返回最新一条记录，不要与 query_detection_history 混用。

    Returns:
        JSON 字符串，包含最近一次检测任务的完整详情：
        - task_id, task_type, status, total_objects, total_images
        - class_counts: 各类别目标数量
        - detections: 每个目标的详细信息（类别名、置信度、边界框）
        - created_at, completed_at
    """
    try:
        user_id = _get_current_user_id()
        db = SessionLocal()
        try:
            query = db.query(DetectionTask)
            if user_id:
                query = query.filter(DetectionTask.user_id == user_id)
            task = (
                query
                .order_by(DetectionTask.created_at.desc())
                .first()
            )
            if not task:
                return json.dumps({"error": "没有任何检测记录"}, ensure_ascii=False)

            # 查询该任务的所有检测结果（排除占位记录）
            results = (
                db.query(DetectionResult)
                .filter(
                    DetectionResult.task_id == task.id,
                    ~(
                        (DetectionResult.class_name == "no_detection")
                        & (DetectionResult.class_id == -1)
                    ),
                )
                .all()
            )

            # 类别统计
            class_counts: dict = {}
            detections = []
            for r in results:
                name = r.class_name_cn or r.class_name
                class_counts[name] = class_counts.get(name, 0) + 1
                detections.append({
                    "class_name": r.class_name,
                    "class_name_cn": r.class_name_cn,
                    "confidence": round(r.confidence, 4) if r.confidence else 0,
                    "bbox": r.bbox,
                    "image_path": r.image_path,
                })

            return json.dumps({
                "task_id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "total_objects": task.total_objects or 0,
                "total_images": task.total_images or 0,
                "total_inference_time": round(task.total_inference_time, 2) if task.total_inference_time else None,
                "latitude": task.latitude,
                "longitude": task.longitude,
                "location_name": task.location_name,
                "class_counts": class_counts,
                "detections": detections[:50],  # 最多返回 50 条
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }, ensure_ascii=False)
        finally:
            db.close()
    except Exception as e:
        logger.error("查询最新检测失败: %s", str(e))
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)


# 分析工具列表
ANALYSIS_TOOLS = [
    query_detection_stats,
    query_detection_history,
]


@tool
def query_detection_geo_summary(days: int = 30) -> str:
    """查询检测任务的地理分布摘要。

    当用户询问"哪些地区检测到了杂草"、"不同地块的杂草分布"、"地理分布"、"杂草分布热力图"等问题时使用此工具。
    返回有位置信息的检测任务摘要，包括每个位置的主要杂草类别。

    Args:
        days: 统计最近 N 天的数据，默认 30 天

    Returns:
        JSON 字符串，包含每个有位置信息的检测任务的摘要
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func

        user_id = _get_current_user_id()
        db = SessionLocal()
        try:
            start_date = datetime.now() - timedelta(days=days)

            query = (
                db.query(DetectionTask)
                .filter(
                    DetectionTask.created_at >= start_date,
                    DetectionTask.latitude.isnot(None),
                    DetectionTask.longitude.isnot(None),
                )
            )
            if user_id:
                query = query.filter(DetectionTask.user_id == user_id)
            tasks = query.order_by(DetectionTask.created_at.desc()).limit(100).all()

            if not tasks:
                return json.dumps({
                    "message": "没有找到带地理位置信息的检测记录",
                    "points": [],
                }, ensure_ascii=False)

            points = []
            for t in tasks:
                # 查询该任务的主要杂草类别
                class_stats = (
                    db.query(
                        DetectionResult.class_name_cn,
                        func.count(DetectionResult.id).label("cnt"),
                    )
                    .filter(
                        DetectionResult.task_id == t.id,
                        DetectionResult.class_name != "no_detection",
                    )
                    .group_by(DetectionResult.class_name_cn)
                    .order_by(func.count(DetectionResult.id).desc())
                    .limit(3)
                    .all()
                )
                top_classes = [
                    {"name": row.class_name_cn or "未知", "count": row.cnt}
                    for row in class_stats
                ]
                points.append({
                    "task_id": t.id,
                    "latitude": t.latitude,
                    "longitude": t.longitude,
                    "location_name": t.location_name or f"({t.latitude:.4f}, {t.longitude:.4f})",
                    "total_objects": t.total_objects or 0,
                    "top_classes": top_classes,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                })

            return json.dumps({
                "period": f"最近 {days} 天",
                "total_geo_tasks": len(points),
                "points": points,
            }, ensure_ascii=False)
        finally:
            db.close()
    except Exception as e:
        logger.error("查询地理分布失败: %s", str(e))
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)


ANALYSIS_TOOLS.append(query_detection_geo_summary)

@tool
def query_user_list(limit: int = 20) -> str:
    """查询系统中的用户列表。

    当用户询问"系统有哪些用户"、"有哪些管理员"、"用户列表"等问题时使用此工具。

    Args:
        limit: 返回最多 N 个用户，默认 20 个

    Returns:
        JSON 字符串，包含用户列表（用户名、邮箱、角色、注册时间）
    """
    try:
        from app.entity.db_models import User, UserRole, Role
        from sqlalchemy.orm import joinedload

        db = SessionLocal()
        try:
            users = (
                db.query(User)
                .options(joinedload(User.user_roles).joinedload(UserRole.role))
                .order_by(User.created_at.desc())
                .limit(limit)
                .all()
            )

            items = []
            for u in users:
                roles = [ur.role.name for ur in u.user_roles] if u.user_roles else []
                items.append({
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "roles": roles,
                    "is_active": u.is_active,
                })

            return json.dumps({"users": items, "count": len(items)}, ensure_ascii=False)
        finally:
            db.close()
    except Exception as e:
        logger.error("查询用户列表失败: %s", str(e))
        return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)


# 更新分析工具列表
ANALYSIS_TOOLS.append(query_user_list)
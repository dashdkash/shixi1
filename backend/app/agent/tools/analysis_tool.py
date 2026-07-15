"""
统计分析工具 — Agent 可调用的数据查询工具

工具列表：
  - query_detection_stats: 查询检测统计数据
  - query_detection_history: 查询检测历史记录
"""

import json

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.database.session import SessionLocal
from app.entity.db_models import DetectionTask

logger = get_logger(__name__)


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

        db = SessionLocal()
        try:
            start_date = datetime.now() - timedelta(days=days)

            stats = (
                db.query(
                    func.count(DetectionTask.id).label("total_tasks"),
                    func.coalesce(func.sum(DetectionTask.total_objects), 0).label("total_objects"),
                    func.coalesce(func.sum(DetectionTask.total_images), 0).label("total_images"),
                    func.coalesce(func.avg(DetectionTask.total_inference_time), 0).label("avg_time"),
                )
                .filter(DetectionTask.created_at >= start_date)
                .first()
            )

            result = {
                "period": f"最近 {days} 天",
                "total_tasks": stats.total_tasks,
                "total_objects": int(stats.total_objects),
                "total_images": int(stats.total_images),
                "avg_inference_time": round(float(stats.avg_time), 2),
            }
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
        db = SessionLocal()
        try:
            tasks = (
                db.query(DetectionTask)
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


# 分析工具列表
ANALYSIS_TOOLS = [
    query_detection_stats,
    query_detection_history,
]

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
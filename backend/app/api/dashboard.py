"""
数据看板 API 路由 — 聚合统计查询接口

接口列表：
  - GET /api/dashboard/statistics    汇总统计（任务数/图片数/目标数/平均耗时）
  - GET /api/dashboard/trend         每日检测趋势（近 N 天）
  - GET /api/dashboard/class-dist    类别分布统计
  - GET /api/dashboard/scene-dist    场景分布统计
  - GET /api/dashboard/type-dist     任务类型分布统计
"""

from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user
from app.core.logger import get_logger
from app.services.dashboard_service import dashboard_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["数据看板"])


@router.get("/statistics", summary="汇总统计")
async def get_statistics(
    days: int = Query(30, ge=1, le=365, description="统计最近 N 天"),
    current_user=Depends(get_current_user),
):
    """
    获取检测汇总统计数据

    返回：总任务数、总图片数、总目标数、平均推理耗时
    以及与上一个同等时段的环比增长率
    """
    return dashboard_service.get_statistics(user_id=current_user.id, days=days)


@router.get("/trend", summary="每日检测趋势")
async def get_trend(
    days: int = Query(30, ge=1, le=365, description="统计最近 N 天"),
    current_user=Depends(get_current_user),
):
    """
    获取每日检测趋势数据（用于折线图）

    返回每天的检测任务数和目标数
    """
    return dashboard_service.get_trend(user_id=current_user.id, days=days)


@router.get("/class-dist", summary="类别分布统计")
async def get_class_distribution(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    """
    获取各类别检测次数分布（用于饼图）

    从 detection_results 表按 class_name 聚合
    """
    return dashboard_service.get_class_distribution(user_id=current_user.id, days=days)


@router.get("/scene-dist", summary="场景分布统计")
async def get_scene_distribution(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    """获取各检测场景的任务分布（用于柱状图）"""
    return dashboard_service.get_scene_distribution(user_id=current_user.id, days=days)


@router.get("/type-dist", summary="任务类型分布统计")
async def get_type_distribution(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
):
    """获取各任务类型（single/batch/zip/video/camera）的分布（用于环形图）"""
    return dashboard_service.get_type_distribution(user_id=current_user.id, days=days)

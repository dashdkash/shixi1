"""
检测工具集 — Agent 可调用的检测相关工具

工具列表：
  - detect_single_image: 单张图片检测
  - detect_batch_images: 批量图片检测
  - detect_zip_images_file: ZIP 文件解压检测
  - detect_video_file: 视频文件检测

设计原则：
  - 每个工具使用 @tool 装饰器定义
  - docstring 必须详细，LLM 通过 docstring 理解工具用途
  - 返回值使用 JSON 字符串，便于 LLM 解析
"""

import json

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.services.detection_service import detection_service

logger = get_logger(__name__)


@tool
def detect_single_image(image_path: str, conf: float = 0.25, iou: float = 0.45) -> str:
    """检测单张杂草图片中的目标物体。

    当用户上传了一张图片并要求检测、识别、分析图中的目标时使用此工具。

    Args:
        image_path: 图片文件的服务器路径（绝对路径），如 /tmp/rsod_uploads/xxx.jpg
        conf: 置信度阈值，0~1 之间，默认 0.25。低于此值的检测结果会被过滤
        iou: NMS（非极大值抑制）IoU 阈值，0~1 之间，默认 0.45。用于去除重叠的检测框

    Returns:
        JSON 字符串，包含：
        - total_objects: 检测到的目标总数
        - class_counts: 各类别目标数量统计
        - objects: 每个目标的详细信息（类别、置信度、边界框）
        - inference_time: 推理耗时（毫秒）
        - annotated_image_url: 标注后的图片 URL
    """
    try:
        result = detection_service.detect_single(image_path, conf=conf, iou=iou)
        logger.info("单图检测完成: %s, 目标数: %d", image_path, result.get("total_objects", 0))
        # 注意：保留 annotated_image_base64，由 _smart_truncate 在 LLM 上下文中精简
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("单图检测失败: %s, 错误: %s", image_path, str(e))
        return json.dumps({"error": f"检测失败: {str(e)}"}, ensure_ascii=False)


@tool
def detect_batch_images(image_paths: list[str], conf: float = 0.25) -> str:
    """批量检测多张杂草图片中的目标物体。

    当用户一次上传了多张图片，或者要求"检测所有图片"时使用此工具。

    Args:
        image_paths: 图片文件路径列表
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含每张图片的检测结果汇总
    """
    try:
        result = detection_service.detect_batch(image_paths, conf=conf)
        logger.info("批量检测完成: %d 张图片", len(image_paths))
        # 保留 base64，由 _smart_truncate 精简
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("批量检测失败: %s", str(e))
        return json.dumps({"error": f"批量检测失败: {str(e)}"}, ensure_ascii=False)


@tool
def detect_zip_images_file(zip_path: str, conf: float = 0.25) -> str:
    """解压 ZIP 文件并批量检测其中所有图片的目标物体。

    当用户上传了 ZIP 压缩包进行批量检测时使用此工具。

    Args:
        zip_path: ZIP 文件的服务器路径
        conf: 置信度阈值，默认 0.25

    Returns:
        JSON 字符串，包含 ZIP 内所有图片的检测结果汇总
    """
    try:
        result = detection_service.detect_zip(zip_path, conf=conf)
        logger.info("ZIP 检测完成: %s", zip_path)
        # 保留 base64，由 _smart_truncate 精简
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("ZIP 检测失败: %s", str(e))
        return json.dumps({"error": f"ZIP 检测失败: {str(e)}"}, ensure_ascii=False)


@tool
def detect_video_file(video_path: str, conf: float = 0.25, frame_sample_rate: int = 5) -> str:
    """检测视频文件中的目标物体。对视频进行帧采样后逐帧检测。

    当用户上传了视频文件并要求检测视频中的目标时使用此工具。

    Args:
        video_path: 视频文件的服务器路径（mp4/avi/mov 等格式）
        conf: 置信度阈值，默认 0.25
        frame_sample_rate: 帧采样间隔，每 N 帧取 1 帧进行检测，默认 5

    Returns:
        JSON 字符串，包含视频检测结果（关键帧目标统计、视频时长、处理帧数）
    """
    try:
        result = detection_service.detect_video(
            video_path, conf=conf, frame_sample_rate=frame_sample_rate
        )
        # 保留数据，由 _smart_truncate 精简
        logger.info("视频检测完成: %s", video_path)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("视频检测失败: %s", str(e))
        return json.dumps({"error": f"视频检测失败: {str(e)}"}, ensure_ascii=False)


# 检测工具列表
DETECTION_TOOLS = [
    detect_single_image,
    detect_batch_images,
    detect_zip_images_file,
    detect_video_file,
]
"""
知识库检索工具 — 供 LangChain Agent 调用的 @tool

当用户询问目标检测相关概念、YOLO 使用方法、模型训练技巧等
知识性问题时，Agent 会自动调用此工具从知识库中检索相关内容。
"""

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.services.rag_service import rag_service

logger = get_logger(__name__)


@tool
def search_knowledge_base(query: str) -> str:
    """
    从知识库中检索与问题相关的专业知识。

    当用户询问以下类型的问题时，应调用此工具：
    - 目标检测相关概念（如 NMS、IoU、mAP 等）
    - YOLO 模型的使用方法和参数配置
    - 模型训练技巧和调参建议
    - 数据标注和数据集相关问题
    - 检测结果的解读和分析方法

    Args:
        query: 检索查询，应包含问题的关键词

    Returns:
        检索到的相关知识片段（含来源和相似度分数）
    """
    results = rag_service.search(query, top_k=3)

    if not results:
        return "知识库中未找到与该问题相关的内容。"

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"【知识片段 {i}】（来源：{r['title']}，相似度：{r['score']:.2f}）\n"
            f"{r['content']}"
        )

    return "\n\n---\n\n".join(formatted)

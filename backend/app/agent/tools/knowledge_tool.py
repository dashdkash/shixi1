"""
知识库检索工具 — 供 LangChain Agent 调用的 @tool

对于用户的任何提问（不仅限于目标检测），Agent 都应调用此工具检索知识库。
"""

from langchain_core.tools import tool

from app.core.logger import get_logger
from app.services.rag_service import rag_service

logger = get_logger(__name__)


@tool
def search_knowledge_base(query: str) -> str:
    """
    从知识库中检索与用户问题相关的内容。

    重要：对于用户的任何提问（不仅限于目标检测），都应该调用此工具。
    包括但不限于：人物、项目、技术概念、操作方法、常见问题等。
    不要自行判断问题是否在知识库中，必须调用工具检索后再回答。

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


# 知识库工具列表
KNOWLEDGE_TOOLS = [
    search_knowledge_base,
]

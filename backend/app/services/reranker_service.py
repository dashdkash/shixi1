"""
Reranker 服务 — 封装 DashScope gte-rerank 重排逻辑

职责：
  - 对向量检索的初筛结果做二次精排
  - 调用 DashScope Reranker API（gte-rerank 模型）
  - 按相关性分数重新排序，返回 Top-N 结果

使用方式：
  from app.services.reranker_service import reranker_service

  reranked = reranker_service.rerank("查询文本", candidates)
"""

import dashscope
from dashscope import TextReRank

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class RerankerService:
    """Reranker 重排服务"""

    def __init__(self):
        self._model = settings.RERANKER_MODEL
        self._top_n = settings.RERANKER_TOP_N
        # 设置 DashScope API Key
        dashscope.api_key = settings.QWEN_API_KEY
        logger.info(
            "RerankerService 初始化: model=%s, top_n=%d",
            self._model, self._top_n,
        )

    def rerank(
        self, query: str, candidates: list[dict], top_n: int = None
    ) -> list[dict]:
        """
        对候选结果做重排

        Args:
            query: 查询文本
            candidates: 初筛结果列表，每项需包含 "content" 字段
            top_n: 重排后保留条数，默认使用配置

        Returns:
            按重排分数排序的结果列表，新增 "rerank_score" 字段
        """
        if not candidates:
            return []

        top_n = top_n or self._top_n

        # 提取文本内容
        documents = [c["content"] for c in candidates]

        try:
            resp = TextReRank.call(
                model=self._model,
                query=query,
                documents=documents,
                top_n=min(top_n, len(documents)),
                return_documents=False,
            )

            if resp.status_code != 200:
                raise RuntimeError(f"Reranker API 错误: {resp.code} - {resp.message}")

            # 解析重排结果
            results = resp.output.get("results", [])

            # 按 rerank 分数组装结果
            reranked = []
            for item in results:
                idx = item["index"]
                score = item["relevance_score"]
                candidate = candidates[idx].copy()
                candidate["rerank_score"] = round(score, 4)
                reranked.append(candidate)

            logger.info(
                "Reranker 完成: query=%s, 初筛 %d 条 → 重排 %d 条",
                query[:50], len(candidates), len(reranked),
            )
            return reranked

        except Exception as e:
            logger.warning("Reranker 调用失败，返回原始排序结果: %s", str(e))
            return candidates[:top_n]


# 全局单例
reranker_service = RerankerService()

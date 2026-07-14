"""
Embedding 服务 — 封装 DashScope text-embedding-v3 向量化逻辑

职责：
  - 调用 DashScope text-embedding-v3 接口（通过 OpenAI 兼容 API）
  - 提供批量向量化（embed_texts）和单条向量化（embed_query）方法
  - 复用 QWEN_API_KEY 和 QWEN_BASE_URL 配置
  - 自动分批处理（DashScope 每次最多 25 条）

使用方式：
  from app.services.embedding_service import embedding_service

  vectors = embedding_service.embed_texts(["文本1", "文本2"])
  vector = embedding_service.embed_query("查询文本")
"""

from openai import OpenAI

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# DashScope text-embedding-v3 单次最大批量数
_BATCH_SIZE = 10


class EmbeddingService:
    """Embedding 向量化服务"""

    def __init__(self):
        self._client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        self._model = settings.EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIM
        logger.info(
            "EmbeddingService 初始化: model=%s, dim=%d",
            self._model, self._dim,
        )

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        调用 DashScope embedding API 并提取向量结果

        DashScope 兼容 OpenAI 格式，input 支持 list[str]。
        """
        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        # 按 index 排序确保顺序正确
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        批量向量化文本列表（自动分批）

        Args:
            texts: 文本列表

        Returns:
            向量列表，每个向量为 float 列表
        """
        if not texts:
            return []

        all_vectors = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            vectors = self._embed_batch(batch)
            all_vectors.extend(vectors)

        logger.info(
            "批量向量化完成: %d 条文本 → %d 维向量",
            len(texts), len(all_vectors[0]) if all_vectors else 0,
        )
        return all_vectors

    def embed_query(self, query: str) -> list[float]:
        """
        单条查询向量化

        Args:
            query: 查询文本

        Returns:
            向量（float 列表）
        """
        vectors = self._embed_batch([query])
        logger.debug("查询向量化: %d 维", len(vectors[0]))
        return vectors[0]


# 全局单例
embedding_service = EmbeddingService()

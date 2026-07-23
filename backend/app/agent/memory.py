"""
对话记忆管理 — 基于 Redis 的对话历史存储

职责：
  - 保存用户对话消息到 Redis（支持 TTL 过期）
  - 加载历史消息作为 Agent 上下文
  - 管理会话（创建、获取、删除）
  - 限制历史消息数量，防止上下文超长

架构：
  ConversationMemory 使用 Redis List 存储每个会话的消息列表。
  key 格式: chat:session:{user_id}:{session_id}
  value: JSON 序列化的消息列表

Redis key 设计：
  chat:session:user1:abc123  → [msg1, msg2, ...]  TTL=3600s
  chat:sessions:user1        → [session_id1, session_id2, ...] (会话索引)
"""

import json
import time
from typing import Optional

from app.core.logger import get_logger
from app.storage.redis_client import redis_client

logger = get_logger(__name__)

# 配置常量
MAX_HISTORY_MESSAGES = 20  # 最多加载的历史消息数
SESSION_TTL = 3600  # 会话过期时间（秒），1 小时
SESSION_INDEX_TTL = 86400  # 会话索引过期时间，24 小时


class ConversationMemory:
    """对话记忆管理器"""

    def __init__(self, max_messages: int = MAX_HISTORY_MESSAGES, ttl: int = SESSION_TTL):
        """
        初始化对话记忆

        Args:
            max_messages: 每次加载的最大历史消息数
            ttl: 会话 TTL（秒）
        """
        self.max_messages = max_messages
        self.ttl = ttl
        self.redis = redis_client

    def _session_key(self, user_id: int, session_id: str) -> str:
        """生成会话的 Redis key"""
        return f"chat:session:{user_id}:{session_id}"

    def _index_key(self, user_id: int) -> str:
        """生成会话索引的 Redis key"""
        return f"chat:sessions:{user_id}"

    def save_message(self, user_id: int, session_id: str, role: str, content: str):
        """
        保存一条对话消息到 Redis

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            role: 消息角色（"user" 或 "ai"）
            content: 消息内容
        """
        key = self._session_key(user_id, session_id)
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }

        # 使用 Redis List 的 RPUSH 追加消息
        self.redis.lpush(key, json.dumps(message, ensure_ascii=False))

        # 设置/刷新 TTL
        self.redis.set(f"{key}:ttl_flag", "1", expire=self.ttl)

        # 更新会话索引
        index_key = self._index_key(user_id)
        # 检查 session_id 是否已在索引中
        existing = self.redis.get(f"chat:exists:{user_id}:{session_id}")
        if not existing:
            self.redis.lpush(index_key, session_id)
            self.redis.set(f"chat:exists:{user_id}:{session_id}", "1", expire=SESSION_INDEX_TTL)

        logger.debug(
            "保存消息: user=%d, session=%s, role=%s, len=%d",
            user_id, session_id, role, len(content),
        )

    def load_history(self, user_id: int, session_id: str) -> list[dict]:
        """
        加载会话历史消息

        Args:
            user_id: 用户 ID
            session_id: 会话 ID

        Returns:
            消息列表 [{"role": "user", "content": "..."}, ...]
        """
        key = self._session_key(user_id, session_id)

        # 获取 Redis List 中的所有消息
        raw_messages = self._get_list(key)
        if not raw_messages:
            return []

        # 解析 JSON 并限制数量（取最后 N 条）
        messages = []
        for raw in raw_messages[-self.max_messages:]:
            try:
                msg = json.loads(raw) if isinstance(raw, str) else raw
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })
            except (json.JSONDecodeError, AttributeError):
                continue

        logger.debug(
            "加载历史: user=%d, session=%s, 消息数=%d",
            user_id, session_id, len(messages),
        )
        return messages

    def get_sessions(self, user_id: int) -> list[str]:
        """
        获取用户的所有会话 ID 列表

        Args:
            user_id: 用户 ID

        Returns:
            会话 ID 列表
        """
        index_key = self._index_key(user_id)
        sessions = self._get_list(index_key)
        return sessions if sessions else []

    def clear_session(self, user_id: int, session_id: str):
        """
        清空指定会话的历史消息

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
        """
        key = self._session_key(user_id, session_id)
        self.redis.delete(key)
        logger.info("清空会话: user=%d, session=%s", user_id, session_id)

    def _get_list(self, key: str) -> list:
        """
        获取 Redis List 数据，返回时间正序（最旧在前，最新在后）。
    
        注意：save_message 使用 LPUSH（左插入），Redis 中最新消息在头部。
        此方法统一 reverse 为时间正序，供 load_history 的 [-N:] 取最新 N 条。
    
        兼容 redis_client 的封装和直接 redis 操作。
        采用三层降级策略：Redis → redis_client 内部客户端 → 内存缓存 → 空列表
        """
        # 策略 1：尝试通过 redis_client 的内部 Redis 客户端读取
        try:
            client = getattr(self.redis, '_client', None)
            if client is not None:
                result = client.lrange(key, 0, -1)
                if result is not None:
                    # lpush 导致最新在前，reverse 为时间正序
                    result.reverse()
                    return result
        except Exception as e:
            logger.debug("Redis lrange 失败，尝试降级: %s", str(e))
    
        # 策略 2：降级到内存缓存（开发环境 / Redis 不可用时）
        try:
            cache = getattr(self.redis, '_memory_cache', None)
            if cache is not None:
                # 内存缓存也用 insert(0) 模拟 lpush，同样需要 reverse
                return list(reversed(cache.get(key, [])))
        except Exception as e:
            logger.debug("内存缓存读取失败: %s", str(e))
    
        # 策略 3：兖底返回空列表
        return []


# 创建全局单例
conversation_memory = ConversationMemory()
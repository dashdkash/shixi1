"""
Redis 客户端 — 封装 Redis 连接池和常用操作

生产环境标准：
  - 使用连接池避免频繁连接开销
  - 提供键值操作、哈希操作、列表操作的便捷方法
  - 添加超时和重试机制
  - Redis 不可用时自动降级到内存字典（开发环境）
"""

import json
import time
from typing import Any, Optional

import redis
from redis.exceptions import RedisError

from app.config.settings import settings


class RedisClient:
    """Redis 客户端封装"""

    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        """初始化 Redis 连接池"""
        self._memory_cache = {}
        try:
            self._pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                max_connections=20,
            )
            self._client = redis.Redis(connection_pool=self._pool)
            self._client.ping()
            self._use_redis = True
            print(f"Redis 连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            self._use_redis = False
            self._client = None
            print(f"Redis 连接失败，降级到内存存储: {e}")

    def _retry_on_fail(self, func, max_retries=3, delay=0.5):
        """重试装饰器"""
        if not self._use_redis:
            return func()
        for retry in range(max_retries):
            try:
                if not self._client:
                    self._connect()
                    if not self._use_redis:
                        return func()
                return func()
            except RedisError as e:
                if retry < max_retries - 1:
                    time.sleep(delay)
                    self._connect()
                    if not self._use_redis:
                        return func()
                else:
                    self._use_redis = False
                    return func()

    def set(self, key: str, value: str, expire: Optional[int] = None) -> Any:
        """设置键值"""
        return self._retry_on_fail(
            lambda: self._client.set(key, value, ex=expire) if self._use_redis else self._memory_cache.setdefault(key, value)
        )

    def get(self, key: str) -> Optional[str]:
        """获取键值"""
        return self._retry_on_fail(
            lambda: self._client.get(key) if self._use_redis else self._memory_cache.get(key)
        )

    def delete(self, key: str) -> Any:
        """删除键"""
        return self._retry_on_fail(
            lambda: self._client.delete(key) if self._use_redis else self._memory_cache.pop(key, None)
        )

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self._retry_on_fail(
            lambda: bool(self._client.exists(key)) if self._use_redis else key in self._memory_cache
        )

    def set_json(self, key: str, data: dict, expire: Optional[int] = None) -> Any:
        """设置 JSON 数据"""
        json_str = json.dumps(data, ensure_ascii=False)
        return self.set(key, json_str, expire)

    def get_json(self, key: str) -> Optional[dict]:
        """获取 JSON 数据"""
        value = self.get(key)
        if value:
            return json.loads(value)
        return None

    def hset(self, name: str, mapping: dict) -> Any:
        """设置哈希表"""
        return self._retry_on_fail(
            lambda: self._client.hset(name, mapping=mapping) if self._use_redis else self._memory_cache.setdefault(name, {}).update(mapping)
        )

    def hgetall(self, name: str) -> Optional[dict]:
        """获取哈希表所有数据"""
        return self._retry_on_fail(
            lambda: self._client.hgetall(name) if self._use_redis else self._memory_cache.get(name, {})
        )

    def lpush(self, name: str, *values: Any) -> Any:
        """列表左侧插入"""
        return self._retry_on_fail(
            lambda: self._client.lpush(name, *values) if self._use_redis else self._memory_cache.setdefault(name, []).extend(values)
        )

    def rpop(self, name: str) -> Optional[Any]:
        """列表右侧弹出"""
        return self._retry_on_fail(
            lambda: self._client.rpop(name) if self._use_redis else self._memory_cache.get(name, []).pop() if self._memory_cache.get(name) else None
        )

    def flushall(self) -> Any:
        """清空所有数据"""
        return self._retry_on_fail(
            lambda: self._client.flushall() if self._use_redis else self._memory_cache.clear()
        )

    def keys(self, pattern: str = "*") -> list:
        """获取匹配模式的所有键"""
        return self._retry_on_fail(
            lambda: self._client.keys(pattern) if self._use_redis else [k for k in self._memory_cache.keys() if pattern == "*" or k.startswith(pattern.replace("*", ""))]
        )

    def get_all_data(self) -> dict:
        """获取所有键值数据（调试用）"""
        data = {}
        if self._use_redis:
            for key in self.keys():
                try:
                    value = self.get(key)
                    data[key] = value
                except Exception:
                    data[key] = "无法解析"
        else:
            data = dict(self._memory_cache)
        return data

    def info(self) -> dict:
        """获取 Redis 客户端状态信息"""
        return {
            "use_redis": self._use_redis,
            "redis_host": settings.REDIS_HOST,
            "redis_port": settings.REDIS_PORT,
            "key_count": len(self.keys()),
            "memory_usage": self._client.info("memory") if self._use_redis and self._client else None,
        }


redis_client = RedisClient()
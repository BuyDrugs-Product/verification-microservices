"""
Redis cache implementation for production deployments
Provides shared cache across multiple workers/pods
"""

import json
from typing import Optional, Dict, Any
from ..core.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis-backed cache for production use"""

    def __init__(self, redis_url: str, default_ttl: int = 3600, key_prefix: str = "ppb:"):
        """
        Initialize Redis cache

        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live in seconds
            key_prefix: Prefix for all cache keys (for namespacing)
        """
        try:
            import redis
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.default_ttl = default_ttl
            self.key_prefix = key_prefix
            
            # Test connection
            self.redis.ping()
            logger.info(f"RedisCache initialized: url={redis_url}, ttl={default_ttl}s")
        except ImportError:
            logger.error("redis-py not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{self.key_prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            full_key = self._make_key(key)
            value = self.redis.get(full_key)
            
            if value is None:
                logger.debug(f"Cache MISS: {key}")
                return None
            
            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)
        except Exception as e:
            logger.error(f"Cache GET error for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        try:
            full_key = self._make_key(key)
            if ttl is None:
                ttl = self.default_ttl
            
            self.redis.setex(full_key, ttl, json.dumps(value))
            logger.debug(f"Cache SET: {key} (ttl={ttl}s)")
        except Exception as e:
            logger.error(f"Cache SET error for {key}: {e}")

    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        try:
            full_key = self._make_key(key)
            result = self.redis.delete(full_key)
            logger.debug(f"Cache DELETE: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Cache DELETE error for {key}: {e}")
            return False

    def clear(self) -> None:
        """Clear all cache entries with the prefix"""
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                logger.info(f"Cache CLEARED: {len(keys)} entries removed")
        except Exception as e:
            logger.error(f"Cache CLEAR error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        try:
            info = self.redis.info("stats")
            pattern = f"{self.key_prefix}*"
            key_count = len(self.redis.keys(pattern))
            
            return {
                "backend": "redis",
                "size": key_count,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"Cache STATS error: {e}")
            return {"backend": "redis", "error": str(e)}


def get_cache(backend: str, **kwargs):
    """
    Factory function to get appropriate cache implementation

    Args:
        backend: Cache backend ('simple' or 'redis')
        **kwargs: Backend-specific configuration

    Returns:
        Cache instance
    """
    if backend == "redis":
        from .cache_redis import RedisCache
        return RedisCache(**kwargs)
    else:
        from .cache_simple import SimpleCache
        return SimpleCache(**kwargs)


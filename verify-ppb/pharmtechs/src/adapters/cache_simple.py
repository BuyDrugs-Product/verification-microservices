"""
Simple in-memory cache implementation
Thread-safe cache with TTL and LRU eviction
"""

import time
from typing import Optional, Dict, Any
from collections import OrderedDict
import threading
from ..core.logger import get_logger

logger = get_logger(__name__)


class SimpleCache:
    """Thread-safe in-memory cache with TTL and LRU eviction"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize cache

        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
        }
        logger.info(f"SimpleCache initialized: max_size={max_size}, ttl={default_ttl}s")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                logger.debug(f"Cache MISS: {key}")
                return None

            entry = self.cache[key]
            current_time = time.time()

            # Check if expired
            if current_time > entry["expires_at"]:
                del self.cache[key]
                self.stats["misses"] += 1
                logger.debug(f"Cache MISS (expired): {key}")
                return None

            # Move to end (LRU)
            self.cache.move_to_end(key)
            self.stats["hits"] += 1
            logger.debug(f"Cache HIT: {key}")
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self.lock:
            if ttl is None:
                ttl = self.default_ttl

            # Evict oldest if at capacity
            if key not in self.cache and len(self.cache) >= self.max_size:
                evicted_key = self.cache.popitem(last=False)[0]
                self.stats["evictions"] += 1
                logger.debug(f"Cache EVICTED: {evicted_key}")

            self.cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
                "created_at": time.time(),
            }

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.stats["sets"] += 1
            logger.debug(f"Cache SET: {key} (ttl={ttl}s)")

    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache DELETE: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cache CLEARED: {count} entries removed")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0

            return {
                "backend": "simple",
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "sets": self.stats["sets"],
                "evictions": self.stats["evictions"],
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
            }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries

        Returns:
            Number of entries removed
        """
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items() if current_time > entry["expires_at"]
            ]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(f"Cache cleanup: {len(expired_keys)} expired entries removed")

            return len(expired_keys)

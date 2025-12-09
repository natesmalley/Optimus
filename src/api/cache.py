"""
Caching Strategy with Redis and Response Optimization
Provides intelligent caching, cache invalidation, and response optimization.
"""

import json
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from fastapi import Request, Response
from redis.asyncio import Redis
from pydantic import BaseModel

from ..config import get_settings, redis_manager, logger


class CacheStrategy(str, Enum):
    """Cache strategy types."""
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"
    REFRESH_AHEAD = "refresh_ahead"


class CacheLevel(str, Enum):
    """Cache levels."""
    L1_MEMORY = "l1_memory"  # In-memory cache
    L2_REDIS = "l2_redis"    # Redis cache
    L3_DATABASE = "l3_database"  # Database cache


@dataclass
class CacheConfig:
    """Cache configuration."""
    ttl_seconds: int = 300  # 5 minutes default
    strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH
    enabled: bool = True
    compress: bool = False
    invalidate_on_write: bool = True
    warm_cache: bool = False
    max_size: Optional[int] = None


class CacheItem(BaseModel):
    """Cached item with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime
    etag: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: int = 0


class CacheStats(BaseModel):
    """Cache statistics."""
    hit_count: int = 0
    miss_count: int = 0
    hit_ratio: float = 0.0
    total_keys: int = 0
    total_size_bytes: int = 0
    eviction_count: int = 0
    average_ttl: float = 0.0


class AdvancedCache:
    """Advanced multi-level caching system."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or redis_manager.client
        self.settings = get_settings()
        
        # L1 Cache (in-memory)
        self.memory_cache: Dict[str, CacheItem] = {}
        self.memory_cache_max_size = 1000  # Max items in memory
        
        # Cache statistics
        self.stats = CacheStats()
        
        # Cache configurations by pattern
        self.cache_configs: Dict[str, CacheConfig] = {
            # Project data - cache for 5 minutes
            "projects:*": CacheConfig(ttl_seconds=300),
            
            # Runtime status - cache for 1 minute
            "runtime:*": CacheConfig(ttl_seconds=60),
            
            # Metrics - cache for 30 seconds
            "metrics:*": CacheConfig(ttl_seconds=30),
            
            # Council deliberations - cache for 10 minutes
            "council:*": CacheConfig(ttl_seconds=600),
            
            # Static data - cache for 1 hour
            "static:*": CacheConfig(ttl_seconds=3600),
            
            # User data - cache for 15 minutes
            "user:*": CacheConfig(ttl_seconds=900),
            
            # Analytics - cache for 5 minutes
            "analytics:*": CacheConfig(ttl_seconds=300),
            
            # Default configuration
            "*": CacheConfig(ttl_seconds=300)
        }
        
        # Cache warming tasks
        self.cache_warming_tasks: Dict[str, asyncio.Task] = {}
        
        # Invalidation patterns
        self.invalidation_patterns: Dict[str, List[str]] = {
            "projects:write": ["projects:*", "analytics:projects:*"],
            "runtime:write": ["runtime:*", "metrics:runtime:*"],
            "user:write": ["user:*", "analytics:users:*"]
        }
    
    def _get_cache_config(self, key: str) -> CacheConfig:
        """Get cache configuration for key."""
        # Check for exact match first
        if key in self.cache_configs:
            return self.cache_configs[key]
        
        # Check for pattern matches
        for pattern, config in self.cache_configs.items():
            if self._pattern_matches(pattern, key):
                return config
        
        # Return default
        return self.cache_configs["*"]
    
    def _pattern_matches(self, pattern: str, key: str) -> bool:
        """Check if key matches pattern."""
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return pattern == key
        
        # Simple wildcard matching
        parts = pattern.split("*")
        
        if len(parts) == 2:  # prefix* or *suffix
            prefix, suffix = parts
            if prefix and not key.startswith(prefix):
                return False
            if suffix and not key.endswith(suffix):
                return False
            return True
        
        # More complex patterns would need proper regex
        return False
    
    def _generate_etag(self, data: Any) -> str:
        """Generate ETag for data."""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get(self, key: str, default: Any = None) -> Tuple[Any, bool]:
        """Get value from cache with hit/miss tracking."""
        try:
            # Try L1 cache (memory) first
            memory_item = self._get_from_memory(key)
            if memory_item:
                if not self._is_expired(memory_item):
                    memory_item.access_count += 1
                    memory_item.last_accessed = datetime.now()
                    self.stats.hit_count += 1
                    return memory_item.value, True
                else:
                    # Remove expired item
                    self._remove_from_memory(key)
            
            # Try L2 cache (Redis)
            redis_value = await self._get_from_redis(key)
            if redis_value is not None:
                # Store in L1 cache
                config = self._get_cache_config(key)
                cache_item = CacheItem(
                    key=key,
                    value=redis_value,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(seconds=config.ttl_seconds),
                    access_count=1,
                    last_accessed=datetime.now(),
                    etag=self._generate_etag(redis_value)
                )
                self._store_in_memory(cache_item)
                
                self.stats.hit_count += 1
                return redis_value, True
            
            # Cache miss
            self.stats.miss_count += 1
            self._update_hit_ratio()
            return default, False
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            self.stats.miss_count += 1
            return default, False
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            config = self._get_cache_config(key)
            if not config.enabled:
                return False
            
            ttl = ttl or config.ttl_seconds
            expires_at = datetime.now() + timedelta(seconds=ttl)
            etag = self._generate_etag(value)
            
            # Create cache item
            cache_item = CacheItem(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
                access_count=0,
                last_accessed=datetime.now(),
                etag=etag,
                size_bytes=len(json.dumps(value, default=str))
            )
            
            # Store in L1 cache (memory)
            self._store_in_memory(cache_item)
            
            # Store in L2 cache (Redis)
            await self._store_in_redis(key, value, ttl)
            
            # Update stats
            self.stats.total_keys += 1
            self.stats.total_size_bytes += cache_item.size_bytes
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache levels."""
        try:
            # Remove from L1 cache
            self._remove_from_memory(key)
            
            # Remove from L2 cache
            await self._remove_from_redis(key)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        try:
            count = 0
            
            # Invalidate from memory cache
            keys_to_remove = []
            for key in self.memory_cache.keys():
                if self._pattern_matches(pattern, key):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._remove_from_memory(key)
                count += 1
            
            # Invalidate from Redis
            redis_keys = await self.redis.keys(pattern.replace("*", "*"))
            if redis_keys:
                await self.redis.delete(*redis_keys)
                count += len(redis_keys)
            
            logger.info(f"Invalidated {count} cache keys matching pattern: {pattern}")
            return count
            
        except Exception as e:
            logger.error(f"Error invalidating pattern {pattern}: {e}")
            return 0
    
    async def invalidate_dependencies(self, write_key: str):
        """Invalidate cache based on write dependencies."""
        for write_pattern, invalidate_patterns in self.invalidation_patterns.items():
            if self._pattern_matches(write_pattern, write_key):
                for pattern in invalidate_patterns:
                    await self.invalidate_pattern(pattern)
    
    def _get_from_memory(self, key: str) -> Optional[CacheItem]:
        """Get item from memory cache."""
        return self.memory_cache.get(key)
    
    def _store_in_memory(self, cache_item: CacheItem):
        """Store item in memory cache with LRU eviction."""
        # Check if we need to evict items
        if len(self.memory_cache) >= self.memory_cache_max_size:
            self._evict_lru_memory()
        
        self.memory_cache[cache_item.key] = cache_item
    
    def _remove_from_memory(self, key: str):
        """Remove item from memory cache."""
        if key in self.memory_cache:
            item = self.memory_cache.pop(key)
            self.stats.total_size_bytes -= item.size_bytes
    
    def _evict_lru_memory(self):
        """Evict least recently used item from memory cache."""
        if not self.memory_cache:
            return
        
        # Find LRU item
        lru_key = min(
            self.memory_cache.keys(),
            key=lambda k: self.memory_cache[k].last_accessed
        )
        
        self._remove_from_memory(lru_key)
        self.stats.eviction_count += 1
    
    def _is_expired(self, cache_item: CacheItem) -> bool:
        """Check if cache item is expired."""
        return datetime.now() > cache_item.expires_at
    
    async def _get_from_redis(self, key: str) -> Any:
        """Get value from Redis cache."""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value.decode())
            return None
        except Exception as e:
            logger.error(f"Error getting from Redis cache {key}: {e}")
            return None
    
    async def _store_in_redis(self, key: str, value: Any, ttl: int):
        """Store value in Redis cache."""
        try:
            serialized_value = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Error storing in Redis cache {key}: {e}")
    
    async def _remove_from_redis(self, key: str):
        """Remove value from Redis cache."""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Error removing from Redis cache {key}: {e}")
    
    def _update_hit_ratio(self):
        """Update cache hit ratio."""
        total_requests = self.stats.hit_count + self.stats.miss_count
        if total_requests > 0:
            self.stats.hit_ratio = self.stats.hit_count / total_requests
    
    async def warm_cache(self, keys_and_loaders: Dict[str, Callable]) -> int:
        """Warm cache with provided data loaders."""
        warmed_count = 0
        
        for key, loader in keys_and_loaders.items():
            try:
                # Check if already cached
                _, hit = await self.get(key)
                if hit:
                    continue
                
                # Load data and cache it
                data = await loader() if asyncio.iscoroutinefunction(loader) else loader()
                await self.set(key, data)
                warmed_count += 1
                
            except Exception as e:
                logger.error(f"Error warming cache for key {key}: {e}")
        
        logger.info(f"Cache warming completed: {warmed_count} keys warmed")
        return warmed_count
    
    async def get_cache_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        try:
            # Update Redis stats
            redis_info = await self.redis.info("memory")
            redis_memory = redis_info.get("used_memory", 0)
            
            # Count Redis keys (approximate)
            redis_key_count = await self.redis.dbsize()
            
            self.stats.total_keys = len(self.memory_cache) + redis_key_count
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return self.stats
    
    async def clear_all_cache(self) -> bool:
        """Clear all cache levels."""
        try:
            # Clear memory cache
            self.memory_cache.clear()
            
            # Clear Redis cache (only Optimus keys)
            optimus_keys = await self.redis.keys("optimus:*")
            if optimus_keys:
                await self.redis.delete(*optimus_keys)
            
            # Reset stats
            self.stats = CacheStats()
            
            logger.info("All cache levels cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
            return False
    
    async def get_cached_keys(self, pattern: str = "*", limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of cached keys with metadata."""
        keys_info = []
        
        # Memory cache keys
        for key, item in self.memory_cache.items():
            if self._pattern_matches(pattern, key) and len(keys_info) < limit:
                keys_info.append({
                    "key": key,
                    "level": "memory",
                    "size_bytes": item.size_bytes,
                    "created_at": item.created_at.isoformat(),
                    "expires_at": item.expires_at.isoformat(),
                    "access_count": item.access_count,
                    "last_accessed": item.last_accessed.isoformat(),
                    "etag": item.etag
                })
        
        # Redis cache keys (sample)
        if len(keys_info) < limit:
            try:
                redis_keys = await self.redis.keys(pattern.replace("*", "*"))
                for key in redis_keys[:limit - len(keys_info)]:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    ttl = await self.redis.ttl(key_str)
                    
                    keys_info.append({
                        "key": key_str,
                        "level": "redis",
                        "ttl_seconds": ttl,
                        "size_bytes": 0  # Would need to get and measure
                    })
            except Exception as e:
                logger.error(f"Error getting Redis keys: {e}")
        
        return keys_info


class ResponseCache:
    """HTTP response caching with ETag support."""
    
    def __init__(self, cache: AdvancedCache):
        self.cache = cache
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for HTTP request."""
        # Include method, path, and relevant query parameters
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        
        # Include user ID if available
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        return f"http:{hashlib.md5('|'.join(key_parts).encode()).hexdigest()}"
    
    async def get_cached_response(self, request: Request) -> Optional[Tuple[Any, str]]:
        """Get cached response for request."""
        cache_key = self._generate_cache_key(request)
        cached_data, hit = await self.cache.get(cache_key)
        
        if hit and cached_data:
            return cached_data.get("content"), cached_data.get("etag")
        
        return None
    
    async def cache_response(self, request: Request, content: Any, 
                           etag: str = None, ttl: int = None) -> bool:
        """Cache response data."""
        cache_key = self._generate_cache_key(request)
        etag = etag or self.cache._generate_etag(content)
        
        cached_data = {
            "content": content,
            "etag": etag,
            "cached_at": datetime.now().isoformat()
        }
        
        return await self.cache.set(cache_key, cached_data, ttl)
    
    def check_if_none_match(self, request: Request, etag: str) -> bool:
        """Check If-None-Match header for conditional requests."""
        if_none_match = request.headers.get("if-none-match")
        if if_none_match:
            # Simple ETag comparison (should handle weak/strong ETags properly)
            return etag in if_none_match.replace("W/", "").split(",")
        return False


# Global cache instances
advanced_cache = AdvancedCache()
response_cache = ResponseCache(advanced_cache)


# Cache decorators and utilities
def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_parts = []
    
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest())
    
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    return ":".join(key_parts)


async def cached_function(func: Callable, cache_key: str, ttl: int = 300):
    """Cache function result."""
    # Check cache first
    result, hit = await advanced_cache.get(cache_key)
    if hit:
        return result
    
    # Execute function and cache result
    if asyncio.iscoroutinefunction(func):
        result = await func()
    else:
        result = func()
    
    await advanced_cache.set(cache_key, result, ttl)
    return result


# Convenience functions
async def get_cache() -> AdvancedCache:
    """Get global cache instance."""
    return advanced_cache


async def get_response_cache() -> ResponseCache:
    """Get global response cache instance."""
    return response_cache


async def cache_warm_up():
    """Warm up cache with frequently accessed data."""
    # This would typically be called during application startup
    warm_data = {
        "static:api_version": lambda: "1.0.0",
        "static:supported_features": lambda: ["orchestration", "council", "monitoring"],
        # Add more warm-up data as needed
    }
    
    return await advanced_cache.warm_cache(warm_data)
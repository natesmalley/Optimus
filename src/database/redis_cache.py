"""
Redis Caching Layer

High-performance distributed caching system for Optimus Council of Minds
with intelligent cache management, serialization, and performance optimization.
"""

import json
import pickle
import asyncio
import zlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass
import hashlib
import redis.asyncio as redis
from enum import Enum
import logging

from .config import get_database_manager, DatabaseManager

T = TypeVar('T')


class CacheStrategy(Enum):
    """Cache strategies for different data types"""
    LRU = "lru"              # Least Recently Used
    LFU = "lfu"              # Least Frequently Used  
    TTL = "ttl"              # Time To Live
    WRITE_THROUGH = "write_through"    # Write to cache and DB
    WRITE_BEHIND = "write_behind"      # Write to cache, async to DB
    READ_THROUGH = "read_through"      # Load from DB if not in cache


class SerializationType(Enum):
    """Serialization methods for different data types"""
    JSON = "json"
    PICKLE = "pickle"
    COMPRESSED_JSON = "compressed_json"
    COMPRESSED_PICKLE = "compressed_pickle"


@dataclass
class CacheConfig:
    """Cache configuration for different data types"""
    ttl: int = 3600  # Time to live in seconds
    strategy: CacheStrategy = CacheStrategy.TTL
    serialization: SerializationType = SerializationType.JSON
    max_size: Optional[int] = None  # Maximum items (for LRU/LFU)
    compression_threshold: int = 1000  # Compress if data > N bytes
    namespace: str = "optimus"


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    memory_usage: int = 0
    avg_response_time: float = 0.0
    
    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheSerializer:
    """Handles serialization and compression of cache data"""
    
    @staticmethod
    def serialize(data: Any, serialization: SerializationType, compression_threshold: int = 1000) -> bytes:
        """Serialize data based on the specified method"""
        if serialization == SerializationType.JSON:
            serialized = json.dumps(data, default=str).encode('utf-8')
        elif serialization == SerializationType.PICKLE:
            serialized = pickle.dumps(data)
        elif serialization == SerializationType.COMPRESSED_JSON:
            json_data = json.dumps(data, default=str).encode('utf-8')
            serialized = zlib.compress(json_data) if len(json_data) > compression_threshold else json_data
        elif serialization == SerializationType.COMPRESSED_PICKLE:
            pickle_data = pickle.dumps(data)
            serialized = zlib.compress(pickle_data) if len(pickle_data) > compression_threshold else pickle_data
        else:
            raise ValueError(f"Unknown serialization type: {serialization}")
        
        # Add metadata header to identify serialization method and compression
        compressed = len(serialized) < len(str(data))
        header = f"{serialization.value}|{compressed}|".encode('utf-8')
        return header + serialized
    
    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize data based on header information"""
        # Extract header
        header_end = data.find(b'|', data.find(b'|') + 1) + 1
        header = data[:header_end].decode('utf-8')
        serialized_data = data[header_end:]
        
        parts = header.rstrip('|').split('|')
        serialization_type = parts[0]
        is_compressed = parts[1].lower() == 'true'
        
        # Decompress if needed
        if is_compressed:
            serialized_data = zlib.decompress(serialized_data)
        
        # Deserialize based on type
        if serialization_type == 'json' or serialization_type == 'compressed_json':
            return json.loads(serialized_data.decode('utf-8'))
        elif serialization_type == 'pickle' or serialization_type == 'compressed_pickle':
            return pickle.loads(serialized_data)
        else:
            raise ValueError(f"Unknown serialization type: {serialization_type}")


class CacheLayer:
    """
    High-performance Redis caching layer with advanced features:
    - Multiple serialization strategies
    - Compression for large objects  
    - Cache warming and preloading
    - Distributed cache invalidation
    - Performance monitoring
    - Automatic failover
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, default_config: Optional[CacheConfig] = None):
        self.db_manager = db_manager or get_database_manager()
        self.default_config = default_config or CacheConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.stats = CacheStats()
        self.serializer = CacheSerializer()
        self.config_registry: Dict[str, CacheConfig] = {}
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.operation_times: List[float] = []
        self.last_stats_update = datetime.now()
    
    async def initialize(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            self.redis_client = await self.db_manager.get_redis_client()
            
            # Test connection
            try:
                await self.redis_client.ping()
                self.logger.info("Redis cache layer initialized successfully")
            except Exception as e:
                self.logger.error(f"Redis connection failed: {e}")
                raise
    
    def register_cache_config(self, key_pattern: str, config: CacheConfig):
        """Register cache configuration for specific key patterns"""
        self.config_registry[key_pattern] = config
    
    def _get_config_for_key(self, key: str) -> CacheConfig:
        """Get cache configuration for a specific key"""
        for pattern, config in self.config_registry.items():
            if pattern in key or key.startswith(pattern):
                return config
        return self.default_config
    
    def _build_cache_key(self, namespace: str, key: str) -> str:
        """Build a namespaced cache key"""
        return f"{namespace}:{key}"
    
    async def get(self, key: str, namespace: Optional[str] = None) -> Optional[Any]:
        """Get value from cache with performance tracking"""
        if not self.redis_client:
            await self.initialize()
        
        start_time = datetime.now()
        config = self._get_config_for_key(key)
        cache_key = self._build_cache_key(namespace or config.namespace, key)
        
        try:
            # Get from Redis
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                # Deserialize
                result = self.serializer.deserialize(cached_data)
                
                # Update access time for LRU/LFU strategies
                if config.strategy in [CacheStrategy.LRU, CacheStrategy.LFU]:
                    await self._update_access_info(cache_key, config.strategy)
                
                self.stats.hits += 1
                self._track_operation_time(start_time)
                
                return result
            else:
                self.stats.misses += 1
                return None
                
        except Exception as e:
            self.logger.error(f"Cache get error for key {cache_key}: {e}")
            self.stats.misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: Optional[str] = None) -> bool:
        """Set value in cache with intelligent serialization"""
        if not self.redis_client:
            await self.initialize()
        
        start_time = datetime.now()
        config = self._get_config_for_key(key)
        cache_key = self._build_cache_key(namespace or config.namespace, key)
        effective_ttl = ttl or config.ttl
        
        try:
            # Serialize data
            serialized_data = self.serializer.serialize(
                value, config.serialization, config.compression_threshold
            )
            
            # Handle different cache strategies
            if config.strategy == CacheStrategy.TTL:
                success = await self.redis_client.setex(cache_key, effective_ttl, serialized_data)
            elif config.strategy in [CacheStrategy.LRU, CacheStrategy.LFU]:
                success = await self._set_with_eviction(cache_key, serialized_data, effective_ttl, config)
            else:
                success = await self.redis_client.set(cache_key, serialized_data, ex=effective_ttl)
            
            if success:
                self.stats.sets += 1
                self._track_operation_time(start_time)
                return True
            
        except Exception as e:
            self.logger.error(f"Cache set error for key {cache_key}: {e}")
        
        return False
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            await self.initialize()
        
        config = self._get_config_for_key(key)
        cache_key = self._build_cache_key(namespace or config.namespace, key)
        
        try:
            deleted = await self.redis_client.delete(cache_key)
            if deleted:
                self.stats.deletes += 1
                return True
        except Exception as e:
            self.logger.error(f"Cache delete error for key {cache_key}: {e}")
        
        return False
    
    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            await self.initialize()
        
        config = self._get_config_for_key(key)
        cache_key = self._build_cache_key(namespace or config.namespace, key)
        
        try:
            return bool(await self.redis_client.exists(cache_key))
        except Exception as e:
            self.logger.error(f"Cache exists error for key {cache_key}: {e}")
            return False
    
    async def mget(self, keys: List[str], namespace: Optional[str] = None) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self.redis_client or not keys:
            return {}
        
        # Build cache keys
        config = self._get_config_for_key(keys[0])
        cache_keys = [self._build_cache_key(namespace or config.namespace, key) for key in keys]
        
        try:
            # Get all values
            cached_values = await self.redis_client.mget(cache_keys)
            
            result = {}
            for key, cached_data in zip(keys, cached_values):
                if cached_data:
                    try:
                        result[key] = self.serializer.deserialize(cached_data)
                        self.stats.hits += 1
                    except Exception as e:
                        self.logger.warning(f"Deserialization error for key {key}: {e}")
                else:
                    self.stats.misses += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cache mget error: {e}")
            return {}
    
    async def mset(self, data: Dict[str, Any], ttl: Optional[int] = None, namespace: Optional[str] = None) -> bool:
        """Set multiple values in cache"""
        if not self.redis_client or not data:
            return False
        
        config = self._get_config_for_key(list(data.keys())[0])
        effective_ttl = ttl or config.ttl
        
        try:
            # Serialize all data
            cache_data = {}
            for key, value in data.items():
                cache_key = self._build_cache_key(namespace or config.namespace, key)
                serialized_data = self.serializer.serialize(
                    value, config.serialization, config.compression_threshold
                )
                cache_data[cache_key] = serialized_data
            
            # Use pipeline for better performance
            async with self.redis_client.pipeline() as pipe:
                # Set all values
                await pipe.mset(cache_data)
                
                # Set TTL for each key
                for cache_key in cache_data.keys():
                    await pipe.expire(cache_key, effective_ttl)
                
                await pipe.execute()
            
            self.stats.sets += len(data)
            return True
            
        except Exception as e:
            self.logger.error(f"Cache mset error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str, namespace: Optional[str] = None) -> int:
        """Invalidate all keys matching a pattern"""
        if not self.redis_client:
            return 0
        
        config = self._get_config_for_key(pattern)
        search_pattern = self._build_cache_key(namespace or config.namespace, pattern)
        
        try:
            # Find matching keys
            keys = []
            async for key in self.redis_client.scan_iter(match=search_pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                self.stats.deletes += deleted
                return deleted
            
        except Exception as e:
            self.logger.error(f"Cache invalidate pattern error: {e}")
        
        return 0
    
    async def _set_with_eviction(self, cache_key: str, data: bytes, ttl: int, config: CacheConfig) -> bool:
        """Set value with LRU/LFU eviction policies"""
        if config.max_size:
            # Check current size
            current_size = await self._get_namespace_size(config.namespace)
            
            if current_size >= config.max_size:
                # Evict based on strategy
                if config.strategy == CacheStrategy.LRU:
                    await self._evict_lru(config.namespace)
                elif config.strategy == CacheStrategy.LFU:
                    await self._evict_lfu(config.namespace)
        
        # Set the value
        success = await self.redis_client.setex(cache_key, ttl, data)
        
        if success and config.strategy in [CacheStrategy.LRU, CacheStrategy.LFU]:
            # Update access metadata
            await self._update_access_info(cache_key, config.strategy)
        
        return success
    
    async def _update_access_info(self, cache_key: str, strategy: CacheStrategy):
        """Update access information for LRU/LFU strategies"""
        try:
            if strategy == CacheStrategy.LRU:
                # Update last access time
                await self.redis_client.zadd(f"{cache_key}:access_time", {cache_key: datetime.now().timestamp()})
            elif strategy == CacheStrategy.LFU:
                # Increment access count
                await self.redis_client.zincrby(f"{cache_key}:access_count", 1, cache_key)
        except Exception as e:
            self.logger.warning(f"Access info update error: {e}")
    
    async def _get_namespace_size(self, namespace: str) -> int:
        """Get the number of keys in a namespace"""
        try:
            count = 0
            async for _ in self.redis_client.scan_iter(match=f"{namespace}:*"):
                count += 1
            return count
        except Exception:
            return 0
    
    async def _evict_lru(self, namespace: str):
        """Evict least recently used item"""
        try:
            # Get the least recently accessed key
            result = await self.redis_client.zrange(f"{namespace}:*:access_time", 0, 0)
            if result:
                oldest_key = result[0].decode('utf-8')
                await self.redis_client.delete(oldest_key)
                await self.redis_client.zrem(f"{namespace}:*:access_time", oldest_key)
                self.stats.evictions += 1
        except Exception as e:
            self.logger.warning(f"LRU eviction error: {e}")
    
    async def _evict_lfu(self, namespace: str):
        """Evict least frequently used item"""
        try:
            # Get the least frequently accessed key
            result = await self.redis_client.zrange(f"{namespace}:*:access_count", 0, 0)
            if result:
                least_used_key = result[0].decode('utf-8')
                await self.redis_client.delete(least_used_key)
                await self.redis_client.zrem(f"{namespace}:*:access_count", least_used_key)
                self.stats.evictions += 1
        except Exception as e:
            self.logger.warning(f"LFU eviction error: {e}")
    
    def _track_operation_time(self, start_time: datetime):
        """Track operation performance"""
        operation_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
        self.operation_times.append(operation_time)
        
        # Keep only recent measurements
        if len(self.operation_times) > 1000:
            self.operation_times = self.operation_times[-1000:]
        
        # Update average response time
        self.stats.avg_response_time = sum(self.operation_times) / len(self.operation_times)
    
    async def warm_cache(self, warm_function: Callable[[], Dict[str, Any]], namespace: str = "warm"):
        """Warm cache with precomputed data"""
        try:
            warm_data = warm_function()
            if warm_data:
                await self.mset(warm_data, namespace=namespace)
                self.logger.info(f"Cache warmed with {len(warm_data)} items in namespace {namespace}")
        except Exception as e:
            self.logger.error(f"Cache warming error: {e}")
    
    async def get_cache_info(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive cache information"""
        if not self.redis_client:
            return {}
        
        try:
            # Redis info
            redis_info = await self.redis_client.info()
            
            # Namespace-specific info if requested
            namespace_info = {}
            if namespace:
                pattern = f"{namespace}:*"
                keys = []
                sizes = []
                
                async for key in self.redis_client.scan_iter(match=pattern):
                    keys.append(key)
                    try:
                        size = await self.redis_client.memory_usage(key)
                        sizes.append(size or 0)
                    except:
                        sizes.append(0)
                
                namespace_info = {
                    'key_count': len(keys),
                    'total_memory': sum(sizes),
                    'avg_key_size': sum(sizes) / len(sizes) if sizes else 0
                }
            
            return {
                'stats': {
                    'hits': self.stats.hits,
                    'misses': self.stats.misses,
                    'hit_ratio': self.stats.hit_ratio,
                    'sets': self.stats.sets,
                    'deletes': self.stats.deletes,
                    'evictions': self.stats.evictions,
                    'avg_response_time_ms': self.stats.avg_response_time
                },
                'redis_info': {
                    'used_memory': redis_info.get('used_memory', 0),
                    'used_memory_human': redis_info.get('used_memory_human', '0'),
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'total_connections_received': redis_info.get('total_connections_received', 0),
                    'total_commands_processed': redis_info.get('total_commands_processed', 0),
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0)
                },
                'namespace_info': namespace_info
            }
            
        except Exception as e:
            self.logger.error(f"Cache info error: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            if not self.redis_client:
                await self.initialize()
            
            await self.redis_client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None


class CacheManager:
    """
    High-level cache manager with domain-specific caching strategies
    """
    
    def __init__(self, cache_layer: Optional[CacheLayer] = None):
        self.cache = cache_layer or CacheLayer()
        self._setup_cache_configs()
    
    def _setup_cache_configs(self):
        """Setup cache configurations for different data types"""
        # Memory system caching
        self.cache.register_cache_config(
            "memory:",
            CacheConfig(
                ttl=1800,  # 30 minutes
                strategy=CacheStrategy.LRU,
                serialization=SerializationType.COMPRESSED_PICKLE,
                max_size=1000,
                namespace="memory"
            )
        )
        
        # Knowledge graph caching
        self.cache.register_cache_config(
            "knowledge:",
            CacheConfig(
                ttl=3600,  # 1 hour
                strategy=CacheStrategy.LFU,
                serialization=SerializationType.COMPRESSED_JSON,
                max_size=500,
                namespace="knowledge"
            )
        )
        
        # Project data caching
        self.cache.register_cache_config(
            "project:",
            CacheConfig(
                ttl=900,  # 15 minutes
                strategy=CacheStrategy.TTL,
                serialization=SerializationType.JSON,
                namespace="projects"
            )
        )
        
        # Analysis results caching
        self.cache.register_cache_config(
            "analysis:",
            CacheConfig(
                ttl=7200,  # 2 hours
                strategy=CacheStrategy.TTL,
                serialization=SerializationType.COMPRESSED_JSON,
                namespace="analysis"
            )
        )
        
        # Dashboard data caching (short TTL for real-time feel)
        self.cache.register_cache_config(
            "dashboard:",
            CacheConfig(
                ttl=300,  # 5 minutes
                strategy=CacheStrategy.TTL,
                serialization=SerializationType.JSON,
                namespace="dashboard"
            )
        )
    
    async def initialize(self):
        """Initialize the cache manager"""
        await self.cache.initialize()
    
    # Memory system cache methods
    async def cache_memories(self, persona_id: str, query_hash: str, memories: List[Any]) -> bool:
        """Cache memory recall results"""
        key = f"memory:recall:{persona_id}:{query_hash}"
        return await self.cache.set(key, memories)
    
    async def get_cached_memories(self, persona_id: str, query_hash: str) -> Optional[List[Any]]:
        """Get cached memory recall results"""
        key = f"memory:recall:{persona_id}:{query_hash}"
        return await self.cache.get(key)
    
    # Knowledge graph cache methods
    async def cache_graph_traversal(self, node_id: str, params_hash: str, result: Dict[str, Any]) -> bool:
        """Cache graph traversal results"""
        key = f"knowledge:traversal:{node_id}:{params_hash}"
        return await self.cache.set(key, result)
    
    async def get_cached_graph_traversal(self, node_id: str, params_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached graph traversal results"""
        key = f"knowledge:traversal:{node_id}:{params_hash}"
        return await self.cache.get(key)
    
    # Project cache methods
    async def cache_project_data(self, project_id: str, data: Dict[str, Any]) -> bool:
        """Cache project dashboard data"""
        key = f"project:dashboard:{project_id}"
        return await self.cache.set(key, data)
    
    async def get_cached_project_data(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get cached project data"""
        key = f"project:dashboard:{project_id}"
        return await self.cache.get(key)
    
    # Analysis cache methods
    async def cache_analysis_results(self, project_id: str, analysis_type: str, results: Dict[str, Any]) -> bool:
        """Cache analysis results"""
        key = f"analysis:{project_id}:{analysis_type}"
        return await self.cache.set(key, results)
    
    async def get_cached_analysis(self, project_id: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis results"""
        key = f"analysis:{project_id}:{analysis_type}"
        return await self.cache.get(key)
    
    # Dashboard cache methods
    async def cache_dashboard_data(self, dashboard_type: str, data: Dict[str, Any]) -> bool:
        """Cache dashboard data"""
        key = f"dashboard:{dashboard_type}"
        return await self.cache.set(key, data)
    
    async def get_cached_dashboard_data(self, dashboard_type: str) -> Optional[Dict[str, Any]]:
        """Get cached dashboard data"""
        key = f"dashboard:{dashboard_type}"
        return await self.cache.get(key)
    
    # Invalidation methods
    async def invalidate_project_cache(self, project_id: str):
        """Invalidate all cache entries for a project"""
        await self.cache.invalidate_pattern(f"project:{project_id}:*")
        await self.cache.invalidate_pattern(f"analysis:{project_id}:*")
    
    async def invalidate_persona_cache(self, persona_id: str):
        """Invalidate all cache entries for a persona"""
        await self.cache.invalidate_pattern(f"memory:*:{persona_id}:*")
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return await self.cache.get_cache_info()
    
    async def health_check(self) -> bool:
        """Check cache health"""
        return await self.cache.health_check()
    
    async def close(self):
        """Close cache connections"""
        await self.cache.close()


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


async def initialize_cache():
    """Initialize the global cache manager"""
    cache_manager = get_cache_manager()
    await cache_manager.initialize()
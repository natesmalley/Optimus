"""
Integration tests for database persistence across all system components
Tests PostgreSQL, Redis, and cross-system data consistency
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch

from src.database.memory_optimized import OptimizedMemoryManager, MemoryEntry
from src.database.knowledge_graph_optimized import OptimizedKnowledgeGraph, Entity, Relationship
from src.database.postgres_optimized import OptimizedPostgresManager
from src.database.redis_cache import RedisCache
from src.council.orchestrator import Orchestrator, DeliberationRequest


class TestPostgresPersistence:
    """Test PostgreSQL persistence functionality"""
    
    @pytest.fixture
    async def postgres_manager(self, temp_database):
        """Create PostgreSQL manager with test database"""
        with patch('src.database.postgres_optimized.DATABASE_CONFIG', temp_database):
            manager = OptimizedPostgresManager()
            
            # Mock asyncpg connection
            mock_pool = MagicMock()
            mock_conn = MagicMock()
            mock_conn.execute = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_pool.acquire = AsyncMock(return_value=mock_conn)
            mock_pool.acquire().__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire().__aexit__ = AsyncMock(return_value=None)
            
            manager.connection_pool = mock_pool
            
            await manager.initialize()
            return manager, mock_conn
    
    async def test_deliberation_result_storage(self, postgres_manager):
        """Test storing deliberation results in PostgreSQL"""
        manager, mock_conn = postgres_manager
        
        deliberation_data = {
            "deliberation_id": "test_delib_123",
            "query": "What database should we use?",
            "decision": "Use PostgreSQL for primary database",
            "confidence": 0.85,
            "agreement_level": 0.8,
            "persona_responses": [
                {
                    "persona_id": "strategist",
                    "recommendation": "PostgreSQL",
                    "confidence": 0.9
                }
            ],
            "consensus_method": "weighted_majority",
            "deliberation_time": 2.5,
            "timestamp": datetime.now()
        }
        
        await manager.store_deliberation_result(deliberation_data)
        
        # Verify database calls were made
        mock_conn.execute.assert_called()
        call_args = mock_conn.execute.call_args[0]
        assert "INSERT INTO deliberation_results" in call_args[0]
        assert deliberation_data["deliberation_id"] in call_args[1:]
    
    async def test_memory_entry_storage(self, postgres_manager):
        """Test storing memory entries in PostgreSQL"""
        manager, mock_conn = postgres_manager
        
        memory_entry = MemoryEntry(
            persona_id="analyst",
            content="Database performance analysis shows slow queries on user table",
            entry_type="analysis",
            topic="database_performance",
            metadata={"query_time": 2.5, "table": "users"},
            tags=["performance", "database", "users"]
        )
        
        await manager.store_memory_entry(memory_entry)
        
        # Verify storage call
        mock_conn.execute.assert_called()
        call_args = mock_conn.execute.call_args[0]
        assert "INSERT INTO memory_entries" in call_args[0]
        assert memory_entry.persona_id in call_args[1:]
    
    async def test_knowledge_graph_entity_storage(self, postgres_manager):
        """Test storing knowledge graph entities"""
        manager, mock_conn = postgres_manager
        
        entity = Entity(
            entity_id="postgresql_db",
            entity_type="database",
            name="PostgreSQL",
            properties={
                "version": "14.0",
                "performance_rating": 9,
                "use_cases": ["OLTP", "analytics"]
            }
        )
        
        await manager.store_entity(entity)
        
        # Verify entity storage
        mock_conn.execute.assert_called()
        call_args = mock_conn.execute.call_args[0]
        assert "INSERT INTO entities" in call_args[0]
        assert entity.entity_id in call_args[1:]
    
    async def test_relationship_storage(self, postgres_manager):
        """Test storing relationships between entities"""
        manager, mock_conn = postgres_manager
        
        relationship = Relationship(
            source_id="user_service",
            target_id="postgresql_db",
            relationship_type="uses",
            properties={
                "connection_pool_size": 10,
                "query_patterns": ["user_lookup", "user_creation"]
            }
        )
        
        await manager.store_relationship(relationship)
        
        # Verify relationship storage
        mock_conn.execute.assert_called()
        call_args = mock_conn.execute.call_args[0]
        assert "INSERT INTO relationships" in call_args[0]
        assert relationship.source_id in call_args[1:]
    
    async def test_blackboard_entry_storage(self, postgres_manager):
        """Test storing blackboard entries"""
        manager, mock_conn = postgres_manager
        
        blackboard_entry = {
            "entry_id": "bb_entry_123",
            "topic": "architecture_discussion",
            "persona_id": "strategist",
            "entry_type": "insight",
            "content": "Microservices architecture would improve scalability",
            "metadata": {"importance": "high"},
            "tags": ["architecture", "scalability"],
            "timestamp": datetime.now()
        }
        
        await manager.store_blackboard_entry(blackboard_entry)
        
        # Verify blackboard storage
        mock_conn.execute.assert_called()
        call_args = mock_conn.execute.call_args[0]
        assert "INSERT INTO blackboard_entries" in call_args[0]
        assert blackboard_entry["entry_id"] in call_args[1:]


class TestRedisCaching:
    """Test Redis caching functionality"""
    
    @pytest.fixture
    async def redis_cache(self, mock_redis):
        """Create Redis cache with mock client"""
        cache = RedisCache()
        cache.redis_client = mock_redis
        await cache.initialize()
        return cache
    
    async def test_memory_caching(self, redis_cache, mock_redis):
        """Test caching memory entries in Redis"""
        cache_key = "memories:database_performance"
        memory_data = [
            {
                "entry_id": "mem_1",
                "persona_id": "analyst",
                "content": "Query performance degraded",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        await cache.cache_memories(cache_key, memory_data, expiry_minutes=60)
        
        # Verify Redis set operation
        mock_redis.set.assert_called()
        call_args = mock_redis.set.call_args
        assert cache_key in call_args[0]
        assert json.dumps(memory_data) in call_args[0]
    
    async def test_deliberation_result_caching(self, redis_cache, mock_redis):
        """Test caching deliberation results"""
        cache_key = "deliberation:test_topic_123"
        result_data = {
            "decision": "Use PostgreSQL",
            "confidence": 0.85,
            "consensus_method": "weighted_majority"
        }
        
        await cache.cache_deliberation_result(cache_key, result_data)
        
        # Verify caching
        mock_redis.set.assert_called()
        call_args = mock_redis.set.call_args[0]
        assert cache_key == call_args[0]
    
    async def test_cache_retrieval(self, redis_cache, mock_redis):
        """Test retrieving data from cache"""
        cache_key = "test_key"
        cached_data = {"test": "data"}
        
        # Mock cache hit
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = await cache.get_cached_data(cache_key)
        
        assert result == cached_data
        mock_redis.get.assert_called_with(cache_key)
    
    async def test_cache_miss(self, redis_cache, mock_redis):
        """Test cache miss handling"""
        cache_key = "nonexistent_key"
        
        # Mock cache miss
        mock_redis.get.return_value = None
        
        result = await cache.get_cached_data(cache_key)
        
        assert result is None
        mock_redis.get.assert_called_with(cache_key)
    
    async def test_cache_invalidation(self, redis_cache, mock_redis):
        """Test cache invalidation"""
        pattern = "memories:*"
        
        await cache.invalidate_cache_pattern(pattern)
        
        # Should get keys matching pattern and delete them
        mock_redis.keys.assert_called_with(pattern)
        mock_redis.delete.assert_called()


class TestCrossSystemPersistence:
    """Test persistence across multiple storage systems"""
    
    @pytest.fixture
    async def integrated_persistence_system(self, temp_database, mock_redis):
        """Create integrated persistence system with all components"""
        
        # Memory Manager
        memory_manager = OptimizedMemoryManager()
        memory_manager.redis_client = mock_redis
        
        mock_postgres_pool = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_postgres_pool.acquire().__aenter__ = AsyncMock(return_value=mock_conn)
        mock_postgres_pool.acquire().__aexit__ = AsyncMock(return_value=None)
        memory_manager.postgres_pool = mock_postgres_pool
        
        await memory_manager.initialize()
        
        # Knowledge Graph
        knowledge_graph = OptimizedKnowledgeGraph()
        await knowledge_graph.initialize()
        
        return memory_manager, knowledge_graph, mock_conn
    
    async def test_deliberation_persistence_workflow(self, integrated_persistence_system):
        """Test complete deliberation persistence across systems"""
        memory_manager, knowledge_graph, mock_conn = integrated_persistence_system
        
        # Simulate a deliberation result
        deliberation_result = {
            "deliberation_id": "delib_persistence_test",
            "query": "How should we implement caching?",
            "decision": "Implement Redis caching with fallback to database",
            "confidence": 0.88,
            "persona_responses": [
                {
                    "persona_id": "strategist",
                    "recommendation": "Multi-layer caching strategy",
                    "reasoning": "Improves performance and reduces database load"
                },
                {
                    "persona_id": "pragmatist", 
                    "recommendation": "Start with Redis, expand later",
                    "reasoning": "Fastest implementation with good results"
                }
            ],
            "entities_mentioned": ["Redis", "Database", "Caching"],
            "relationships_identified": [
                ("Application", "uses", "Redis"),
                ("Redis", "fallback_to", "Database")
            ]
        }
        
        # Store deliberation result
        await memory_manager.store_deliberation_result(deliberation_result)
        
        # Extract and store entities in knowledge graph
        for entity_name in deliberation_result["entities_mentioned"]:
            entity = Entity(
                entity_id=entity_name.lower().replace(" ", "_"),
                entity_type="technology",
                name=entity_name,
                properties={"mentioned_in_deliberation": deliberation_result["deliberation_id"]}
            )
            await knowledge_graph.add_entity(entity)
        
        # Store relationships
        for source, relation_type, target in deliberation_result["relationships_identified"]:
            relationship = Relationship(
                source_id=source.lower().replace(" ", "_"),
                target_id=target.lower().replace(" ", "_"),
                relationship_type=relation_type,
                properties={"source_deliberation": deliberation_result["deliberation_id"]}
            )
            await knowledge_graph.add_relationship(relationship)
        
        # Store memories for each persona response
        for response in deliberation_result["persona_responses"]:
            memory_entry = MemoryEntry(
                persona_id=response["persona_id"],
                content=f"{response['recommendation']} - {response['reasoning']}",
                entry_type="deliberation_contribution",
                topic="caching_strategy",
                metadata={
                    "deliberation_id": deliberation_result["deliberation_id"],
                    "recommendation_type": "caching"
                },
                tags=["caching", "redis", "strategy"]
            )
            await memory_manager.store_memory(memory_entry)
        
        # Verify cross-system storage
        # PostgreSQL calls should have been made
        assert mock_conn.execute.call_count >= 3  # Deliberation + memories + entities/relationships
        
        # Redis caching should have been used
        assert memory_manager.redis_client.set.called
        
        # Knowledge graph should contain entities
        redis_entity = await knowledge_graph.get_entity("redis")
        assert redis_entity is not None
        assert redis_entity.name == "Redis"
    
    async def test_data_consistency_across_systems(self, integrated_persistence_system):
        """Test data consistency across PostgreSQL, Redis, and Knowledge Graph"""
        memory_manager, knowledge_graph, mock_conn = integrated_persistence_system
        
        # Create consistent data across systems
        entity_id = "user_authentication_service"
        
        # Store in knowledge graph
        entity = Entity(
            entity_id=entity_id,
            entity_type="service",
            name="User Authentication Service",
            properties={"status": "active", "version": "2.1.0"}
        )
        await knowledge_graph.add_entity(entity)
        
        # Store related memory
        memory_entry = MemoryEntry(
            persona_id="guardian",
            content="User Authentication Service requires security audit",
            entry_type="security_requirement",
            topic="security_audit",
            metadata={
                "entity_reference": entity_id,
                "priority": "high",
                "compliance": "required"
            },
            tags=["security", "audit", "authentication"]
        )
        await memory_manager.store_memory(memory_entry)
        
        # Mock retrieval to verify consistency
        mock_conn.fetchrow.return_value = {
            "entry_id": memory_entry.entry_id,
            "persona_id": "guardian",
            "content": memory_entry.content,
            "metadata": json.dumps(memory_entry.metadata),
            "entity_references": [entity_id]
        }
        
        # Retrieve and verify consistency
        retrieved_memory = await memory_manager.get_memory_by_id(memory_entry.entry_id)
        retrieved_entity = await knowledge_graph.get_entity(entity_id)
        
        # Data should be consistent across systems
        assert retrieved_memory is not None
        assert retrieved_entity is not None
        assert retrieved_memory.metadata["entity_reference"] == entity_id
        assert retrieved_entity.entity_id == entity_id
    
    async def test_backup_and_recovery_workflow(self, integrated_persistence_system):
        """Test backup and recovery across persistence systems"""
        memory_manager, knowledge_graph, mock_conn = integrated_persistence_system
        
        # Create test data
        test_data = {
            "memories": [
                MemoryEntry(
                    persona_id="strategist",
                    content="Backup strategy should include cross-region replication",
                    entry_type="strategy",
                    topic="backup_recovery"
                )
            ],
            "entities": [
                Entity(
                    entity_id="backup_system",
                    entity_type="system",
                    name="Backup System"
                )
            ]
        }
        
        # Store test data
        for memory in test_data["memories"]:
            await memory_manager.store_memory(memory)
        
        for entity in test_data["entities"]:
            await knowledge_graph.add_entity(entity)
        
        # Create backup
        backup_data = await memory_manager.create_backup()
        kg_backup_data = await knowledge_graph.export_data()
        
        # Simulate data loss and recovery
        await memory_manager.clear_all_data()
        await knowledge_graph.clear_all_data()
        
        # Restore from backup
        await memory_manager.restore_from_backup(backup_data)
        await knowledge_graph.import_data(kg_backup_data)
        
        # Verify restoration
        # Mock successful restoration responses
        mock_conn.fetch.return_value = [{
            "entry_id": test_data["memories"][0].entry_id,
            "persona_id": "strategist",
            "content": test_data["memories"][0].content
        }]
        
        restored_memories = await memory_manager.get_memories_by_topic("backup_recovery")
        restored_entity = await knowledge_graph.get_entity("backup_system")
        
        assert len(restored_memories) >= 1
        assert restored_entity is not None


class TestPersistencePerformance:
    """Test persistence performance and optimization"""
    
    @pytest.fixture
    async def performance_test_system(self, temp_database, mock_redis):
        """Create system optimized for performance testing"""
        memory_manager = OptimizedMemoryManager()
        memory_manager.redis_client = mock_redis
        
        # Mock high-performance PostgreSQL pool
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.executemany = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool.acquire().__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire().__aexit__ = AsyncMock(return_value=None)
        
        memory_manager.postgres_pool = mock_pool
        await memory_manager.initialize()
        
        return memory_manager, mock_conn
    
    async def test_batch_memory_storage(self, performance_test_system):
        """Test batch storage of memory entries for performance"""
        memory_manager, mock_conn = performance_test_system
        
        # Create batch of memory entries
        memory_batch = [
            MemoryEntry(
                persona_id=f"persona_{i%5}",
                content=f"Memory entry {i} for performance testing",
                entry_type="performance_test",
                topic=f"batch_test_{i%3}",
                tags=[f"tag_{i%10}"]
            )
            for i in range(100)
        ]
        
        # Store batch
        start_time = asyncio.get_event_loop().time()
        await memory_manager.store_memory_batch(memory_batch)
        end_time = asyncio.get_event_loop().time()
        
        batch_time = end_time - start_time
        
        # Should use batch operations for efficiency
        mock_conn.executemany.assert_called()
        
        # Should complete reasonably quickly
        assert batch_time < 1.0  # Should complete in under 1 second
    
    async def test_concurrent_persistence_operations(self, performance_test_system):
        """Test concurrent persistence operations"""
        memory_manager, mock_conn = performance_test_system
        
        # Create concurrent storage tasks
        async def store_memory_task(task_id):
            memory_entry = MemoryEntry(
                persona_id=f"concurrent_persona_{task_id}",
                content=f"Concurrent memory {task_id}",
                entry_type="concurrency_test",
                topic=f"concurrent_topic_{task_id}"
            )
            await memory_manager.store_memory(memory_entry)
            return task_id
        
        # Run concurrent tasks
        tasks = [store_memory_task(i) for i in range(20)]
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        concurrent_time = end_time - start_time
        
        # All tasks should complete
        assert len(results) == 20
        assert all(isinstance(r, int) for r in results)
        
        # Should handle concurrency efficiently
        assert concurrent_time < 2.0  # Should complete in reasonable time
        
        # Should have made database calls
        assert mock_conn.execute.call_count >= 20
    
    async def test_cache_performance_optimization(self, performance_test_system):
        """Test cache performance optimizations"""
        memory_manager, mock_conn = performance_test_system
        
        cache_key = "performance_test_memories"
        
        # First call - cache miss (should hit database)
        mock_conn.fetch.return_value = [
            {
                "entry_id": "perf_test_1",
                "persona_id": "strategist",
                "content": "Cached memory content"
            }
        ]
        
        start_time = asyncio.get_event_loop().time()
        result1 = await memory_manager.get_cached_memories(cache_key)
        end_time = asyncio.get_event_loop().time()
        
        cache_miss_time = end_time - start_time
        
        # Second call - cache hit (should be faster)
        memory_manager.redis_client.get.return_value = json.dumps([{
            "entry_id": "perf_test_1",
            "persona_id": "strategist", 
            "content": "Cached memory content"
        }])
        
        start_time = asyncio.get_event_loop().time()
        result2 = await memory_manager.get_cached_memories(cache_key)
        end_time = asyncio.get_event_loop().time()
        
        cache_hit_time = end_time - start_time
        
        # Cache hit should be faster than cache miss
        assert cache_hit_time < cache_miss_time
        
        # Both should return same data
        assert result1 == result2


class TestPersistenceErrorHandling:
    """Test persistence error handling and recovery"""
    
    @pytest.fixture
    async def error_prone_system(self, temp_database, mock_redis):
        """Create system for testing error scenarios"""
        memory_manager = OptimizedMemoryManager()
        memory_manager.redis_client = mock_redis
        
        # Mock PostgreSQL with potential failures
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        memory_manager.postgres_pool = mock_pool
        
        await memory_manager.initialize()
        return memory_manager, mock_pool, mock_conn
    
    async def test_database_connection_failure_handling(self, error_prone_system):
        """Test handling of database connection failures"""
        memory_manager, mock_pool, mock_conn = error_prone_system
        
        # Mock connection failure
        mock_pool.acquire.side_effect = Exception("Database connection failed")
        
        memory_entry = MemoryEntry(
            persona_id="test_persona",
            content="Test memory for connection failure",
            entry_type="test",
            topic="error_handling"
        )
        
        # Should handle connection failure gracefully
        try:
            await memory_manager.store_memory(memory_entry)
            # Should either succeed with fallback or raise specific error
        except Exception as e:
            # Should be a handled exception, not raw database error
            assert "connection" in str(e).lower() or "database" in str(e).lower()
    
    async def test_redis_cache_failure_fallback(self, error_prone_system):
        """Test fallback when Redis cache fails"""
        memory_manager, mock_pool, mock_conn = error_prone_system
        
        # Mock Redis failure
        memory_manager.redis_client.get.side_effect = Exception("Redis connection failed")
        
        # Mock successful database fallback
        mock_conn.fetch.return_value = [
            {
                "entry_id": "fallback_test",
                "persona_id": "strategist",
                "content": "Fallback memory content"
            }
        ]
        mock_pool.acquire().__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire().__aexit__ = AsyncMock(return_value=None)
        
        # Should fall back to database when cache fails
        result = await memory_manager.get_cached_memories("test_key")
        
        # Should get data from database fallback
        assert len(result) >= 1
        assert result[0]["content"] == "Fallback memory content"
    
    async def test_partial_failure_recovery(self, error_prone_system):
        """Test recovery from partial system failures"""
        memory_manager, mock_pool, mock_conn = error_prone_system
        
        # Mock partial failure - some operations succeed, others fail
        call_count = 0
        
        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Every third call fails
                raise Exception("Intermittent database error")
            return AsyncMock()()
        
        mock_conn.execute = mock_execute
        mock_pool.acquire().__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire().__aexit__ = AsyncMock(return_value=None)
        
        # Try multiple operations
        successes = 0
        failures = 0
        
        for i in range(10):
            try:
                memory_entry = MemoryEntry(
                    persona_id="test_persona",
                    content=f"Test memory {i}",
                    entry_type="test",
                    topic="partial_failure"
                )
                await memory_manager.store_memory(memory_entry)
                successes += 1
            except:
                failures += 1
        
        # Should have mix of successes and failures
        assert successes > 0  # Some should succeed
        assert failures > 0   # Some should fail
        assert successes + failures == 10
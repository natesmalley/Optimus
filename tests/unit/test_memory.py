"""
Unit tests for memory system and knowledge graph operations
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch
import json

from src.database.memory_optimized import OptimizedMemoryManager, MemoryEntry, MemoryQueryType
from src.database.knowledge_graph_optimized import OptimizedKnowledgeGraph, Entity, Relationship


class TestMemoryEntry:
    """Test MemoryEntry data structure"""
    
    def test_memory_entry_creation(self):
        """Test creating a valid memory entry"""
        entry = MemoryEntry(
            persona_id="strategist",
            content="Microservices architecture decision for user service",
            entry_type="decision",
            topic="architecture",
            metadata={
                "decision_confidence": 0.85,
                "stakeholders": ["backend_team", "devops_team"],
                "timeline": "Q2_2024"
            },
            tags=["microservices", "architecture", "user_service"]
        )
        
        assert entry.persona_id == "strategist"
        assert entry.content == "Microservices architecture decision for user service"
        assert entry.entry_type == "decision"
        assert entry.topic == "architecture"
        assert entry.metadata["decision_confidence"] == 0.85
        assert "microservices" in entry.tags
        assert entry.timestamp is not None
        assert entry.entry_id is not None
    
    def test_memory_entry_validation(self):
        """Test memory entry validation"""
        # Test empty content
        with pytest.raises(ValueError):
            MemoryEntry(
                persona_id="test",
                content="",  # Empty content
                entry_type="insight",
                topic="test"
            )
        
        # Test empty persona_id
        with pytest.raises(ValueError):
            MemoryEntry(
                persona_id="",  # Empty persona_id
                content="Valid content",
                entry_type="insight",
                topic="test"
            )
    
    def test_memory_entry_serialization(self):
        """Test memory entry serialization"""
        entry = MemoryEntry(
            persona_id="analyst",
            content="Database performance analysis shows bottleneck in user queries",
            entry_type="analysis",
            topic="performance",
            metadata={"query_time": 2.5, "table": "users", "index_recommendation": "user_email_idx"},
            tags=["performance", "database", "optimization"]
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict["persona_id"] == "analyst"
        assert entry_dict["content"] == "Database performance analysis shows bottleneck in user queries"
        assert entry_dict["entry_type"] == "analysis"
        assert entry_dict["metadata"]["query_time"] == 2.5
        assert "performance" in entry_dict["tags"]
        assert "timestamp" in entry_dict
    
    def test_memory_entry_from_dict(self):
        """Test creating memory entry from dictionary"""
        entry_data = {
            "entry_id": "test_id_123",
            "persona_id": "innovator",
            "content": "New AI integration opportunity identified",
            "entry_type": "opportunity",
            "topic": "innovation",
            "metadata": {"feasibility": 0.7, "impact": 0.9},
            "tags": ["AI", "integration", "opportunity"],
            "timestamp": datetime.now().isoformat()
        }
        
        entry = MemoryEntry.from_dict(entry_data)
        
        assert entry.entry_id == "test_id_123"
        assert entry.persona_id == "innovator"
        assert entry.content == "New AI integration opportunity identified"
        assert entry.metadata["feasibility"] == 0.7
        assert "AI" in entry.tags


class TestOptimizedMemoryManager:
    """Test OptimizedMemoryManager functionality"""
    
    @pytest.fixture
    async def memory_manager(self, temp_database, mock_redis, mock_postgres):
        """Create memory manager with mocked dependencies"""
        with patch('src.database.memory_optimized.DATABASE_CONFIG', temp_database):
            manager = OptimizedMemoryManager()
            manager.redis_client = mock_redis
            manager.postgres_pool = mock_postgres
            await manager.initialize()
            return manager
    
    async def test_memory_manager_initialization(self, memory_manager):
        """Test memory manager initialization"""
        assert memory_manager.is_initialized is True
        assert memory_manager.redis_client is not None
        assert memory_manager.postgres_pool is not None
    
    async def test_store_memory_entry(self, memory_manager, mock_redis, mock_postgres):
        """Test storing memory entry"""
        entry = MemoryEntry(
            persona_id="strategist",
            content="Key architectural decision about database choice",
            entry_type="decision",
            topic="architecture"
        )
        
        await memory_manager.store_memory(entry)
        
        # Verify Redis cache was updated
        mock_redis.set.assert_called()
        
        # Verify PostgreSQL storage was called
        mock_postgres.execute.assert_called()
    
    async def test_retrieve_memories(self, memory_manager, mock_postgres):
        """Test retrieving memories by topic"""
        # Mock database response
        mock_postgres.fetch.return_value = [
            {
                "entry_id": "test_1",
                "persona_id": "strategist", 
                "content": "First memory",
                "entry_type": "decision",
                "topic": "architecture",
                "metadata": json.dumps({}),
                "tags": json.dumps(["architecture"]),
                "timestamp": datetime.now()
            },
            {
                "entry_id": "test_2",
                "persona_id": "analyst",
                "content": "Second memory",
                "entry_type": "analysis",
                "topic": "architecture", 
                "metadata": json.dumps({}),
                "tags": json.dumps(["performance"]),
                "timestamp": datetime.now()
            }
        ]
        
        memories = await memory_manager.retrieve_memories("architecture", limit=10)
        
        assert len(memories) == 2
        assert memories[0].persona_id == "strategist"
        assert memories[1].persona_id == "analyst"
        mock_postgres.fetch.assert_called()
    
    async def test_search_memories(self, memory_manager, mock_postgres):
        """Test searching memories by content"""
        # Mock search results
        mock_postgres.fetch.return_value = [
            {
                "entry_id": "search_1",
                "persona_id": "strategist",
                "content": "Database optimization strategies for high-traffic applications",
                "entry_type": "strategy",
                "topic": "performance",
                "metadata": json.dumps({"relevance": 0.95}),
                "tags": json.dumps(["database", "performance", "optimization"]),
                "timestamp": datetime.now(),
                "similarity_score": 0.85
            }
        ]
        
        results = await memory_manager.search_memories(
            query="database optimization",
            limit=5,
            min_relevance=0.7
        )
        
        assert len(results) == 1
        assert "database optimization" in results[0].content.lower()
        mock_postgres.fetch.assert_called()
    
    async def test_memory_clustering(self, memory_manager):
        """Test memory clustering by topic and content"""
        memories = [
            MemoryEntry(
                persona_id="strategist",
                content="Authentication system design decisions",
                entry_type="decision",
                topic="security",
                tags=["authentication", "security"]
            ),
            MemoryEntry(
                persona_id="guardian",
                content="Security vulnerability assessment results",
                entry_type="assessment",
                topic="security",
                tags=["security", "vulnerability"]
            ),
            MemoryEntry(
                persona_id="analyst",
                content="Performance metrics for authentication service",
                entry_type="metrics",
                topic="performance",
                tags=["authentication", "performance"]
            )
        ]
        
        clusters = await memory_manager.cluster_memories(memories, cluster_count=2)
        
        assert len(clusters) <= 2
        assert all(isinstance(cluster, list) for cluster in clusters)
        # Memories should be grouped by similarity
    
    async def test_memory_summarization(self, memory_manager):
        """Test summarizing related memories"""
        related_memories = [
            MemoryEntry(
                persona_id="strategist",
                content="Chose PostgreSQL for primary database",
                entry_type="decision",
                topic="database"
            ),
            MemoryEntry(
                persona_id="analyst",
                content="PostgreSQL performance tests show good results",
                entry_type="analysis",
                topic="database"
            ),
            MemoryEntry(
                persona_id="pragmatist",
                content="PostgreSQL migration completed successfully",
                entry_type="update",
                topic="database"
            )
        ]
        
        summary = await memory_manager.summarize_memories(
            related_memories,
            focus_areas=["decisions", "outcomes", "performance"]
        )
        
        assert isinstance(summary, dict)
        assert "key_decisions" in summary
        assert "outcomes" in summary
        assert "postgresql" in summary["summary_text"].lower()
    
    async def test_memory_expiration(self, memory_manager, mock_redis, mock_postgres):
        """Test memory expiration and cleanup"""
        # Mock expired memories
        mock_postgres.fetch.return_value = [
            {
                "entry_id": "expired_1",
                "timestamp": datetime.now() - timedelta(days=365)  # Old memory
            }
        ]
        
        expired_count = await memory_manager.cleanup_expired_memories(max_age_days=180)
        
        assert isinstance(expired_count, int)
        # Should have called delete operations
        mock_postgres.execute.assert_called()
    
    async def test_memory_cache_management(self, memory_manager, mock_redis):
        """Test Redis cache management"""
        # Test cache hit
        mock_redis.get.return_value = json.dumps([{
            "entry_id": "cached_1",
            "persona_id": "strategist",
            "content": "Cached memory",
            "entry_type": "decision",
            "topic": "cache_test",
            "metadata": {},
            "tags": [],
            "timestamp": datetime.now().isoformat()
        }])
        
        memories = await memory_manager.get_cached_memories("cache_test")
        
        assert len(memories) == 1
        assert memories[0].content == "Cached memory"
        mock_redis.get.assert_called()
    
    async def test_memory_statistics(self, memory_manager, mock_postgres):
        """Test memory statistics generation"""
        # Mock statistics query results
        mock_postgres.fetchrow.return_value = {
            "total_memories": 1500,
            "unique_personas": 13,
            "unique_topics": 25,
            "avg_memories_per_day": 12.5
        }
        
        stats = await memory_manager.get_memory_statistics()
        
        assert stats["total_memories"] == 1500
        assert stats["unique_personas"] == 13
        assert stats["unique_topics"] == 25
        assert stats["avg_memories_per_day"] == 12.5


class TestOptimizedKnowledgeGraph:
    """Test OptimizedKnowledgeGraph functionality"""
    
    @pytest.fixture
    async def knowledge_graph(self, temp_database):
        """Create knowledge graph with temporary storage"""
        with patch('src.database.knowledge_graph_optimized.DATABASE_CONFIG', temp_database):
            kg = OptimizedKnowledgeGraph()
            await kg.initialize()
            return kg
    
    async def test_knowledge_graph_initialization(self, knowledge_graph):
        """Test knowledge graph initialization"""
        assert knowledge_graph.is_initialized is True
        assert knowledge_graph.graph is not None
    
    async def test_add_entity(self, knowledge_graph):
        """Test adding entities to knowledge graph"""
        entity = Entity(
            entity_id="postgresql_db",
            entity_type="database",
            name="PostgreSQL",
            properties={
                "type": "relational",
                "version": "14.0",
                "performance_rating": 9,
                "use_cases": ["OLTP", "analytics"]
            }
        )
        
        await knowledge_graph.add_entity(entity)
        
        # Verify entity was added
        retrieved = await knowledge_graph.get_entity("postgresql_db")
        assert retrieved is not None
        assert retrieved.name == "PostgreSQL"
        assert retrieved.properties["version"] == "14.0"
    
    async def test_add_relationship(self, knowledge_graph):
        """Test adding relationships between entities"""
        # Add entities first
        db_entity = Entity("postgresql_db", "database", "PostgreSQL")
        app_entity = Entity("user_service", "service", "User Service")
        
        await knowledge_graph.add_entity(db_entity)
        await knowledge_graph.add_entity(app_entity)
        
        # Add relationship
        relationship = Relationship(
            source_id="user_service",
            target_id="postgresql_db",
            relationship_type="uses",
            properties={
                "connection_pool_size": 10,
                "query_patterns": ["user_lookup", "user_creation"],
                "performance_impact": "low"
            }
        )
        
        await knowledge_graph.add_relationship(relationship)
        
        # Verify relationship
        relationships = await knowledge_graph.get_entity_relationships("user_service")
        assert len(relationships) >= 1
        assert any(r.target_id == "postgresql_db" for r in relationships)
    
    async def test_query_entities_by_type(self, knowledge_graph):
        """Test querying entities by type"""
        # Add multiple entities of different types
        entities = [
            Entity("service1", "service", "Auth Service"),
            Entity("service2", "service", "Payment Service"),
            Entity("db1", "database", "PostgreSQL"),
            Entity("cache1", "cache", "Redis")
        ]
        
        for entity in entities:
            await knowledge_graph.add_entity(entity)
        
        # Query services
        services = await knowledge_graph.query_entities_by_type("service")
        assert len(services) == 2
        assert all(e.entity_type == "service" for e in services)
        
        # Query databases
        databases = await knowledge_graph.query_entities_by_type("database")
        assert len(databases) == 1
        assert databases[0].name == "PostgreSQL"
    
    async def test_find_path_between_entities(self, knowledge_graph):
        """Test finding paths between entities"""
        # Create a graph: User -> Auth Service -> Database
        entities = [
            Entity("user", "actor", "User"),
            Entity("auth_service", "service", "Auth Service"),
            Entity("user_db", "database", "User Database")
        ]
        
        relationships = [
            Relationship("user", "auth_service", "authenticates_with"),
            Relationship("auth_service", "user_db", "queries")
        ]
        
        for entity in entities:
            await knowledge_graph.add_entity(entity)
        
        for relationship in relationships:
            await knowledge_graph.add_relationship(relationship)
        
        # Find path
        path = await knowledge_graph.find_path("user", "user_db", max_depth=3)
        
        assert path is not None
        assert len(path) >= 2  # At least user -> auth_service -> user_db
        assert path[0] == "user"
        assert path[-1] == "user_db"
    
    async def test_entity_neighbors(self, knowledge_graph):
        """Test finding neighboring entities"""
        # Create connected entities
        center_entity = Entity("api_gateway", "service", "API Gateway")
        connected_entities = [
            Entity("auth_service", "service", "Auth Service"),
            Entity("user_service", "service", "User Service"),
            Entity("load_balancer", "infrastructure", "Load Balancer")
        ]
        
        await knowledge_graph.add_entity(center_entity)
        for entity in connected_entities:
            await knowledge_graph.add_entity(entity)
        
        # Add relationships
        relationships = [
            Relationship("api_gateway", "auth_service", "routes_to"),
            Relationship("api_gateway", "user_service", "routes_to"),
            Relationship("load_balancer", "api_gateway", "forwards_to")
        ]
        
        for relationship in relationships:
            await knowledge_graph.add_relationship(relationship)
        
        # Get neighbors
        neighbors = await knowledge_graph.get_neighbors("api_gateway")
        
        assert len(neighbors) >= 2
        neighbor_ids = [n.entity_id for n in neighbors]
        assert "auth_service" in neighbor_ids
        assert "user_service" in neighbor_ids
    
    async def test_graph_statistics(self, knowledge_graph):
        """Test knowledge graph statistics"""
        # Add sample data
        entities = [
            Entity(f"entity_{i}", "type_" + str(i % 3), f"Entity {i}")
            for i in range(10)
        ]
        
        for entity in entities:
            await knowledge_graph.add_entity(entity)
        
        # Add some relationships
        for i in range(5):
            relationship = Relationship(
                f"entity_{i}",
                f"entity_{i+1}",
                "connected_to"
            )
            await knowledge_graph.add_relationship(relationship)
        
        stats = await knowledge_graph.get_statistics()
        
        assert stats["total_entities"] == 10
        assert stats["total_relationships"] >= 5
        assert "entity_types" in stats
        assert "relationship_types" in stats
    
    async def test_subgraph_extraction(self, knowledge_graph):
        """Test extracting subgraphs"""
        # Create a larger graph structure
        entities = [
            Entity("web_app", "application", "Web Application"),
            Entity("api", "service", "REST API"),
            Entity("database", "database", "PostgreSQL"),
            Entity("cache", "cache", "Redis"),
            Entity("user", "actor", "End User")
        ]
        
        relationships = [
            Relationship("user", "web_app", "uses"),
            Relationship("web_app", "api", "calls"),
            Relationship("api", "database", "queries"),
            Relationship("api", "cache", "caches_in")
        ]
        
        for entity in entities:
            await knowledge_graph.add_entity(entity)
        for relationship in relationships:
            await knowledge_graph.add_relationship(relationship)
        
        # Extract subgraph around API
        subgraph = await knowledge_graph.extract_subgraph("api", max_distance=2)
        
        assert "api" in subgraph["entities"]
        assert len(subgraph["entities"]) >= 3  # API + connected entities
        assert len(subgraph["relationships"]) >= 2
    
    async def test_entity_similarity(self, knowledge_graph):
        """Test entity similarity calculations"""
        # Add similar entities
        similar_entities = [
            Entity("postgres_main", "database", "PostgreSQL Main", {
                "type": "relational", "version": "14", "use_case": "OLTP"
            }),
            Entity("postgres_analytics", "database", "PostgreSQL Analytics", {
                "type": "relational", "version": "14", "use_case": "OLAP"
            }),
            Entity("redis_cache", "cache", "Redis Cache", {
                "type": "key_value", "version": "6", "use_case": "caching"
            })
        ]
        
        for entity in similar_entities:
            await knowledge_graph.add_entity(entity)
        
        # Calculate similarity
        similarity = await knowledge_graph.calculate_entity_similarity(
            "postgres_main", 
            "postgres_analytics"
        )
        
        assert 0 <= similarity <= 1
        assert similarity > 0.5  # Should be similar (both PostgreSQL databases)
        
        # Compare with different type
        diff_similarity = await knowledge_graph.calculate_entity_similarity(
            "postgres_main",
            "redis_cache"
        )
        
        assert diff_similarity < similarity  # Should be less similar


class TestMemoryKnowledgeGraphIntegration:
    """Test integration between memory system and knowledge graph"""
    
    @pytest.fixture
    async def integrated_system(self, temp_database, mock_redis, mock_postgres):
        """Create integrated memory and knowledge graph system"""
        with patch('src.database.memory_optimized.DATABASE_CONFIG', temp_database):
            memory_manager = OptimizedMemoryManager()
            memory_manager.redis_client = mock_redis
            memory_manager.postgres_pool = mock_postgres
            await memory_manager.initialize()
        
        with patch('src.database.knowledge_graph_optimized.DATABASE_CONFIG', temp_database):
            knowledge_graph = OptimizedKnowledgeGraph()
            await knowledge_graph.initialize()
        
        return memory_manager, knowledge_graph
    
    async def test_memory_to_knowledge_graph_extraction(self, integrated_system):
        """Test extracting knowledge graph entities from memories"""
        memory_manager, knowledge_graph = integrated_system
        
        memory_entry = MemoryEntry(
            persona_id="strategist",
            content="We decided to use PostgreSQL as our primary database and Redis for caching",
            entry_type="decision",
            topic="architecture",
            metadata={
                "entities_mentioned": ["PostgreSQL", "Redis"],
                "relationships": [("Application", "uses", "PostgreSQL"), ("Application", "caches_in", "Redis")]
            }
        )
        
        # Extract entities from memory
        entities = await memory_manager.extract_entities_from_memory(memory_entry)
        
        assert len(entities) >= 2
        entity_names = [e.name for e in entities]
        assert "PostgreSQL" in entity_names
        assert "Redis" in entity_names
        
        # Add to knowledge graph
        for entity in entities:
            await knowledge_graph.add_entity(entity)
        
        # Verify entities in graph
        pg_entity = await knowledge_graph.get_entity_by_name("PostgreSQL")
        assert pg_entity is not None
        assert pg_entity.entity_type in ["database", "technology"]
    
    async def test_knowledge_graph_enhanced_memory_retrieval(self, integrated_system):
        """Test using knowledge graph to enhance memory retrieval"""
        memory_manager, knowledge_graph = integrated_system
        
        # Add related entities to knowledge graph
        entities = [
            Entity("postgresql", "database", "PostgreSQL"),
            Entity("redis", "cache", "Redis"), 
            Entity("performance", "concept", "Performance"),
        ]
        
        relationships = [
            Relationship("postgresql", "performance", "impacts"),
            Relationship("redis", "performance", "improves")
        ]
        
        for entity in entities:
            await knowledge_graph.add_entity(entity)
        for relationship in relationships:
            await knowledge_graph.add_relationship(relationship)
        
        # Mock related memories
        mock_postgres = memory_manager.postgres_pool
        mock_postgres.fetch.return_value = [
            {
                "entry_id": "mem_1",
                "persona_id": "strategist",
                "content": "PostgreSQL performance optimization completed",
                "entry_type": "update",
                "topic": "performance",
                "metadata": json.dumps({}),
                "tags": json.dumps(["postgresql", "performance"]),
                "timestamp": datetime.now()
            }
        ]
        
        # Retrieve memories enhanced with graph context
        memories = await memory_manager.retrieve_memories_with_graph_context(
            "performance",
            knowledge_graph,
            expand_related=True
        )
        
        assert len(memories) >= 1
        assert "postgresql" in memories[0].content.lower()
    
    async def test_cross_system_consistency(self, integrated_system):
        """Test consistency between memory and knowledge graph systems"""
        memory_manager, knowledge_graph = integrated_system
        
        # Store decision in memory
        decision_memory = MemoryEntry(
            persona_id="strategist",
            content="Adopted microservices architecture with API Gateway pattern",
            entry_type="decision",
            topic="architecture",
            metadata={
                "confidence": 0.85,
                "impact": "high",
                "entities": ["microservices", "API_Gateway"]
            }
        )
        
        await memory_manager.store_memory(decision_memory)
        
        # Extract and store entities in knowledge graph
        api_gateway = Entity("api_gateway", "pattern", "API Gateway Pattern")
        microservices = Entity("microservices", "architecture", "Microservices Architecture")
        
        await knowledge_graph.add_entity(api_gateway)
        await knowledge_graph.add_entity(microservices)
        
        # Add relationship
        relationship = Relationship("microservices", "api_gateway", "implements")
        await knowledge_graph.add_relationship(relationship)
        
        # Verify cross-system queries work
        # 1. Get memories related to microservices
        mock_postgres = memory_manager.postgres_pool
        mock_postgres.fetch.return_value = [{
            "entry_id": decision_memory.entry_id,
            "persona_id": "strategist",
            "content": decision_memory.content,
            "entry_type": "decision",
            "topic": "architecture",
            "metadata": json.dumps(decision_memory.metadata),
            "tags": json.dumps(decision_memory.tags),
            "timestamp": datetime.now()
        }]
        
        memories = await memory_manager.search_memories("microservices")
        assert len(memories) >= 1
        
        # 2. Get entities related to architecture
        entities = await knowledge_graph.query_entities_by_type("architecture")
        assert len(entities) >= 1
        assert any(e.name == "Microservices Architecture" for e in entities)
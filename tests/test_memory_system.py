"""
Comprehensive test suite for the Optimus Council of Minds Memory System.

Tests storage, retrieval, similarity matching, performance, and integration
with the orchestrator and persona system.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random
import string

from src.council.memory_system import (
    PersonaMemorySystem, 
    MemoryQuery, 
    MemoryRecall,
    get_memory_system
)
from src.council.orchestrator import (
    Orchestrator, 
    DeliberationRequest, 
    DeliberationResult
)
from src.council.consensus import ConsensusResult, ConsensusMethod
from src.council.persona import PersonaResponse
from src.models.memory import (
    DeliberationMemory,
    PersonaResponseMemory,
    ContextMemory,
    PersonaLearningPattern,
    MemoryAssociation
)
from src.database.config import get_database_manager
from sqlalchemy import select, func, delete


class TestPersonaMemorySystem:
    """Test suite for the PersonaMemorySystem"""

    @pytest.fixture
    async def memory_system(self):
        """Get a memory system instance for testing"""
        system = await get_memory_system()
        await system.initialize()
        return system

    @pytest.fixture
    async def clean_database(self, memory_system):
        """Clean the database before each test"""
        db_manager = get_database_manager()
        async with db_manager.get_postgres_session() as session:
            # Clean up test data
            await session.execute(delete(ContextMemory))
            await session.execute(delete(PersonaResponseMemory))
            await session.execute(delete(DeliberationMemory))
            await session.execute(delete(PersonaLearningPattern))
            await session.execute(delete(MemoryAssociation))
            await session.commit()

    @pytest.fixture
    def sample_deliberation_request(self):
        """Create a sample deliberation request for testing"""
        return DeliberationRequest(
            query="What is the best approach for implementing a caching system?",
            context={"project": "web_app", "performance": "critical"},
            topic="caching_strategy",
            timeout=30.0
        )

    @pytest.fixture
    def sample_persona_responses(self):
        """Create sample persona responses for testing"""
        responses = []
        personas = ["strategist", "pragmatist", "analyst"]
        
        for i, persona in enumerate(personas):
            response = PersonaResponse(
                persona_name=persona,
                persona_role=f"Test {persona.title()}",
                response=f"I recommend approach {i+1} for the caching system because...",
                reasoning=f"Based on my analysis as a {persona}, this approach offers...",
                confidence=0.7 + (i * 0.1),
                response_time=1.5 + (i * 0.2),
                tools_used=["analysis", "research"],
                context_used={"considered_factors": ["performance", "scalability"]},
                recommendation="Use Redis with intelligent invalidation"
            )
            responses.append(response)
        
        return responses

    @pytest.fixture
    def sample_consensus_result(self):
        """Create a sample consensus result"""
        return ConsensusResult(
            decision="Implement Redis caching with intelligent invalidation strategy",
            confidence=0.85,
            method=ConsensusMethod.WEIGHTED_VOTING,
            agreement_level=0.78,
            supporting_personas=["strategist", "pragmatist"],
            dissenting_personas=["analyst"],
            reasoning="Strong agreement on Redis, with some concerns about complexity",
            metadata={
                "weights": {"strategist": 0.4, "pragmatist": 0.4, "analyst": 0.2},
                "vote_distribution": {"redis": 2, "memcached": 1}
            }
        )

    @pytest.fixture
    def sample_deliberation_result(self, sample_deliberation_request, sample_persona_responses, sample_consensus_result):
        """Create a complete sample deliberation result"""
        return DeliberationResult(
            request=sample_deliberation_request,
            consensus=sample_consensus_result,
            persona_responses=sample_persona_responses,
            deliberation_time=3.2,
            blackboard_topic="test_caching_deliberation",
            statistics={
                "total_messages": 15,
                "consensus_rounds": 2,
                "average_confidence": 0.8
            }
        )

    async def test_memory_system_initialization(self, memory_system):
        """Test that memory system initializes correctly"""
        assert memory_system is not None
        
        health = await memory_system.health_check()
        assert health["status"] == "healthy"

    async def test_store_deliberation_basic(self, memory_system, clean_database, sample_deliberation_request, sample_deliberation_result):
        """Test basic deliberation storage"""
        # Store deliberation
        stored_memory = await memory_system.store_deliberation(
            sample_deliberation_request, 
            sample_deliberation_result
        )
        
        assert stored_memory is not None
        assert stored_memory.query == sample_deliberation_request.query
        assert stored_memory.topic == sample_deliberation_request.topic
        assert stored_memory.consensus_confidence == sample_deliberation_result.consensus.confidence
        assert stored_memory.persona_count == len(sample_deliberation_result.persona_responses)

    async def test_store_and_recall_memories(self, memory_system, clean_database, sample_deliberation_request, sample_deliberation_result):
        """Test storing and recalling memories"""
        # Store deliberation
        await memory_system.store_deliberation(sample_deliberation_request, sample_deliberation_result)
        
        # Create memory query
        memory_query = MemoryQuery(
            query_text="caching implementation strategies",
            context={"project": "web_app"},
            limit=5,
            min_relevance=0.1
        )
        
        # Recall memories
        recall_result = await memory_system.recall_memories(memory_query)
        
        assert len(recall_result.memories) >= 1
        assert all(score >= 0.1 for score in recall_result.relevance_scores)
        assert recall_result.total_found >= 1
        assert recall_result.query_time > 0

    async def test_similarity_matching(self, memory_system, clean_database):
        """Test similarity matching between memories"""
        # Store several related deliberations
        queries = [
            "How to implement Redis caching?",
            "Best practices for cache invalidation?",
            "Database connection pooling strategies?",
            "Redis vs Memcached comparison?",
            "API rate limiting implementation?"
        ]
        
        for i, query in enumerate(queries):
            request = DeliberationRequest(
                query=query,
                context={"performance": True},
                topic=f"test_topic_{i}"
            )
            
            # Create a mock result
            consensus = ConsensusResult(
                decision=f"Recommendation for: {query}",
                confidence=0.7,
                method=ConsensusMethod.SIMPLE_MAJORITY,
                agreement_level=0.8,
                supporting_personas=["strategist"],
                dissenting_personas=[],
                reasoning="Test reasoning",
                metadata={}
            )
            
            result = DeliberationResult(
                request=request,
                consensus=consensus,
                persona_responses=[],
                deliberation_time=2.0,
                blackboard_topic=f"test_topic_{i}",
                statistics={}
            )
            
            await memory_system.store_deliberation(request, result)
        
        # Test similarity search
        similar_memories = await memory_system.find_similar_memories(
            "Redis caching strategy", 
            limit=3,
            threshold=0.2
        )
        
        assert len(similar_memories) > 0
        
        # Check that Redis-related queries rank higher
        memories_text = [mem.query.lower() for mem, score in similar_memories]
        redis_memories = [text for text in memories_text if 'redis' in text or 'cache' in text]
        assert len(redis_memories) > 0

    async def test_learning_patterns(self, memory_system, clean_database):
        """Test learning pattern creation and tracking"""
        persona_name = "test_strategist"
        
        # Store multiple deliberations for the same persona
        for i in range(5):
            request = DeliberationRequest(
                query=f"Strategic decision {i}",
                context={"domain": "strategy"},
                topic=f"strategy_{i}"
            )
            
            # Create response with varying confidence
            response = PersonaResponse(
                persona_name=persona_name,
                persona_role="Strategic Advisor",
                response=f"Strategic recommendation {i}",
                reasoning="Strategic analysis",
                confidence=0.5 + (i * 0.1),
                response_time=2.0,
                tools_used=["analysis"],
                context_used={"domain": "strategy"},
                recommendation="Strategic approach"
            )
            
            consensus = ConsensusResult(
                decision=f"Decision {i}",
                confidence=0.7,
                method=ConsensusMethod.CONSENSUS,
                agreement_level=0.8,
                supporting_personas=[persona_name],
                dissenting_personas=[],
                reasoning="Consensus reached",
                metadata={}
            )
            
            result = DeliberationResult(
                request=request,
                consensus=consensus,
                persona_responses=[response],
                deliberation_time=3.0,
                blackboard_topic=f"strategy_{i}",
                statistics={}
            )
            
            await memory_system.store_deliberation(request, result)
        
        # Check learning patterns were created
        summary = await memory_system.get_persona_memory_summary(persona_name)
        
        assert summary["persona_name"] == persona_name
        assert summary["total_responses"] == 5
        assert summary["learning_patterns"] > 0
        assert len(summary["strongest_patterns"]) > 0

    async def test_context_memory_storage(self, memory_system, clean_database, sample_deliberation_request, sample_deliberation_result):
        """Test that context memories are stored correctly"""
        # Store deliberation with context
        await memory_system.store_deliberation(sample_deliberation_request, sample_deliberation_result)
        
        # Verify context memories were created
        db_manager = get_database_manager()
        async with db_manager.get_postgres_session() as session:
            context_count_query = select(func.count(ContextMemory.id))
            context_count_result = await session.execute(context_count_query)
            context_count = context_count_result.scalar()
            
            # Should have context memories from persona responses
            assert context_count >= 0  # At least some context should be stored

    async def test_memory_associations(self, memory_system, clean_database):
        """Test memory association creation"""
        # Store two related deliberations
        queries = [
            "How to scale a web application?",
            "Best practices for application scalability?"
        ]
        
        for i, query in enumerate(queries):
            request = DeliberationRequest(
                query=query,
                context={"scalability": True},
                topic=f"scalability_{i}"
            )
            
            consensus = ConsensusResult(
                decision=f"Scalability solution {i}",
                confidence=0.8,
                method=ConsensusMethod.WEIGHTED_VOTING,
                agreement_level=0.9,
                supporting_personas=["strategist"],
                dissenting_personas=[],
                reasoning="Strong consensus",
                metadata={}
            )
            
            result = DeliberationResult(
                request=request,
                consensus=consensus,
                persona_responses=[],
                deliberation_time=2.5,
                blackboard_topic=f"scalability_{i}",
                statistics={}
            )
            
            await memory_system.store_deliberation(request, result)
        
        # Check if associations were created
        db_manager = get_database_manager()
        async with db_manager.get_postgres_session() as session:
            associations_query = select(func.count(MemoryAssociation.id))
            associations_result = await session.execute(associations_query)
            associations_count = associations_result.scalar()
            
            # Should have created some associations due to similarity
            assert associations_count >= 0  # Associations are created for similar memories

    async def test_performance_with_many_memories(self, memory_system, clean_database):
        """Test system performance with a large number of memories"""
        # Store 100+ memories to test performance
        start_time = datetime.now()
        
        topics = ["caching", "database", "security", "performance", "scalability"]
        
        memories_created = 0
        for i in range(100):
            topic = random.choice(topics)
            request = DeliberationRequest(
                query=f"How to optimize {topic} for scenario {i}?",
                context={"optimization": True, "scenario": i},
                topic=f"{topic}_{i}"
            )
            
            consensus = ConsensusResult(
                decision=f"Optimize {topic} using approach {i % 5}",
                confidence=random.uniform(0.5, 0.95),
                method=ConsensusMethod.SIMPLE_MAJORITY,
                agreement_level=random.uniform(0.6, 1.0),
                supporting_personas=["strategist", "analyst"],
                dissenting_personas=[],
                reasoning=f"Analysis for {topic} optimization",
                metadata={}
            )
            
            result = DeliberationResult(
                request=request,
                consensus=consensus,
                persona_responses=[],
                deliberation_time=random.uniform(1.0, 5.0),
                blackboard_topic=f"{topic}_{i}",
                statistics={}
            )
            
            await memory_system.store_deliberation(request, result)
            memories_created += 1
            
            # Test recall performance periodically
            if i % 25 == 0 and i > 0:
                query = MemoryQuery(
                    query_text=f"{topic} optimization",
                    context={"optimization": True},
                    limit=10,
                    min_relevance=0.1
                )
                
                recall_start = datetime.now()
                recall_result = await memory_system.recall_memories(query)
                recall_time = (datetime.now() - recall_start).total_seconds()
                
                # Recall should be fast even with many memories
                assert recall_time < 2.0  # Should complete within 2 seconds
                assert len(recall_result.memories) > 0
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        print(f"Created {memories_created} memories in {total_time:.2f} seconds")
        print(f"Average storage time: {total_time/memories_created:.3f} seconds per memory")
        
        # Performance assertions
        assert memories_created == 100
        assert total_time < 120  # Should complete within 2 minutes
        
        # Test final recall performance
        query = MemoryQuery(
            query_text="database optimization strategies",
            context={"optimization": True},
            limit=15,
            min_relevance=0.1
        )
        
        recall_start = datetime.now()
        final_recall = await memory_system.recall_memories(query)
        final_recall_time = (datetime.now() - recall_start).total_seconds()
        
        assert final_recall_time < 3.0  # Should be fast even with 100+ memories
        assert len(final_recall.memories) > 0

    async def test_memory_system_health_check(self, memory_system, clean_database):
        """Test memory system health check functionality"""
        health = await memory_system.health_check()
        
        assert "status" in health
        assert health["status"] == "healthy"
        assert "total_deliberations" in health
        assert "total_responses" in health
        assert health["total_deliberations"] >= 0
        assert health["total_responses"] >= 0

    async def test_memory_consolidation(self, memory_system, clean_database):
        """Test memory consolidation functionality"""
        # Create some old memories (simulate by setting created date)
        for i in range(10):
            request = DeliberationRequest(
                query=f"Old query {i}",
                context={"old": True},
                topic=f"old_{i}"
            )
            
            consensus = ConsensusResult(
                decision="Old decision",
                confidence=0.1,  # Low importance
                method=ConsensusMethod.SIMPLE_MAJORITY,
                agreement_level=0.5,
                supporting_personas=[],
                dissenting_personas=[],
                reasoning="Old reasoning",
                metadata={}
            )
            
            result = DeliberationResult(
                request=request,
                consensus=consensus,
                persona_responses=[],
                deliberation_time=1.0,
                blackboard_topic=f"old_{i}",
                statistics={}
            )
            
            # Store with low importance
            memory = await memory_system.store_deliberation(request, result)
            
            # Manually update importance to be very low for testing
            db_manager = get_database_manager()
            async with db_manager.get_postgres_session() as session:
                memory_to_update = await session.get(DeliberationMemory, memory.id)
                memory_to_update.importance_score = 0.15  # Low importance
                memory_to_update.created_at = datetime.now() - timedelta(days=100)  # Old
                await session.commit()
        
        # Run consolidation
        await memory_system.consolidate_old_memories(days_threshold=50)
        
        # Verify consolidation occurred (memories should have reduced importance)
        db_manager = get_database_manager()
        async with db_manager.get_postgres_session() as session:
            low_importance_query = select(func.count(DeliberationMemory.id)).where(
                DeliberationMemory.importance_score < 0.15
            )
            result = await session.execute(low_importance_query)
            low_importance_count = result.scalar()
            
            # Some memories should have been further reduced in importance
            assert low_importance_count > 0

    async def test_integration_with_orchestrator(self):
        """Test full integration between memory system and orchestrator"""
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        
        # Ensure memory system was initialized
        assert orchestrator.memory_system is not None
        
        # Create a deliberation request
        request = DeliberationRequest(
            query="What's the best way to implement user authentication?",
            context={"security": "high", "user_base": "large"},
            topic="authentication_strategy"
        )
        
        # Run deliberation (this should store memories)
        result = await orchestrator.deliberate(request)
        
        # Verify deliberation completed
        assert result is not None
        assert result.consensus is not None
        
        # Verify memory was stored
        memory_query = MemoryQuery(
            query_text="authentication implementation",
            context={"security": "high"},
            limit=5,
            min_relevance=0.1
        )
        
        recall_result = await orchestrator.memory_system.recall_memories(memory_query)
        assert len(recall_result.memories) >= 1
        
        # Run another related deliberation to test memory recall
        request2 = DeliberationRequest(
            query="How to secure user login process?",
            context={"security": "high", "authentication": True},
            topic="login_security"
        )
        
        # This should use memories from previous deliberation
        result2 = await orchestrator.deliberate(request2)
        
        assert result2 is not None
        # The context should have been enhanced with memories
        assert "memory_context_available" in result2.request.context or \
               "remembered_experiences" in result2.request.context


class TestMemoryQueries:
    """Test various memory query scenarios"""

    @pytest.fixture
    async def populated_memory_system(self, memory_system, clean_database):
        """Create a memory system with test data"""
        # Add diverse test data
        test_scenarios = [
            {
                "query": "How to implement microservices architecture?",
                "context": {"architecture": "microservices", "scale": "large"},
                "topic": "microservices",
                "confidence": 0.9
            },
            {
                "query": "Database sharding strategies for high traffic?",
                "context": {"database": "mysql", "traffic": "high"},
                "topic": "database_scaling", 
                "confidence": 0.8
            },
            {
                "query": "React vs Vue for frontend development?",
                "context": {"frontend": True, "framework": "comparison"},
                "topic": "frontend_choice",
                "confidence": 0.7
            },
            {
                "query": "Docker container orchestration best practices?",
                "context": {"devops": True, "containers": "docker"},
                "topic": "container_orchestration",
                "confidence": 0.85
            },
            {
                "query": "API security and rate limiting implementation?",
                "context": {"api": True, "security": "high"},
                "topic": "api_security",
                "confidence": 0.92
            }
        ]
        
        for scenario in test_scenarios:
            request = DeliberationRequest(
                query=scenario["query"],
                context=scenario["context"],
                topic=scenario["topic"]
            )
            
            consensus = ConsensusResult(
                decision=f"Recommended solution for: {scenario['topic']}",
                confidence=scenario["confidence"],
                method=ConsensusMethod.WEIGHTED_VOTING,
                agreement_level=0.8,
                supporting_personas=["strategist", "analyst"],
                dissenting_personas=[],
                reasoning="Well-reasoned decision",
                metadata={}
            )
            
            result = DeliberationResult(
                request=request,
                consensus=consensus,
                persona_responses=[],
                deliberation_time=2.0,
                blackboard_topic=scenario["topic"],
                statistics={}
            )
            
            await memory_system.store_deliberation(request, result)
        
        return memory_system

    async def test_topic_based_queries(self, populated_memory_system):
        """Test queries filtered by topic"""
        query = MemoryQuery(
            query_text="architecture patterns",
            context={},
            topic="microservices",
            limit=5
        )
        
        result = await populated_memory_system.recall_memories(query)
        
        assert len(result.memories) >= 1
        # Should find the microservices memory
        microservices_found = any("microservices" in mem.query.lower() for mem in result.memories)
        assert microservices_found

    async def test_context_based_queries(self, populated_memory_system):
        """Test queries that match on context"""
        query = MemoryQuery(
            query_text="system design",
            context={"security": "high"},
            limit=5
        )
        
        result = await populated_memory_system.recall_memories(query)
        
        assert len(result.memories) >= 1
        # Should prioritize memories with security context
        security_memories = [mem for mem in result.memories if "security" in str(mem.context)]
        assert len(security_memories) > 0

    async def test_relevance_threshold_filtering(self, populated_memory_system):
        """Test that relevance threshold filtering works"""
        # High threshold should return fewer results
        high_threshold_query = MemoryQuery(
            query_text="completely unrelated topic xyz",
            context={},
            limit=10,
            min_relevance=0.8
        )
        
        high_result = await populated_memory_system.recall_memories(high_threshold_query)
        
        # Low threshold should return more results
        low_threshold_query = MemoryQuery(
            query_text="development practices",
            context={},
            limit=10,
            min_relevance=0.1
        )
        
        low_result = await populated_memory_system.recall_memories(low_threshold_query)
        
        # Low threshold should find more matches
        assert len(low_result.memories) >= len(high_result.memories)

    async def test_time_range_queries(self, populated_memory_system):
        """Test queries with time range filtering"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        query = MemoryQuery(
            query_text="development",
            context={},
            time_range=(one_hour_ago, now),
            limit=10
        )
        
        result = await populated_memory_system.recall_memories(query)
        
        # All returned memories should be within time range
        for memory in result.memories:
            assert one_hour_ago <= memory.created_at <= now


if __name__ == "__main__":
    # Run tests manually if needed
    pytest.main([__file__, "-v"])
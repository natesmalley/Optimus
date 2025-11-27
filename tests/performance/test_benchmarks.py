"""
Performance benchmarking tests for specific system components
Detailed benchmarks for personas, consensus, memory, and knowledge graph operations
"""

import pytest
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch
import statistics
import gc

from src.council.personas import StrategistPersona, PragmatistPersona, ALL_PERSONAS
from src.council.consensus import ConsensusEngine, ConsensusMethod
from src.council.blackboard import Blackboard, BlackboardEntry, EntryType
from src.council.persona import PersonaResponse, PersonaPriority
from src.database.memory_optimized import OptimizedMemoryManager, MemoryEntry
from src.database.knowledge_graph_optimized import OptimizedKnowledgeGraph, Entity, Relationship


class TestPersonaBenchmarks:
    """Benchmark individual persona performance"""
    
    @pytest.fixture
    async def benchmark_personas(self):
        """Create personas for benchmarking"""
        personas = []
        for PersonaClass in ALL_PERSONAS[:5]:  # Test first 5 personas
            persona = PersonaClass()
            await persona.initialize()
            
            # Mock blackboard for consistent testing
            mock_blackboard = MagicMock()
            mock_blackboard.get_recent_entries = AsyncMock(return_value=[])
            mock_blackboard.post = AsyncMock()
            persona.connect_blackboard(mock_blackboard)
            
            personas.append(persona)
        
        return personas
    
    async def test_persona_response_time_benchmark(self, benchmark_personas):
        """Benchmark persona response times"""
        test_queries = [
            ("What database should we use?", {"type": "database_selection"}),
            ("How should we implement authentication?", {"security": "high"}),
            ("What's the best deployment strategy?", {"environment": "production"}),
            ("How can we improve performance?", {"current_metrics": "slow"}),
            ("What architecture pattern is optimal?", {"complexity": "high"})
        ]
        
        persona_benchmarks = {}
        
        for persona in benchmark_personas:
            response_times = []
            
            for query, context in test_queries:
                start_time = time.time()
                
                response = await persona.deliberate(
                    topic="benchmark_test",
                    query=query,
                    context=context
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                # Verify response quality
                assert isinstance(response, PersonaResponse)
                assert len(response.recommendation) > 10
                assert response.confidence > 0
            
            persona_benchmarks[persona.persona_id] = {
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "response_times": response_times
            }
        
        # Performance assertions
        for persona_id, metrics in persona_benchmarks.items():
            assert metrics["avg_response_time"] < 1.0  # Should average under 1 second
            assert metrics["max_response_time"] < 2.0  # No response should take too long
        
        return persona_benchmarks
    
    async def test_persona_memory_efficiency(self, benchmark_personas):
        """Benchmark persona memory usage"""
        import tracemalloc
        
        memory_benchmarks = {}
        
        for persona in benchmark_personas:
            # Start memory tracing
            tracemalloc.start()
            
            # Run multiple deliberations
            for i in range(20):
                await persona.deliberate(
                    topic=f"memory_test_{i}",
                    query=f"Memory efficiency test query {i}",
                    context={"test_id": i}
                )
            
            # Get memory usage
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            memory_benchmarks[persona.persona_id] = {
                "current_memory_bytes": current,
                "peak_memory_bytes": peak,
                "current_memory_mb": current / 1024 / 1024,
                "peak_memory_mb": peak / 1024 / 1024
            }
            
            # Clean up
            gc.collect()
        
        # Memory efficiency assertions
        for persona_id, metrics in memory_benchmarks.items():
            assert metrics["peak_memory_mb"] < 50  # Should use less than 50MB per persona
        
        return memory_benchmarks
    
    async def test_persona_concurrent_performance(self, benchmark_personas):
        """Benchmark persona performance under concurrent load"""
        concurrent_requests = 15
        
        async def concurrent_persona_test(persona, request_id):
            start_time = time.time()
            response = await persona.deliberate(
                topic=f"concurrent_test_{request_id}",
                query=f"Concurrent performance test {request_id}",
                context={"concurrent": True, "request_id": request_id}
            )
            end_time = time.time()
            
            return {
                "persona_id": persona.persona_id,
                "request_id": request_id,
                "response_time": end_time - start_time,
                "response": response
            }
        
        concurrent_benchmarks = {}
        
        for persona in benchmark_personas:
            start_time = time.time()
            
            # Run concurrent requests to same persona
            tasks = [concurrent_persona_test(persona, i) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            response_times = [r["response_time"] for r in results]
            
            concurrent_benchmarks[persona.persona_id] = {
                "total_concurrent_time": total_time,
                "avg_response_time": statistics.mean(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times),
                "throughput": concurrent_requests / total_time,
                "successful_responses": len([r for r in results if r["response"] is not None])
            }
        
        # Concurrent performance assertions
        for persona_id, metrics in concurrent_benchmarks.items():
            assert metrics["successful_responses"] == concurrent_requests  # All should succeed
            assert metrics["throughput"] > 5.0  # Should handle good concurrent throughput
            assert metrics["avg_response_time"] < 2.0  # Should maintain good response times
        
        return concurrent_benchmarks


class TestConsensusBenchmarks:
    """Benchmark consensus engine performance"""
    
    @pytest.fixture
    async def benchmark_consensus_engine(self):
        """Create consensus engine for benchmarking"""
        blackboard = Blackboard()
        await blackboard.initialize()
        
        # Mock blackboard operations for consistency
        blackboard.post = AsyncMock()
        
        engine = ConsensusEngine(blackboard)
        return engine
    
    def create_sample_responses(self, count: int, variation: str = "mixed") -> List[PersonaResponse]:
        """Create sample persona responses for testing"""
        if variation == "unanimous":
            # All personas agree
            return [
                PersonaResponse(
                    persona_id=f"persona_{i}",
                    recommendation="Use PostgreSQL database",
                    reasoning=f"Reasoning {i} for PostgreSQL",
                    confidence=0.8 + (i * 0.02),
                    priority=PersonaPriority.HIGH
                )
                for i in range(count)
            ]
        elif variation == "conflicted":
            # Personas disagree
            recommendations = ["Use PostgreSQL", "Use MongoDB", "Use MySQL"]
            return [
                PersonaResponse(
                    persona_id=f"persona_{i}",
                    recommendation=recommendations[i % 3],
                    reasoning=f"Reasoning for {recommendations[i % 3]}",
                    confidence=0.7 + (i * 0.01),
                    priority=PersonaPriority.MEDIUM
                )
                for i in range(count)
            ]
        else:
            # Mixed responses
            recommendations = ["Option A", "Option B", "Option A", "Option C"]
            return [
                PersonaResponse(
                    persona_id=f"persona_{i}",
                    recommendation=recommendations[i % len(recommendations)],
                    reasoning=f"Mixed reasoning {i}",
                    confidence=0.6 + (i * 0.03),
                    priority=PersonaPriority.MEDIUM
                )
                for i in range(count)
            ]
    
    async def test_consensus_method_performance(self, benchmark_consensus_engine):
        """Benchmark different consensus methods"""
        engine = benchmark_consensus_engine
        
        response_counts = [5, 10, 15, 20]
        consensus_methods = [
            ConsensusMethod.WEIGHTED_MAJORITY,
            ConsensusMethod.SUPERMAJORITY,
            ConsensusMethod.CONFIDENCE_WEIGHTED,
            ConsensusMethod.HYBRID
        ]
        
        method_benchmarks = {}
        
        for method in consensus_methods:
            method_times = []
            
            for count in response_counts:
                responses = self.create_sample_responses(count)
                weights = {f"persona_{i}": 0.8 for i in range(count)}
                
                start_time = time.time()
                result = await engine.reach_consensus(
                    topic=f"benchmark_{method.value}_{count}",
                    responses=responses,
                    weights=weights,
                    method=method
                )
                end_time = time.time()
                
                consensus_time = end_time - start_time
                method_times.append(consensus_time)
                
                # Verify consensus quality
                assert result.decision is not None
                assert result.confidence > 0
            
            method_benchmarks[method.value] = {
                "avg_consensus_time": statistics.mean(method_times),
                "max_consensus_time": max(method_times),
                "consensus_times_by_count": dict(zip(response_counts, method_times))
            }
        
        # Performance assertions
        for method, metrics in method_benchmarks.items():
            assert metrics["avg_consensus_time"] < 0.5  # Should be fast
            assert metrics["max_consensus_time"] < 1.0  # Even with many responses
        
        return method_benchmarks
    
    async def test_consensus_scalability(self, benchmark_consensus_engine):
        """Test consensus performance scaling with response count"""
        engine = benchmark_consensus_engine
        
        response_counts = [1, 5, 10, 20, 50, 100]
        scalability_results = {}
        
        for count in response_counts:
            responses = self.create_sample_responses(count)
            weights = {f"persona_{i}": 0.5 + (i * 0.01) for i in range(count)}
            
            # Test multiple runs for each count
            run_times = []
            for run in range(5):
                start_time = time.time()
                result = await engine.reach_consensus(
                    topic=f"scalability_test_{count}_{run}",
                    responses=responses,
                    weights=weights,
                    method=ConsensusMethod.HYBRID
                )
                end_time = time.time()
                run_times.append(end_time - start_time)
            
            scalability_results[count] = {
                "avg_time": statistics.mean(run_times),
                "min_time": min(run_times),
                "max_time": max(run_times)
            }
        
        # Check scaling behavior
        times_by_count = [(count, metrics["avg_time"]) for count, metrics in scalability_results.items()]
        
        # Should scale reasonably (not exponentially)
        for i in range(1, len(times_by_count)):
            prev_count, prev_time = times_by_count[i-1]
            curr_count, curr_time = times_by_count[i]
            
            # Time shouldn't increase faster than response count
            time_ratio = curr_time / prev_time if prev_time > 0 else 1
            count_ratio = curr_count / prev_count
            
            assert time_ratio < count_ratio * 2  # Should scale better than linear
        
        return scalability_results


class TestBlackboardBenchmarks:
    """Benchmark blackboard operations"""
    
    @pytest.fixture
    async def benchmark_blackboard(self):
        """Create blackboard for benchmarking"""
        blackboard = Blackboard()
        await blackboard.initialize()
        return blackboard
    
    async def test_blackboard_entry_performance(self, benchmark_blackboard):
        """Benchmark blackboard entry operations"""
        blackboard = benchmark_blackboard
        
        entry_counts = [10, 50, 100, 200, 500]
        operation_benchmarks = {}
        
        for count in entry_counts:
            topic = f"benchmark_topic_{count}"
            
            # Benchmark posting entries
            entries = [
                BlackboardEntry(
                    persona_id=f"persona_{i%10}",
                    entry_type=EntryType.INSIGHT,
                    content=f"Benchmark entry {i} with substantial content for performance testing",
                    metadata={"benchmark": True, "entry_id": i},
                    tags=[f"tag_{j}" for j in range(i%5)]
                )
                for i in range(count)
            ]
            
            post_start = time.time()
            for entry in entries:
                await blackboard.post(topic, entry)
            post_end = time.time()
            
            post_time = post_end - post_start
            
            # Benchmark retrieving entries
            retrieve_start = time.time()
            retrieved_entries = await blackboard.get_entries(topic)
            retrieve_end = time.time()
            
            retrieve_time = retrieve_end - retrieve_start
            
            # Benchmark searching entries
            search_start = time.time()
            search_results = await blackboard.search_entries(topic, "benchmark")
            search_end = time.time()
            
            search_time = search_end - search_start
            
            operation_benchmarks[count] = {
                "post_time": post_time,
                "retrieve_time": retrieve_time,
                "search_time": search_time,
                "post_throughput": count / post_time,
                "retrieve_count": len(retrieved_entries),
                "search_count": len(search_results)
            }
            
            # Verify operations
            assert len(retrieved_entries) == count
            assert len(search_results) > 0
        
        # Performance assertions
        for count, metrics in operation_benchmarks.items():
            assert metrics["post_throughput"] > 20  # Should post at least 20 entries/sec
            assert metrics["retrieve_time"] < 1.0   # Retrieval should be fast
            assert metrics["search_time"] < 2.0     # Search should be reasonable
        
        return operation_benchmarks
    
    async def test_blackboard_concurrent_access(self, benchmark_blackboard):
        """Benchmark concurrent blackboard access"""
        blackboard = benchmark_blackboard
        
        concurrent_operations = 25
        topics = [f"concurrent_topic_{i}" for i in range(5)]
        
        async def concurrent_blackboard_operation(op_id):
            topic = topics[op_id % len(topics)]
            
            if op_id % 3 == 0:
                # Post operation
                entry = BlackboardEntry(
                    persona_id=f"concurrent_persona_{op_id}",
                    entry_type=EntryType.INSIGHT,
                    content=f"Concurrent entry {op_id}"
                )
                start_time = time.time()
                await blackboard.post(topic, entry)
                end_time = time.time()
                operation_type = "post"
            elif op_id % 3 == 1:
                # Retrieve operation
                start_time = time.time()
                await blackboard.get_entries(topic)
                end_time = time.time()
                operation_type = "retrieve"
            else:
                # Search operation
                start_time = time.time()
                await blackboard.search_entries(topic, "concurrent")
                end_time = time.time()
                operation_type = "search"
            
            return {
                "operation_id": op_id,
                "operation_type": operation_type,
                "execution_time": end_time - start_time
            }
        
        # Execute concurrent operations
        start_time = time.time()
        tasks = [concurrent_blackboard_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # Analyze by operation type
        post_times = [r["execution_time"] for r in results if r["operation_type"] == "post"]
        retrieve_times = [r["execution_time"] for r in results if r["operation_type"] == "retrieve"]
        search_times = [r["execution_time"] for r in results if r["operation_type"] == "search"]
        
        concurrent_benchmark = {
            "total_operations": len(results),
            "total_time": total_time,
            "throughput": len(results) / total_time,
            "avg_post_time": statistics.mean(post_times) if post_times else 0,
            "avg_retrieve_time": statistics.mean(retrieve_times) if retrieve_times else 0,
            "avg_search_time": statistics.mean(search_times) if search_times else 0,
            "operation_counts": {
                "post": len(post_times),
                "retrieve": len(retrieve_times),
                "search": len(search_times)
            }
        }
        
        # Concurrent performance assertions
        assert total_time < 10.0  # Should complete quickly
        assert concurrent_benchmark["throughput"] > 5.0  # Good concurrent throughput
        
        return concurrent_benchmark


class TestKnowledgeGraphBenchmarks:
    """Benchmark knowledge graph operations"""
    
    @pytest.fixture
    async def benchmark_knowledge_graph(self, temp_database):
        """Create knowledge graph for benchmarking"""
        with patch('src.database.knowledge_graph_optimized.DATABASE_CONFIG', temp_database):
            kg = OptimizedKnowledgeGraph()
            await kg.initialize()
            return kg
    
    async def test_entity_operation_performance(self, benchmark_knowledge_graph):
        """Benchmark entity operations"""
        kg = benchmark_knowledge_graph
        
        entity_counts = [10, 50, 100]
        entity_benchmarks = {}
        
        for count in entity_counts:
            # Create entities
            entities = [
                Entity(
                    entity_id=f"benchmark_entity_{i}",
                    entity_type=f"type_{i%5}",
                    name=f"Benchmark Entity {i}",
                    properties={
                        "benchmark": True,
                        "entity_number": i,
                        "description": f"Entity {i} for performance testing" * 5
                    }
                )
                for i in range(count)
            ]
            
            # Benchmark adding entities
            add_start = time.time()
            for entity in entities:
                await kg.add_entity(entity)
            add_end = time.time()
            
            add_time = add_end - add_start
            
            # Benchmark querying entities
            query_start = time.time()
            type_0_entities = await kg.query_entities_by_type("type_0")
            query_end = time.time()
            
            query_time = query_end - query_start
            
            entity_benchmarks[count] = {
                "add_time": add_time,
                "query_time": query_time,
                "add_throughput": count / add_time,
                "entities_found": len(type_0_entities)
            }
        
        # Performance assertions
        for count, metrics in entity_benchmarks.items():
            assert metrics["add_throughput"] > 5  # Should add at least 5 entities/sec
            assert metrics["query_time"] < 1.0   # Queries should be fast
        
        return entity_benchmarks
    
    async def test_relationship_performance(self, benchmark_knowledge_graph):
        """Benchmark relationship operations"""
        kg = benchmark_knowledge_graph
        
        # Add entities first
        entity_count = 20
        for i in range(entity_count):
            entity = Entity(f"rel_entity_{i}", "node", f"Relationship Entity {i}")
            await kg.add_entity(entity)
        
        # Create relationships
        relationship_count = 50
        relationships = [
            Relationship(
                source_id=f"rel_entity_{i%entity_count}",
                target_id=f"rel_entity_{(i+1)%entity_count}",
                relationship_type="connects_to",
                properties={"strength": i%10, "benchmark": True}
            )
            for i in range(relationship_count)
        ]
        
        # Benchmark adding relationships
        add_rel_start = time.time()
        for relationship in relationships:
            await kg.add_relationship(relationship)
        add_rel_end = time.time()
        
        add_rel_time = add_rel_end - add_rel_start
        
        # Benchmark finding paths
        path_start = time.time()
        path = await kg.find_path("rel_entity_0", "rel_entity_5", max_depth=5)
        path_end = time.time()
        
        path_time = path_end - path_start
        
        # Benchmark getting neighbors
        neighbors_start = time.time()
        neighbors = await kg.get_neighbors("rel_entity_0")
        neighbors_end = time.time()
        
        neighbors_time = neighbors_end - neighbors_start
        
        relationship_benchmark = {
            "add_relationship_time": add_rel_time,
            "add_relationship_throughput": relationship_count / add_rel_time,
            "path_finding_time": path_time,
            "neighbors_query_time": neighbors_time,
            "path_found": path is not None and len(path) > 0,
            "neighbors_count": len(neighbors) if neighbors else 0
        }
        
        # Performance assertions
        assert relationship_benchmark["add_relationship_throughput"] > 10  # Good throughput
        assert relationship_benchmark["path_finding_time"] < 1.0  # Fast path finding
        assert relationship_benchmark["neighbors_query_time"] < 0.5  # Fast neighbor queries
        
        return relationship_benchmark
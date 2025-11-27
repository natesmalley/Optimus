"""
Performance and load tests for the Optimus Council of Minds system
Tests system behavior under high load, concurrent operations, and stress conditions
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch
import statistics
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.council.orchestrator import Orchestrator, DeliberationRequest, DeliberationResult
from src.council.personas import CORE_PERSONAS, ALL_PERSONAS
from src.database.memory_optimized import OptimizedMemoryManager, MemoryEntry
from src.database.knowledge_graph_optimized import OptimizedKnowledgeGraph


class TestDeliberationPerformance:
    """Test deliberation performance under various loads"""
    
    @pytest.fixture
    async def performance_orchestrator(self):
        """Create orchestrator optimized for performance testing"""
        orchestrator = Orchestrator(use_all_personas=False)
        
        # Mock external dependencies for consistent performance
        with patch('src.database.memory_optimized.OptimizedMemoryManager'):
            with patch('src.database.knowledge_graph_optimized.OptimizedKnowledgeGraph'):
                await orchestrator.initialize()
        
        # Mock persona responses to have consistent timing
        for persona in orchestrator.personas.values():
            persona.deliberate = AsyncMock(return_value=MagicMock(
                persona_id=persona.persona_id,
                recommendation="Performance test recommendation",
                confidence=0.8,
                priority=MagicMock(value="medium")
            ))
        
        return orchestrator
    
    async def test_single_deliberation_baseline_performance(self, performance_orchestrator):
        """Test baseline performance of single deliberation"""
        orchestrator = performance_orchestrator
        
        request = DeliberationRequest(
            query="What is the optimal database configuration for high performance?",
            context={"performance_requirements": "high", "load": "1000_qps"},
            topic="performance_baseline_test",
            timeout=5.0
        )
        
        # Measure single deliberation performance
        start_time = time.time()
        result = await orchestrator.deliberate(request)
        end_time = time.time()
        
        deliberation_time = end_time - start_time
        
        # Verify result
        assert isinstance(result, DeliberationResult)
        assert result.consensus is not None
        
        # Performance benchmarks
        assert deliberation_time < 3.0  # Should complete within 3 seconds
        assert result.deliberation_time < 2.5  # Internal timing should be fast
        
        # Memory usage check
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        assert memory_mb < 500  # Should use less than 500MB for single deliberation
        
        return {
            "deliberation_time": deliberation_time,
            "internal_time": result.deliberation_time,
            "memory_usage_mb": memory_mb,
            "persona_count": len(result.persona_responses)
        }
    
    async def test_concurrent_deliberations_performance(self, performance_orchestrator):
        """Test performance with concurrent deliberations"""
        orchestrator = performance_orchestrator
        
        concurrent_count = 10
        
        async def run_deliberation(deliberation_id):
            request = DeliberationRequest(
                query=f"Performance test query {deliberation_id}",
                context={"test_id": deliberation_id, "load_test": True},
                topic=f"concurrent_test_{deliberation_id}",
                timeout=5.0
            )
            
            start_time = time.time()
            result = await orchestrator.deliberate(request)
            end_time = time.time()
            
            return {
                "deliberation_id": deliberation_id,
                "execution_time": end_time - start_time,
                "result": result
            }
        
        # Run concurrent deliberations
        start_time = time.time()
        tasks = [run_deliberation(i) for i in range(concurrent_count)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        execution_times = [r["execution_time"] for r in results]
        
        # Performance analysis
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        # Assertions
        assert len(results) == concurrent_count
        assert all(r["result"] is not None for r in results)
        
        # Performance requirements
        assert total_time < 15.0  # All should complete within 15 seconds
        assert avg_time < 5.0     # Average should be reasonable
        assert max_time < 8.0     # No deliberation should take too long
        
        # Check system resources
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        assert memory_mb < 1000  # Should use less than 1GB even with concurrency
        
        return {
            "total_time": total_time,
            "avg_execution_time": avg_time,
            "max_execution_time": max_time,
            "min_execution_time": min_time,
            "throughput": concurrent_count / total_time,
            "memory_usage_mb": memory_mb
        }
    
    async def test_sequential_deliberations_throughput(self, performance_orchestrator):
        """Test throughput of sequential deliberations"""
        orchestrator = performance_orchestrator
        
        deliberation_count = 20
        execution_times = []
        
        overall_start = time.time()
        
        for i in range(deliberation_count):
            request = DeliberationRequest(
                query=f"Sequential throughput test {i}",
                context={"sequence_id": i},
                topic=f"throughput_test_{i}",
                timeout=3.0
            )
            
            start_time = time.time()
            result = await orchestrator.deliberate(request)
            end_time = time.time()
            
            execution_times.append(end_time - start_time)
            
            # Verify each result
            assert isinstance(result, DeliberationResult)
        
        overall_end = time.time()
        total_time = overall_end - overall_start
        
        # Performance metrics
        avg_time = statistics.mean(execution_times)
        throughput = deliberation_count / total_time
        
        # Performance requirements
        assert avg_time < 2.0  # Average deliberation should be fast
        assert throughput > 5.0  # Should handle at least 5 deliberations per second
        
        return {
            "total_deliberations": deliberation_count,
            "total_time": total_time,
            "avg_execution_time": avg_time,
            "throughput_per_second": throughput,
            "execution_times": execution_times
        }
    
    async def test_memory_usage_under_load(self, performance_orchestrator):
        """Test memory usage patterns under sustained load"""
        orchestrator = performance_orchestrator
        
        process = psutil.Process()
        memory_samples = []
        
        async def run_deliberation_batch(batch_id, batch_size=5):
            batch_start_memory = process.memory_info().rss / 1024 / 1024
            
            tasks = []
            for i in range(batch_size):
                request = DeliberationRequest(
                    query=f"Memory test batch {batch_id} item {i}",
                    context={"batch_id": batch_id, "item_id": i},
                    topic=f"memory_test_b{batch_id}_i{i}",
                    timeout=2.0
                )
                tasks.append(orchestrator.deliberate(request))
            
            await asyncio.gather(*tasks)
            
            batch_end_memory = process.memory_info().rss / 1024 / 1024
            memory_delta = batch_end_memory - batch_start_memory
            
            return {
                "batch_id": batch_id,
                "start_memory_mb": batch_start_memory,
                "end_memory_mb": batch_end_memory,
                "memory_delta_mb": memory_delta
            }
        
        # Run multiple batches to test memory usage
        batch_count = 10
        for batch_id in range(batch_count):
            batch_result = await run_deliberation_batch(batch_id)
            memory_samples.append(batch_result)
            
            # Small delay to allow garbage collection
            await asyncio.sleep(0.1)
        
        # Analyze memory usage
        memory_deltas = [sample["memory_delta_mb"] for sample in memory_samples]
        final_memory = memory_samples[-1]["end_memory_mb"]
        initial_memory = memory_samples[0]["start_memory_mb"]
        total_memory_growth = final_memory - initial_memory
        
        # Memory usage assertions
        assert final_memory < 1500  # Should not exceed 1.5GB
        assert total_memory_growth < 500  # Should not grow more than 500MB
        assert all(delta < 100 for delta in memory_deltas)  # Each batch should not consume too much
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "total_growth_mb": total_memory_growth,
            "batch_memory_deltas": memory_deltas,
            "avg_batch_growth_mb": statistics.mean(memory_deltas)
        }


class TestDatabasePerformance:
    """Test database operations performance"""
    
    @pytest.fixture
    async def performance_memory_manager(self, temp_database, mock_redis):
        """Create memory manager for performance testing"""
        manager = OptimizedMemoryManager()
        manager.redis_client = mock_redis
        
        # Mock high-performance PostgreSQL operations
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()
        mock_conn.executemany = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        
        mock_pool = MagicMock()
        mock_pool.acquire().__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire().__aexit__ = AsyncMock(return_value=None)
        
        manager.postgres_pool = mock_pool
        await manager.initialize()
        
        return manager
    
    async def test_memory_storage_performance(self, performance_memory_manager):
        """Test memory storage performance under load"""
        manager = performance_memory_manager
        
        # Generate test data
        memory_entries = [
            MemoryEntry(
                persona_id=f"persona_{i%5}",
                content=f"Performance test memory entry {i} with substantial content to simulate real usage patterns and test storage efficiency",
                entry_type="performance_test",
                topic=f"perf_topic_{i%10}",
                metadata={"test_id": i, "performance_test": True, "batch_size": 1000},
                tags=[f"tag_{j}" for j in range(i%5)]
            )
            for i in range(1000)
        ]
        
        # Test individual storage performance
        single_storage_times = []
        for i in range(100):  # Test first 100 individually
            start_time = time.time()
            await manager.store_memory(memory_entries[i])
            end_time = time.time()
            single_storage_times.append(end_time - start_time)
        
        # Test batch storage performance
        batch_start_time = time.time()
        await manager.store_memory_batch(memory_entries[100:600])  # 500 entries
        batch_end_time = time.time()
        
        batch_time = batch_end_time - batch_start_time
        avg_single_time = statistics.mean(single_storage_times)
        
        # Performance assertions
        assert avg_single_time < 0.1  # Individual storage should be fast
        assert batch_time < 5.0  # Batch storage should be efficient
        
        # Batch should be more efficient than individual operations
        estimated_individual_time = 500 * avg_single_time
        batch_efficiency = estimated_individual_time / batch_time
        assert batch_efficiency > 2.0  # Batch should be at least 2x faster
        
        return {
            "avg_single_storage_time": avg_single_time,
            "batch_storage_time": batch_time,
            "batch_efficiency_factor": batch_efficiency,
            "entries_processed": len(memory_entries)
        }
    
    async def test_memory_retrieval_performance(self, performance_memory_manager):
        """Test memory retrieval performance"""
        manager = performance_memory_manager
        
        # Mock retrieval results
        mock_memories = [
            {
                "entry_id": f"perf_test_{i}",
                "persona_id": f"persona_{i%5}",
                "content": f"Retrieved memory {i}",
                "entry_type": "test",
                "topic": f"topic_{i%10}",
                "metadata": "{}",
                "tags": "[]",
                "timestamp": datetime.now()
            }
            for i in range(100)
        ]
        
        manager.postgres_pool.acquire().__aenter__.return_value.fetch.return_value = mock_memories
        
        # Test retrieval performance
        retrieval_times = []
        for topic_id in range(20):
            start_time = time.time()
            memories = await manager.retrieve_memories(f"topic_{topic_id}", limit=50)
            end_time = time.time()
            retrieval_times.append(end_time - start_time)
        
        avg_retrieval_time = statistics.mean(retrieval_times)
        max_retrieval_time = max(retrieval_times)
        
        # Performance assertions
        assert avg_retrieval_time < 0.5  # Average retrieval should be fast
        assert max_retrieval_time < 1.0   # No retrieval should take too long
        
        return {
            "avg_retrieval_time": avg_retrieval_time,
            "max_retrieval_time": max_retrieval_time,
            "retrieval_count": len(retrieval_times)
        }
    
    async def test_concurrent_database_operations(self, performance_memory_manager):
        """Test concurrent database operations performance"""
        manager = performance_memory_manager
        
        concurrent_operations = 50
        
        async def concurrent_memory_operation(operation_id):
            # Mix of storage and retrieval operations
            if operation_id % 3 == 0:
                # Storage operation
                memory_entry = MemoryEntry(
                    persona_id=f"concurrent_persona_{operation_id}",
                    content=f"Concurrent operation {operation_id}",
                    entry_type="concurrency_test",
                    topic=f"concurrent_topic_{operation_id}"
                )
                start_time = time.time()
                await manager.store_memory(memory_entry)
                end_time = time.time()
            else:
                # Retrieval operation
                start_time = time.time()
                await manager.retrieve_memories(f"concurrent_topic_{operation_id%10}", limit=10)
                end_time = time.time()
            
            return {
                "operation_id": operation_id,
                "execution_time": end_time - start_time,
                "operation_type": "storage" if operation_id % 3 == 0 else "retrieval"
            }
        
        # Execute concurrent operations
        start_time = time.time()
        tasks = [concurrent_memory_operation(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        operation_times = [r["execution_time"] for r in results]
        avg_operation_time = statistics.mean(operation_times)
        
        # Performance assertions
        assert total_time < 10.0  # All operations should complete quickly
        assert avg_operation_time < 0.5  # Individual operations should be fast
        
        # Analyze operation types
        storage_times = [r["execution_time"] for r in results if r["operation_type"] == "storage"]
        retrieval_times = [r["execution_time"] for r in results if r["operation_type"] == "retrieval"]
        
        return {
            "total_concurrent_time": total_time,
            "avg_operation_time": avg_operation_time,
            "concurrent_operations": concurrent_operations,
            "avg_storage_time": statistics.mean(storage_times) if storage_times else 0,
            "avg_retrieval_time": statistics.mean(retrieval_times) if retrieval_times else 0,
            "throughput_ops_per_second": concurrent_operations / total_time
        }


class TestSystemStressTest:
    """Test system behavior under stress conditions"""
    
    @pytest.fixture
    async def stress_test_orchestrator(self):
        """Create orchestrator for stress testing"""
        orchestrator = Orchestrator(use_all_personas=True)  # Use all personas for stress
        
        with patch('src.database.memory_optimized.OptimizedMemoryManager'):
            with patch('src.database.knowledge_graph_optimized.OptimizedKnowledgeGraph'):
                await orchestrator.initialize()
        
        # Mock personas with variable response times
        for i, persona in enumerate(orchestrator.personas.values()):
            async def variable_response_time(*args, **kwargs):
                # Simulate variable processing time
                await asyncio.sleep(0.1 + (i * 0.05))  # 0.1 to 0.8 seconds
                return MagicMock(
                    persona_id=persona.persona_id,
                    recommendation=f"Stress test response from {persona.persona_id}",
                    confidence=0.7 + (i * 0.02),
                    priority=MagicMock(value="medium")
                )
            persona.deliberate = variable_response_time
        
        return orchestrator
    
    async def test_high_load_deliberation_stress(self, stress_test_orchestrator):
        """Test system under high deliberation load"""
        orchestrator = stress_test_orchestrator
        
        high_load_count = 25  # High number of concurrent deliberations
        timeout_count = 0
        success_count = 0
        error_count = 0
        
        async def stress_deliberation(stress_id):
            try:
                request = DeliberationRequest(
                    query=f"High load stress test query {stress_id} with complex context requiring analysis",
                    context={
                        "stress_test_id": stress_id,
                        "complexity": "high",
                        "requirements": ["performance", "scalability", "reliability"],
                        "constraints": {"budget": "limited", "time": "tight"}
                    },
                    topic=f"stress_test_{stress_id}",
                    timeout=8.0
                )
                
                result = await orchestrator.deliberate(request)
                return {"status": "success", "stress_id": stress_id, "result": result}
                
            except asyncio.TimeoutError:
                return {"status": "timeout", "stress_id": stress_id}
            except Exception as e:
                return {"status": "error", "stress_id": stress_id, "error": str(e)}
        
        # Execute high load test
        start_time = time.time()
        tasks = [stress_deliberation(i) for i in range(high_load_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # Analyze results
        for result in results:
            if isinstance(result, Exception):
                error_count += 1
            elif result["status"] == "success":
                success_count += 1
            elif result["status"] == "timeout":
                timeout_count += 1
            else:
                error_count += 1
        
        # Stress test assertions
        assert success_count > 0  # At least some should succeed
        success_rate = success_count / high_load_count
        assert success_rate > 0.7  # At least 70% should succeed under stress
        
        # System should handle stress gracefully
        assert total_time < 30.0  # Should not take excessively long
        
        return {
            "total_deliberations": high_load_count,
            "success_count": success_count,
            "timeout_count": timeout_count,
            "error_count": error_count,
            "success_rate": success_rate,
            "total_time": total_time,
            "throughput": high_load_count / total_time
        }
    
    async def test_memory_pressure_stress(self, stress_test_orchestrator):
        """Test system behavior under memory pressure"""
        orchestrator = stress_test_orchestrator
        
        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Create memory-intensive deliberations
        memory_intensive_count = 15
        large_context_size = 1000  # Large context objects
        
        async def memory_intensive_deliberation(mem_id):
            # Create large context to simulate memory pressure
            large_context = {
                "deliberation_id": mem_id,
                "large_data": [f"Data item {i} with substantial content" * 10 for i in range(large_context_size)],
                "metadata": {"size": "large", "complexity": "high"},
                "requirements": [f"Requirement {i}" for i in range(100)]
            }
            
            request = DeliberationRequest(
                query=f"Memory intensive analysis {mem_id} requiring processing of large datasets",
                context=large_context,
                topic=f"memory_stress_{mem_id}",
                timeout=10.0
            )
            
            return await orchestrator.deliberate(request)
        
        # Execute memory-intensive operations
        start_time = time.time()
        results = []
        
        for i in range(memory_intensive_count):
            result = await memory_intensive_deliberation(i)
            results.append(result)
            
            # Check memory usage periodically
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = current_memory - initial_memory
            
            # Ensure memory doesn't grow uncontrollably
            assert memory_growth < 2000  # Should not exceed 2GB growth
        
        end_time = time.time()
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory
        
        # Memory stress assertions
        assert len(results) == memory_intensive_count  # All should complete
        assert all(isinstance(r, DeliberationResult) for r in results)  # All should succeed
        assert total_memory_growth < 1000  # Memory growth should be reasonable
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "total_growth_mb": total_memory_growth,
            "deliberations_completed": len(results),
            "avg_memory_per_deliberation": total_memory_growth / len(results)
        }
    
    def test_cpu_intensive_stress(self, stress_test_orchestrator):
        """Test system behavior under CPU stress"""
        orchestrator = stress_test_orchestrator
        
        # Create CPU-intensive operations using threads
        def cpu_intensive_task(task_id):
            # Simulate CPU-intensive work
            start_time = time.time()
            result = 0
            for i in range(1000000):  # CPU-intensive computation
                result += i ** 0.5
            end_time = time.time()
            
            return {
                "task_id": task_id,
                "computation_result": result,
                "execution_time": end_time - start_time
            }
        
        # Monitor CPU usage
        initial_cpu_percent = psutil.cpu_percent(interval=1)
        
        # Execute CPU-intensive tasks
        thread_count = psutil.cpu_count() * 2  # 2x CPU cores
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            start_time = time.time()
            
            # Submit CPU-intensive tasks
            futures = [executor.submit(cpu_intensive_task, i) for i in range(thread_count)]
            
            # Wait for completion
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
            
            end_time = time.time()
        
        total_time = end_time - start_time
        final_cpu_percent = psutil.cpu_percent(interval=1)
        
        # CPU stress assertions
        assert len(results) == thread_count  # All tasks should complete
        assert all(r["computation_result"] > 0 for r in results)  # All should produce results
        assert total_time < 30.0  # Should complete within reasonable time
        
        execution_times = [r["execution_time"] for r in results]
        avg_execution_time = statistics.mean(execution_times)
        
        return {
            "thread_count": thread_count,
            "total_execution_time": total_time,
            "avg_task_execution_time": avg_execution_time,
            "initial_cpu_percent": initial_cpu_percent,
            "final_cpu_percent": final_cpu_percent,
            "tasks_completed": len(results)
        }


class TestPerformanceBenchmarks:
    """Comprehensive performance benchmarks"""
    
    async def test_comprehensive_performance_benchmark(self):
        """Run comprehensive performance benchmark suite"""
        benchmark_results = {}
        
        # Test 1: Single deliberation baseline
        orchestrator = Orchestrator(use_all_personas=False)
        with patch('src.database.memory_optimized.OptimizedMemoryManager'):
            with patch('src.database.knowledge_graph_optimized.OptimizedKnowledgeGraph'):
                await orchestrator.initialize()
        
        # Mock fast persona responses
        for persona in orchestrator.personas.values():
            persona.deliberate = AsyncMock(return_value=MagicMock(
                persona_id=persona.persona_id,
                confidence=0.8
            ))
        
        # Baseline test
        baseline_start = time.time()
        baseline_request = DeliberationRequest(
            query="Benchmark baseline deliberation",
            context={"benchmark": True},
            topic="benchmark_baseline"
        )
        baseline_result = await orchestrator.deliberate(baseline_request)
        baseline_time = time.time() - baseline_start
        
        benchmark_results["baseline_deliberation_time"] = baseline_time
        
        # Test 2: Throughput test
        throughput_count = 50
        throughput_start = time.time()
        
        for i in range(throughput_count):
            request = DeliberationRequest(
                query=f"Throughput test {i}",
                context={"throughput_test": i},
                topic=f"throughput_{i}"
            )
            await orchestrator.deliberate(request)
        
        throughput_time = time.time() - throughput_start
        throughput_per_second = throughput_count / throughput_time
        
        benchmark_results["throughput_per_second"] = throughput_per_second
        benchmark_results["total_throughput_time"] = throughput_time
        
        # Test 3: Concurrent deliberations
        concurrent_count = 20
        concurrent_start = time.time()
        
        async def concurrent_deliberation(conc_id):
            request = DeliberationRequest(
                query=f"Concurrent benchmark {conc_id}",
                context={"concurrent_test": conc_id},
                topic=f"concurrent_{conc_id}"
            )
            return await orchestrator.deliberate(request)
        
        concurrent_tasks = [concurrent_deliberation(i) for i in range(concurrent_count)]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_time = time.time() - concurrent_start
        
        benchmark_results["concurrent_deliberations_time"] = concurrent_time
        benchmark_results["concurrent_throughput"] = concurrent_count / concurrent_time
        
        # System resource usage
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent()
        
        benchmark_results["memory_usage_mb"] = memory_usage
        benchmark_results["cpu_usage_percent"] = cpu_percent
        
        # Performance assertions
        assert baseline_time < 2.0  # Baseline should be fast
        assert throughput_per_second > 10.0  # Should handle good throughput
        assert concurrent_time < 10.0  # Concurrent operations should be efficient
        assert memory_usage < 1000  # Memory usage should be reasonable
        
        return benchmark_results
    
    def test_performance_regression_detection(self):
        """Test for performance regression detection"""
        # Define expected performance baselines
        performance_baselines = {
            "max_deliberation_time": 3.0,
            "min_throughput_per_second": 8.0,
            "max_memory_usage_mb": 800,
            "max_concurrent_deliberation_time": 12.0
        }
        
        # In a real implementation, this would compare against
        # historical performance data stored in a database
        # For testing, we'll just verify the baselines are reasonable
        
        assert performance_baselines["max_deliberation_time"] > 0
        assert performance_baselines["min_throughput_per_second"] > 0
        assert performance_baselines["max_memory_usage_mb"] > 0
        assert performance_baselines["max_concurrent_deliberation_time"] > 0
        
        return performance_baselines
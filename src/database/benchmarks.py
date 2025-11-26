"""
Database Performance Benchmarks

Comprehensive benchmarking suite for validating database optimizations
and measuring performance improvements across all database systems.
"""

import asyncio
import time
import statistics
import random
import string
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import uuid
import logging
from contextlib import asynccontextmanager

from .config import get_database_manager, DatabaseManager
from .memory_optimized import OptimizedMemorySystem, Memory
from .knowledge_graph_optimized import OptimizedKnowledgeGraph, NodeType, EdgeType
from .postgres_optimized import get_postgres_optimizer
from .redis_cache import get_cache_manager
from .performance_monitor import get_performance_monitor


@dataclass
class BenchmarkResult:
    """Single benchmark test result"""
    test_name: str
    operation_type: str
    database_system: str
    execution_time_ms: float
    operations_per_second: float
    memory_usage_mb: float
    success_rate: float
    additional_metrics: Dict[str, Any]
    timestamp: datetime


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results"""
    suite_name: str
    results: List[BenchmarkResult]
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    summary_stats: Dict[str, Any]


class DatabaseBenchmark:
    """
    Comprehensive database benchmarking framework with:
    - Performance testing for all database systems
    - Load testing with concurrent operations
    - Scalability testing with increasing data volumes
    - Comparison testing before/after optimizations
    - Memory and resource usage monitoring
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_database_manager()
        self.logger = logging.getLogger("benchmark")
        
        # Test data generators
        self.test_personas = ["analyst", "creator", "guardian", "strategist", "scholar"]
        self.test_content_templates = [
            "Analyzed project {} with complexity score {}",
            "Created solution for {} using approach {}",
            "Identified security concern in {} module {}",
            "Strategic decision made regarding {} with priority {}",
            "Research completed on {} topic with findings {}"
        ]
        
        # Benchmark configurations
        self.small_dataset_size = 100
        self.medium_dataset_size = 1000
        self.large_dataset_size = 10000
        self.stress_dataset_size = 50000
    
    async def run_comprehensive_benchmark(self) -> BenchmarkSuite:
        """Run comprehensive benchmark suite across all systems"""
        start_time = datetime.now()
        results = []
        
        self.logger.info("Starting comprehensive database benchmark suite")
        
        # Memory System Benchmarks
        self.logger.info("Benchmarking Memory System...")
        memory_results = await self._benchmark_memory_system()
        results.extend(memory_results)
        
        # Knowledge Graph Benchmarks
        self.logger.info("Benchmarking Knowledge Graph...")
        graph_results = await self._benchmark_knowledge_graph()
        results.extend(graph_results)
        
        # PostgreSQL Benchmarks
        self.logger.info("Benchmarking PostgreSQL...")
        postgres_results = await self._benchmark_postgresql()
        results.extend(postgres_results)
        
        # Redis Cache Benchmarks
        self.logger.info("Benchmarking Redis Cache...")
        redis_results = await self._benchmark_redis_cache()
        results.extend(redis_results)
        
        # Concurrent Load Tests
        self.logger.info("Running concurrent load tests...")
        load_results = await self._benchmark_concurrent_operations()
        results.extend(load_results)
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Generate summary statistics
        summary_stats = self._generate_summary_stats(results)
        
        suite = BenchmarkSuite(
            suite_name="Comprehensive Database Benchmark",
            results=results,
            start_time=start_time,
            end_time=end_time,
            total_duration_seconds=total_duration,
            summary_stats=summary_stats
        )
        
        self.logger.info(f"Benchmark suite completed in {total_duration:.2f} seconds")
        return suite
    
    async def _benchmark_memory_system(self) -> List[BenchmarkResult]:
        """Benchmark Memory System performance"""
        results = []
        memory_system = OptimizedMemorySystem(self.db_manager)
        
        # Test: Bulk Memory Storage
        memories_data = []
        for i in range(self.medium_dataset_size):
            persona_id = random.choice(self.test_personas)
            content = random.choice(self.test_content_templates).format(
                f"project_{i}", random.randint(1, 10)
            )
            context = {"test_id": i, "benchmark": True}
            importance = random.uniform(0.1, 1.0)
            emotional_valence = random.uniform(-1.0, 1.0)
            tags = {f"tag_{j}" for j in range(random.randint(1, 5))}
            
            memories_data.append((persona_id, content, context, importance, emotional_valence, tags))
        
        # Bulk insert benchmark
        start_time = time.time()
        stored_memories = await memory_system.store_memory_batch(memories_data)
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000
        ops_per_second = len(memories_data) / max(end_time - start_time, 0.001)
        
        results.append(BenchmarkResult(
            test_name="Memory Bulk Insert",
            operation_type="INSERT",
            database_system="SQLite Memory",
            execution_time_ms=execution_time_ms,
            operations_per_second=ops_per_second,
            memory_usage_mb=0,  # TODO: Implement memory tracking
            success_rate=len(stored_memories) / len(memories_data),
            additional_metrics={
                "records_inserted": len(stored_memories),
                "batch_size": len(memories_data)
            },
            timestamp=datetime.now()
        ))
        
        # Test: Memory Recall Performance
        recall_times = []
        for _ in range(50):
            persona_id = random.choice(self.test_personas)
            query = f"project analysis complexity"
            context = {"test": True}
            
            start_time = time.time()
            recalled_memories = await memory_system.recall_optimized(
                persona_id, query, context, limit=20
            )
            end_time = time.time()
            
            recall_times.append((end_time - start_time) * 1000)
        
        avg_recall_time = statistics.mean(recall_times)
        
        results.append(BenchmarkResult(
            test_name="Memory Recall Performance",
            operation_type="SELECT",
            database_system="SQLite Memory",
            execution_time_ms=avg_recall_time,
            operations_per_second=1000 / avg_recall_time,
            memory_usage_mb=0,
            success_rate=1.0,
            additional_metrics={
                "min_recall_time_ms": min(recall_times),
                "max_recall_time_ms": max(recall_times),
                "std_dev_ms": statistics.stdev(recall_times)
            },
            timestamp=datetime.now()
        ))
        
        # Test: Memory Compression
        start_time = time.time()
        await memory_system.compress_old_memories(age_days=0)  # Compress all for testing
        end_time = time.time()
        
        results.append(BenchmarkResult(
            test_name="Memory Compression",
            operation_type="COMPRESS",
            database_system="SQLite Memory",
            execution_time_ms=(end_time - start_time) * 1000,
            operations_per_second=0,  # Not applicable
            memory_usage_mb=0,
            success_rate=1.0,
            additional_metrics={},
            timestamp=datetime.now()
        ))
        
        return results
    
    async def _benchmark_knowledge_graph(self) -> List[BenchmarkResult]:
        """Benchmark Knowledge Graph performance"""
        results = []
        graph = OptimizedKnowledgeGraph(self.db_manager)
        
        # Test: Bulk Node Creation
        nodes_data = []
        for i in range(self.medium_dataset_size):
            name = f"Node_{i}"
            node_type = random.choice(list(NodeType))
            attributes = {"test_id": i, "category": f"cat_{i % 10}"}
            importance = random.uniform(0.1, 1.0)
            
            nodes_data.append((name, node_type, attributes, importance))
        
        start_time = time.time()
        created_nodes = await graph.add_node_batch(nodes_data)
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000
        ops_per_second = len(nodes_data) / max(end_time - start_time, 0.001)
        
        results.append(BenchmarkResult(
            test_name="Graph Node Bulk Insert",
            operation_type="INSERT",
            database_system="SQLite Graph",
            execution_time_ms=execution_time_ms,
            operations_per_second=ops_per_second,
            memory_usage_mb=0,
            success_rate=len(created_nodes) / len(nodes_data),
            additional_metrics={
                "nodes_created": len(created_nodes),
                "batch_size": len(nodes_data)
            },
            timestamp=datetime.now()
        ))
        
        # Test: Bulk Edge Creation
        edges_data = []
        node_ids = [node.id for node in created_nodes]
        
        for _ in range(self.medium_dataset_size // 2):
            source_id = random.choice(node_ids)
            target_id = random.choice(node_ids)
            if source_id != target_id:
                edge_type = random.choice(list(EdgeType))
                weight = random.uniform(0.1, 1.0)
                confidence = random.uniform(0.5, 1.0)
                
                edges_data.append((source_id, target_id, edge_type, weight, confidence, {}))
        
        start_time = time.time()
        created_edges = await graph.add_edge_batch(edges_data)
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000
        ops_per_second = len(edges_data) / max(end_time - start_time, 0.001)
        
        results.append(BenchmarkResult(
            test_name="Graph Edge Bulk Insert",
            operation_type="INSERT",
            database_system="SQLite Graph",
            execution_time_ms=execution_time_ms,
            operations_per_second=ops_per_second,
            memory_usage_mb=0,
            success_rate=len(created_edges) / len(edges_data),
            additional_metrics={
                "edges_created": len(created_edges),
                "batch_size": len(edges_data)
            },
            timestamp=datetime.now()
        ))
        
        # Test: Graph Traversal Performance
        traversal_times = []
        for _ in range(20):
            node_id = random.choice(node_ids)
            
            start_time = time.time()
            related = await graph.find_related_optimized(
                node_id, max_depth=2, min_weight=0.1
            )
            end_time = time.time()
            
            traversal_times.append((end_time - start_time) * 1000)
        
        avg_traversal_time = statistics.mean(traversal_times)
        
        results.append(BenchmarkResult(
            test_name="Graph Traversal Performance",
            operation_type="SELECT",
            database_system="SQLite Graph",
            execution_time_ms=avg_traversal_time,
            operations_per_second=1000 / avg_traversal_time,
            memory_usage_mb=0,
            success_rate=1.0,
            additional_metrics={
                "min_traversal_time_ms": min(traversal_times),
                "max_traversal_time_ms": max(traversal_times),
                "std_dev_ms": statistics.stdev(traversal_times)
            },
            timestamp=datetime.now()
        ))
        
        # Test: Centrality Calculation
        start_time = time.time()
        centrality = await graph.calculate_centrality_optimized("betweenness")
        end_time = time.time()
        
        results.append(BenchmarkResult(
            test_name="Graph Centrality Calculation",
            operation_type="COMPUTE",
            database_system="SQLite Graph",
            execution_time_ms=(end_time - start_time) * 1000,
            operations_per_second=len(centrality) / max(end_time - start_time, 0.001),
            memory_usage_mb=0,
            success_rate=1.0,
            additional_metrics={
                "nodes_processed": len(centrality),
                "centrality_type": "betweenness"
            },
            timestamp=datetime.now()
        ))
        
        return results
    
    async def _benchmark_postgresql(self) -> List[BenchmarkResult]:
        """Benchmark PostgreSQL performance"""
        results = []
        optimizer = get_postgres_optimizer()
        
        # Test: Dashboard Query Performance
        dashboard_times = []
        for _ in range(20):
            start_time = time.time()
            dashboard_data = await optimizer.get_project_dashboard_data(limit=50)
            end_time = time.time()
            
            dashboard_times.append((end_time - start_time) * 1000)
        
        avg_dashboard_time = statistics.mean(dashboard_times)
        
        results.append(BenchmarkResult(
            test_name="PostgreSQL Dashboard Query",
            operation_type="SELECT",
            database_system="PostgreSQL",
            execution_time_ms=avg_dashboard_time,
            operations_per_second=1000 / avg_dashboard_time,
            memory_usage_mb=0,
            success_rate=1.0,
            additional_metrics={
                "min_query_time_ms": min(dashboard_times),
                "max_query_time_ms": max(dashboard_times),
                "std_dev_ms": statistics.stdev(dashboard_times)
            },
            timestamp=datetime.now()
        ))
        
        # Test: Bulk Metrics Insert
        metrics_data = []
        for i in range(self.medium_dataset_size):
            metrics_data.append({
                "project_id": str(uuid.uuid4()),
                "metric_type": random.choice(["cpu_usage", "memory_usage", "response_time"]),
                "value": random.uniform(0, 100),
                "unit": "percent",
                "metadata": {"test": True},
                "timestamp": datetime.now() - timedelta(minutes=random.randint(0, 60))
            })
        
        start_time = time.time()
        inserted_count = await optimizer.batch_insert_metrics(metrics_data)
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000
        ops_per_second = inserted_count / max(end_time - start_time, 0.001)
        
        results.append(BenchmarkResult(
            test_name="PostgreSQL Bulk Metrics Insert",
            operation_type="INSERT",
            database_system="PostgreSQL",
            execution_time_ms=execution_time_ms,
            operations_per_second=ops_per_second,
            memory_usage_mb=0,
            success_rate=inserted_count / len(metrics_data),
            additional_metrics={
                "records_inserted": inserted_count,
                "batch_size": len(metrics_data)
            },
            timestamp=datetime.now()
        ))
        
        # Test: Error Pattern Analysis
        start_time = time.time()
        error_insights = await optimizer.get_error_pattern_insights(days=7)
        end_time = time.time()
        
        results.append(BenchmarkResult(
            test_name="PostgreSQL Error Analysis",
            operation_type="SELECT",
            database_system="PostgreSQL",
            execution_time_ms=(end_time - start_time) * 1000,
            operations_per_second=len(error_insights) / max(end_time - start_time, 0.001),
            memory_usage_mb=0,
            success_rate=1.0,
            additional_metrics={
                "patterns_analyzed": len(error_insights)
            },
            timestamp=datetime.now()
        ))
        
        return results
    
    async def _benchmark_redis_cache(self) -> List[BenchmarkResult]:
        """Benchmark Redis Cache performance"""
        results = []
        cache_manager = get_cache_manager()
        await cache_manager.initialize()
        
        # Test: Cache Set Performance
        cache_data = {}
        for i in range(self.medium_dataset_size):
            key = f"benchmark_key_{i}"
            value = {
                "id": i,
                "data": "test_data_" * 10,  # ~100 bytes
                "timestamp": datetime.now().isoformat()
            }
            cache_data[key] = value
        
        start_time = time.time()
        success = await cache_manager.cache.mset(cache_data, ttl=3600)
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000
        ops_per_second = len(cache_data) / max(end_time - start_time, 0.001)
        
        results.append(BenchmarkResult(
            test_name="Redis Cache Bulk Set",
            operation_type="SET",
            database_system="Redis",
            execution_time_ms=execution_time_ms,
            operations_per_second=ops_per_second,
            memory_usage_mb=0,
            success_rate=1.0 if success else 0.0,
            additional_metrics={
                "items_cached": len(cache_data),
                "avg_item_size_bytes": 100
            },
            timestamp=datetime.now()
        ))
        
        # Test: Cache Get Performance
        keys_to_get = list(cache_data.keys())
        get_times = []
        
        for _ in range(50):
            sample_keys = random.sample(keys_to_get, min(20, len(keys_to_get)))
            
            start_time = time.time()
            cached_values = await cache_manager.cache.mget(sample_keys)
            end_time = time.time()
            
            get_times.append((end_time - start_time) * 1000)
        
        avg_get_time = statistics.mean(get_times)
        
        results.append(BenchmarkResult(
            test_name="Redis Cache Bulk Get",
            operation_type="GET",
            database_system="Redis",
            execution_time_ms=avg_get_time,
            operations_per_second=20 / (avg_get_time / 1000),  # 20 keys per operation
            memory_usage_mb=0,
            success_rate=1.0,
            additional_metrics={
                "min_get_time_ms": min(get_times),
                "max_get_time_ms": max(get_times),
                "std_dev_ms": statistics.stdev(get_times)
            },
            timestamp=datetime.now()
        ))
        
        # Test: Cache Hit Ratio
        hit_count = 0
        miss_count = 0
        
        for _ in range(100):
            # 80% existing keys, 20% non-existing
            if random.random() < 0.8:
                key = random.choice(keys_to_get)
                result = await cache_manager.cache.get(key)
                if result:
                    hit_count += 1
                else:
                    miss_count += 1
            else:
                key = f"non_existing_key_{random.randint(100000, 999999)}"
                result = await cache_manager.cache.get(key)
                miss_count += 1
        
        hit_ratio = hit_count / (hit_count + miss_count)
        
        results.append(BenchmarkResult(
            test_name="Redis Cache Hit Ratio Test",
            operation_type="GET",
            database_system="Redis",
            execution_time_ms=0,  # Not relevant for this test
            operations_per_second=0,  # Not relevant for this test
            memory_usage_mb=0,
            success_rate=hit_ratio,
            additional_metrics={
                "hit_count": hit_count,
                "miss_count": miss_count,
                "hit_ratio": hit_ratio
            },
            timestamp=datetime.now()
        ))
        
        return results
    
    async def _benchmark_concurrent_operations(self) -> List[BenchmarkResult]:
        """Benchmark concurrent database operations"""
        results = []
        
        # Test: Concurrent Memory Operations
        async def memory_operation(persona_id: str, operation_id: int):
            memory_system = OptimizedMemorySystem(self.db_manager)
            content = f"Concurrent operation {operation_id} for {persona_id}"
            context = {"concurrent_test": True, "operation_id": operation_id}
            
            # Store memory
            await memory_system.store_memory(
                persona_id, content, context, 
                importance=random.uniform(0.5, 1.0)
            )
            
            # Recall memories
            await memory_system.recall_optimized(
                persona_id, "concurrent operation", context, limit=10
            )
        
        concurrent_tasks = []
        start_time = time.time()
        
        for i in range(50):  # 50 concurrent operations
            persona_id = random.choice(self.test_personas)
            task = asyncio.create_task(memory_operation(persona_id, i))
            concurrent_tasks.append(task)
        
        await asyncio.gather(*concurrent_tasks)
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000
        ops_per_second = len(concurrent_tasks) / max(end_time - start_time, 0.001)
        
        results.append(BenchmarkResult(
            test_name="Concurrent Memory Operations",
            operation_type="CONCURRENT",
            database_system="SQLite Memory",
            execution_time_ms=execution_time_ms,
            operations_per_second=ops_per_second,
            memory_usage_mb=0,
            success_rate=1.0,
            additional_metrics={
                "concurrent_operations": len(concurrent_tasks),
                "avg_time_per_operation_ms": execution_time_ms / len(concurrent_tasks)
            },
            timestamp=datetime.now()
        ))
        
        return results
    
    def _generate_summary_stats(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate summary statistics for benchmark results"""
        stats = {
            "total_tests": len(results),
            "by_database": {},
            "by_operation": {},
            "performance_summary": {}
        }
        
        # Group by database system
        for result in results:
            db_name = result.database_system
            if db_name not in stats["by_database"]:
                stats["by_database"][db_name] = {
                    "test_count": 0,
                    "avg_execution_time_ms": 0,
                    "total_operations_per_second": 0,
                    "avg_success_rate": 0
                }
            
            db_stats = stats["by_database"][db_name]
            db_stats["test_count"] += 1
            db_stats["avg_execution_time_ms"] += result.execution_time_ms
            db_stats["total_operations_per_second"] += result.operations_per_second
            db_stats["avg_success_rate"] += result.success_rate
        
        # Calculate averages
        for db_name, db_stats in stats["by_database"].items():
            test_count = db_stats["test_count"]
            db_stats["avg_execution_time_ms"] /= test_count
            db_stats["avg_operations_per_second"] = db_stats["total_operations_per_second"] / test_count
            db_stats["avg_success_rate"] /= test_count
            del db_stats["total_operations_per_second"]  # Remove intermediate calculation
        
        # Group by operation type
        op_types = {}
        for result in results:
            op_type = result.operation_type
            if op_type not in op_types:
                op_types[op_type] = []
            op_types[op_type].append(result.execution_time_ms)
        
        for op_type, times in op_types.items():
            stats["by_operation"][op_type] = {
                "test_count": len(times),
                "avg_time_ms": statistics.mean(times),
                "min_time_ms": min(times),
                "max_time_ms": max(times),
                "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0
            }
        
        # Overall performance summary
        all_times = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        all_ops_per_sec = [r.operations_per_second for r in results if r.operations_per_second > 0]
        all_success_rates = [r.success_rate for r in results]
        
        if all_times:
            stats["performance_summary"] = {
                "avg_execution_time_ms": statistics.mean(all_times),
                "median_execution_time_ms": statistics.median(all_times),
                "p95_execution_time_ms": sorted(all_times)[int(len(all_times) * 0.95)] if all_times else 0,
                "avg_operations_per_second": statistics.mean(all_ops_per_sec) if all_ops_per_sec else 0,
                "overall_success_rate": statistics.mean(all_success_rates),
                "fastest_operation_ms": min(all_times),
                "slowest_operation_ms": max(all_times)
            }
        
        return stats
    
    def export_benchmark_results(self, suite: BenchmarkSuite, output_file: str):
        """Export benchmark results to JSON file"""
        # Convert to serializable format
        export_data = {
            "suite_name": suite.suite_name,
            "start_time": suite.start_time.isoformat(),
            "end_time": suite.end_time.isoformat(),
            "total_duration_seconds": suite.total_duration_seconds,
            "summary_stats": suite.summary_stats,
            "results": []
        }
        
        for result in suite.results:
            export_data["results"].append({
                "test_name": result.test_name,
                "operation_type": result.operation_type,
                "database_system": result.database_system,
                "execution_time_ms": result.execution_time_ms,
                "operations_per_second": result.operations_per_second,
                "memory_usage_mb": result.memory_usage_mb,
                "success_rate": result.success_rate,
                "additional_metrics": result.additional_metrics,
                "timestamp": result.timestamp.isoformat()
            })
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Benchmark results exported to {output_file}")
    
    def print_benchmark_summary(self, suite: BenchmarkSuite):
        """Print a formatted summary of benchmark results"""
        print("\n" + "="*80)
        print(f"DATABASE BENCHMARK SUITE: {suite.suite_name}")
        print("="*80)
        print(f"Duration: {suite.total_duration_seconds:.2f} seconds")
        print(f"Total Tests: {suite.summary_stats['total_tests']}")
        print()
        
        # Performance summary
        if "performance_summary" in suite.summary_stats:
            perf = suite.summary_stats["performance_summary"]
            print("PERFORMANCE SUMMARY:")
            print(f"  Average Execution Time: {perf.get('avg_execution_time_ms', 0):.2f} ms")
            print(f"  Median Execution Time:  {perf.get('median_execution_time_ms', 0):.2f} ms")
            print(f"  95th Percentile:        {perf.get('p95_execution_time_ms', 0):.2f} ms")
            print(f"  Average Ops/Second:     {perf.get('avg_operations_per_second', 0):.2f}")
            print(f"  Overall Success Rate:   {perf.get('overall_success_rate', 0)*100:.1f}%")
            print()
        
        # Database breakdown
        print("BY DATABASE SYSTEM:")
        for db_name, db_stats in suite.summary_stats["by_database"].items():
            print(f"  {db_name}:")
            print(f"    Tests:           {db_stats['test_count']}")
            print(f"    Avg Time:        {db_stats['avg_execution_time_ms']:.2f} ms")
            print(f"    Avg Ops/Sec:     {db_stats['avg_operations_per_second']:.2f}")
            print(f"    Success Rate:    {db_stats['avg_success_rate']*100:.1f}%")
            print()
        
        # Operation breakdown
        print("BY OPERATION TYPE:")
        for op_type, op_stats in suite.summary_stats["by_operation"].items():
            print(f"  {op_type}:")
            print(f"    Tests:        {op_stats['test_count']}")
            print(f"    Avg Time:     {op_stats['avg_time_ms']:.2f} ms")
            print(f"    Min Time:     {op_stats['min_time_ms']:.2f} ms")
            print(f"    Max Time:     {op_stats['max_time_ms']:.2f} ms")
            print(f"    Std Dev:      {op_stats['std_dev_ms']:.2f} ms")
            print()
        
        print("="*80)


async def run_performance_validation():
    """Run performance validation and benchmarks"""
    print("Initializing database connections...")
    db_manager = get_database_manager()
    await db_manager.initialize()
    
    print("Starting performance validation...")
    benchmark = DatabaseBenchmark(db_manager)
    
    # Run comprehensive benchmark
    results = await benchmark.run_comprehensive_benchmark()
    
    # Print results
    benchmark.print_benchmark_summary(results)
    
    # Export results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"benchmark_results_{timestamp}.json"
    benchmark.export_benchmark_results(results, output_file)
    
    return results


if __name__ == "__main__":
    asyncio.run(run_performance_validation())
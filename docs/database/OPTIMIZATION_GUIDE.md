# Database Optimization Documentation

This directory contains comprehensive documentation for the Optimus Council of Minds database optimization system.

## Overview

The Optimus database architecture has been completely optimized to handle the demands of a 13+ persona system with extensive memory storage, complex knowledge graphs, and real-time performance monitoring. The system includes multiple database technologies working together to provide high-performance, scalable data management.

## Architecture

### Database Systems

1. **PostgreSQL (Main Application Database)**
   - Project management and orchestration data
   - Runtime monitoring and status tracking
   - Analysis results and performance metrics
   - Error pattern tracking with ML features

2. **SQLite Memory System**
   - Optimized for persona memory storage
   - Advanced indexing for fast recall
   - Compression for old memories
   - Batch operations for high throughput

3. **SQLite Knowledge Graph**
   - Persistent graph storage with NetworkX compatibility
   - Advanced graph traversal algorithms
   - Centrality calculations and community detection
   - Subgraph caching for performance

4. **Redis Cache Layer**
   - Distributed caching with intelligent serialization
   - Multiple cache strategies (LRU, LFU, TTL)
   - Compression for large objects
   - Domain-specific caching configurations

### Key Features

- **Unified Connection Management**: Single configuration point for all databases
- **Connection Pooling**: Optimized connection pools for each database type
- **Advanced Indexing**: Query-optimized indexes for all common access patterns
- **Performance Monitoring**: Real-time monitoring with alerting and recommendations
- **Migration System**: Comprehensive migration framework with rollback capabilities
- **Caching Layer**: Intelligent multi-tier caching with automatic invalidation
- **Benchmarking Suite**: Performance validation and regression testing

## Quick Start

### 1. Initialize the Database System

```bash
# Full initialization with migrations and optimizations
python -m src.database.initialize --mode=full

# Quick health check
python -m src.database.initialize --mode=health-check

# Cleanup (for shutdown)
python -m src.database.initialize --mode=cleanup
```

### 2. Configuration

The system is configured through environment variables or the unified configuration system:

```python
from src.database.config import get_database_manager, DatabaseConfig

# Use default configuration
db_manager = get_database_manager()

# Or custom configuration
config = DatabaseConfig(
    postgres_url="postgresql+asyncpg://user:pass@host:port/db",
    redis_url="redis://host:port/db",
    memory_db_path="data/memory/optimus_memory.db",
    knowledge_db_path="data/knowledge/optimus_knowledge.db"
)

db_manager = DatabaseManager(config)
await db_manager.initialize()
```

### 3. Using Optimized Systems

#### Memory System

```python
from src.database.memory_optimized import OptimizedMemorySystem

memory_system = OptimizedMemorySystem()

# Store memories in batches for better performance
memories_data = [
    (persona_id, content, context, importance, emotional_valence, tags),
    # ... more memories
]
memories = await memory_system.store_memory_batch(memories_data)

# Optimized recall with caching
recalled_memories = await memory_system.recall_optimized(
    persona_id="analyst",
    query="project analysis",
    context={"domain": "technical"},
    limit=10
)
```

#### Knowledge Graph

```python
from src.database.knowledge_graph_optimized import OptimizedKnowledgeGraph
from src.database.knowledge_graph_optimized import NodeType, EdgeType

graph = OptimizedKnowledgeGraph()

# Batch node creation
nodes_data = [
    ("Node Name", NodeType.CONCEPT, {"attr": "value"}, 0.8),
    # ... more nodes
]
nodes = await graph.add_node_batch(nodes_data)

# Optimized graph traversal with caching
related = await graph.find_related_optimized(
    node_id="some_node_id",
    max_depth=2,
    edge_types=[EdgeType.RELATES_TO, EdgeType.INFLUENCES],
    min_weight=0.3
)
```

## Performance Benchmarks

### Expected Performance

Based on the optimization benchmarks:

- **Memory Recall**: < 100ms for typical queries
- **Graph Traversal**: < 500ms for depth-2 traversals
- **Dashboard Queries**: < 2s for complex aggregations
- **Cache Operations**: < 10ms for typical get/set operations
- **Bulk Operations**: > 1000 ops/second for batch inserts

### Scalability Targets

The optimized system is designed to handle:

- **Memory System**: 1M+ memories per persona
- **Knowledge Graph**: 100K+ nodes, 1M+ edges
- **PostgreSQL**: 10M+ projects and metrics
- **Cache**: 10GB+ with intelligent eviction
- **Concurrent Users**: 100+ simultaneous connections

## Integration with Council of Minds

The optimized database system is designed to integrate seamlessly with the existing Council of Minds architecture. See the full documentation at `/docs/database/README.md` for complete integration guides and best practices.
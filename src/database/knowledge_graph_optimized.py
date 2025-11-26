"""
Optimized Knowledge Graph System

High-performance graph database with persistent storage, advanced indexing,
caching, and graph algorithms for the Council of Minds knowledge representation.
Supports both SQLite with graph extensions and Neo4j for scalability.
"""

import json
import sqlite3
import asyncio
import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import numpy as np
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor
import pickle
import zlib
import base64

from .config import get_database_manager, DatabaseManager


class NodeType(Enum):
    """Enhanced node types for the knowledge graph"""
    CONCEPT = "concept"
    PERSON = "person" 
    PROJECT = "project"
    SKILL = "skill"
    GOAL = "goal"
    EXPERIENCE = "experience"
    EMOTION = "emotion"
    VALUE = "value"
    RESOURCE = "resource"
    LOCATION = "location"
    ACTIVITY = "activity"
    HEALTH = "health"
    LEARNING = "learning"
    DECISION = "decision"
    PATTERN = "pattern"           # For learned patterns
    INSIGHT = "insight"           # For generated insights
    RELATIONSHIP = "relationship" # For interpersonal relationships
    WORKFLOW = "workflow"         # For process flows
    TOOL = "tool"                 # For software tools and technologies


class EdgeType(Enum):
    """Enhanced edge types for relationships"""
    RELATES_TO = "relates_to"
    CAUSES = "causes"
    REQUIRES = "requires"
    CONFLICTS_WITH = "conflicts_with"
    SUPPORTS = "supports"
    PART_OF = "part_of"
    LEADS_TO = "leads_to"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    INFLUENCES = "influences"
    BELONGS_TO = "belongs_to"
    LOCATED_AT = "located_at"
    OCCURS_DURING = "occurs_during"
    LEARNED_FROM = "learned_from"
    EMOTIONAL_LINK = "emotional_link"
    IMPLEMENTS = "implements"     # For implementation relationships
    USES = "uses"                 # For usage relationships
    CONTAINS = "contains"         # For containment relationships
    TRIGGERS = "triggers"         # For trigger relationships
    DERIVES_FROM = "derives_from" # For derivation relationships


@dataclass
class Node:
    """Optimized node with caching and versioning support"""
    id: str
    name: str
    node_type: NodeType
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    importance: float = 0.5
    activation_level: float = 0.0
    personas_relevance: Dict[str, float] = field(default_factory=dict)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    version: int = 1
    embedding_vector: Optional[List[float]] = None  # For semantic similarity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'node_type': self.node_type.value,
            'attributes': self.attributes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'importance': self.importance,
            'activation_level': self.activation_level,
            'personas_relevance': self.personas_relevance,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'version': self.version,
            'embedding_vector': self.embedding_vector
        }


@dataclass
class Edge:
    """Optimized edge with performance metadata"""
    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    confidence: float = 0.5
    last_reinforced: Optional[datetime] = None
    reinforcement_count: int = 1
    decay_rate: float = 0.01
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'edge_type': self.edge_type.value,
            'weight': self.weight,
            'attributes': self.attributes,
            'created_at': self.created_at.isoformat(),
            'confidence': self.confidence,
            'last_reinforced': self.last_reinforced.isoformat() if self.last_reinforced else None,
            'reinforcement_count': self.reinforcement_count,
            'decay_rate': self.decay_rate
        }


class GraphCache:
    """High-performance caching layer for graph operations"""
    
    def __init__(self, max_size: int = 10000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._access_order: deque = deque()
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if (datetime.now() - timestamp).seconds < self.ttl:
                    # Move to end for LRU
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    return value
                else:
                    # Expired
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
        return None
    
    def put(self, key: str, value: Any):
        with self._lock:
            # Remove if already exists
            if key in self._cache:
                self._access_order.remove(key)
            
            # Evict if at capacity
            while len(self._cache) >= self.max_size and self._access_order:
                oldest_key = self._access_order.popleft()
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
            
            self._cache[key] = (value, datetime.now())
            self._access_order.append(key)
    
    def invalidate(self, key: str):
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
    
    def clear(self):
        with self._lock:
            self._cache.clear()
            self._access_order.clear()


class OptimizedKnowledgeGraph:
    """
    High-performance knowledge graph with persistent storage and advanced features:
    - Persistent SQLite storage with graph optimizations
    - Connection pooling and transaction management
    - Advanced caching layer for frequent operations
    - Batch operations for bulk inserts/updates
    - Graph algorithm optimizations
    - Subgraph caching and materialized views
    - Semantic similarity with embeddings
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, cache_size: int = 10000):
        self.db_manager = db_manager or get_database_manager()
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.cache = GraphCache(max_size=cache_size)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._batch_queue: List[Tuple[str, Any]] = []
        self._batch_size = 100
        self._lock = threading.Lock()
        
        # Performance tracking
        self.query_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'db_queries': 0,
            'batch_operations': 0
        }
        
        self._init_database()
        self._load_graph()
    
    def _init_database(self):
        """Initialize optimized SQLite database with graph-specific optimizations"""
        conn = self.db_manager.get_knowledge_connection()
        cursor = conn.cursor()
        
        # Enable graph-friendly optimizations
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL") 
        cursor.execute("PRAGMA cache_size=50000")  # Larger cache for graph queries
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA recursive_triggers=ON")  # For graph operations
        
        # Optimized nodes table with graph-specific fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                node_type TEXT NOT NULL,
                attributes TEXT,
                created_at TEXT,
                updated_at TEXT,
                created_at_unix INTEGER NOT NULL,
                updated_at_unix INTEGER NOT NULL,
                importance REAL DEFAULT 0.5,
                personas_relevance TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                last_accessed_unix INTEGER,
                version INTEGER DEFAULT 1,
                embedding_vector BLOB,  -- Serialized embedding
                name_lower TEXT,  -- For case-insensitive searches
                search_terms TEXT -- For full-text search
            )
        ''')
        
        # Advanced indexing for graph traversal
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_importance ON nodes(importance DESC)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_access ON nodes(access_count DESC)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_name_lower ON nodes(name_lower)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at_unix DESC)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_updated ON nodes(updated_at_unix DESC)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_version ON nodes(version)",
            
            # Composite indexes for common patterns
            "CREATE INDEX IF NOT EXISTS idx_nodes_type_importance ON nodes(node_type, importance DESC)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_type_access ON nodes(node_type, access_count DESC)",
            "CREATE INDEX IF NOT EXISTS idx_nodes_recent_important ON nodes(updated_at_unix DESC, importance DESC)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Optimized edges table for graph traversal
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                attributes TEXT,
                created_at TEXT,
                created_at_unix INTEGER NOT NULL,
                confidence REAL DEFAULT 0.5,
                last_reinforced TEXT,
                last_reinforced_unix INTEGER,
                reinforcement_count INTEGER DEFAULT 1,
                decay_rate REAL DEFAULT 0.01,
                FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
            )
        ''')
        
        # Critical indexes for graph traversal performance
        edge_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)",
            "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)",
            "CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type)",
            "CREATE INDEX IF NOT EXISTS idx_edges_weight ON edges(weight DESC)",
            "CREATE INDEX IF NOT EXISTS idx_edges_confidence ON edges(confidence DESC)",
            "CREATE INDEX IF NOT EXISTS idx_edges_reinforced ON edges(last_reinforced_unix DESC)",
            
            # Graph traversal optimized indexes
            "CREATE INDEX IF NOT EXISTS idx_edges_source_type ON edges(source_id, edge_type)",
            "CREATE INDEX IF NOT EXISTS idx_edges_target_type ON edges(target_id, edge_type)",
            "CREATE INDEX IF NOT EXISTS idx_edges_bidirectional ON edges(source_id, target_id)",
            "CREATE INDEX IF NOT EXISTS idx_edges_type_weight ON edges(edge_type, weight DESC)",
            "CREATE INDEX IF NOT EXISTS idx_edges_source_weight ON edges(source_id, weight DESC)",
            "CREATE INDEX IF NOT EXISTS idx_edges_target_weight ON edges(target_id, weight DESC)",
            
            # Performance indexes for graph algorithms
            "CREATE INDEX IF NOT EXISTS idx_edges_graph_traversal ON edges(source_id, edge_type, weight DESC)",
            "CREATE INDEX IF NOT EXISTS idx_edges_reverse_traversal ON edges(target_id, edge_type, weight DESC)"
        ]
        
        for index_sql in edge_indexes:
            cursor.execute(index_sql)
        
        # Materialized views for common graph patterns
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS node_connectivity AS
            SELECT 
                n.id,
                n.name,
                n.node_type,
                n.importance,
                COUNT(DISTINCT e1.target_id) as out_degree,
                COUNT(DISTINCT e2.source_id) as in_degree,
                COUNT(DISTINCT e1.target_id) + COUNT(DISTINCT e2.source_id) as total_degree,
                AVG(e1.weight) as avg_out_weight,
                AVG(e2.weight) as avg_in_weight
            FROM nodes n
            LEFT JOIN edges e1 ON n.id = e1.source_id
            LEFT JOIN edges e2 ON n.id = e2.target_id
            GROUP BY n.id, n.name, n.node_type, n.importance
        ''')
        
        # Graph statistics table for performance monitoring
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS graph_stats (
                id INTEGER PRIMARY KEY,
                total_nodes INTEGER,
                total_edges INTEGER,
                avg_node_degree REAL,
                max_node_degree INTEGER,
                graph_density REAL,
                connected_components INTEGER,
                largest_component_size INTEGER,
                calculated_at TEXT,
                calculated_at_unix INTEGER
            )
        ''')
        
        # Subgraph cache table for frequently accessed subgraphs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subgraph_cache (
                cache_key TEXT PRIMARY KEY,
                subgraph_data BLOB,
                node_count INTEGER,
                edge_count INTEGER,
                created_at TEXT,
                created_at_unix INTEGER,
                access_count INTEGER DEFAULT 1,
                last_accessed TEXT
            )
        ''')
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subgraph_cache_access ON subgraph_cache(access_count DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subgraph_cache_created ON subgraph_cache(created_at_unix DESC)")
        
        # Triggers for automatic maintenance
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_node_access
            AFTER UPDATE OF access_count ON nodes
            FOR EACH ROW
            BEGIN
                UPDATE nodes SET 
                    last_accessed = datetime('now'),
                    last_accessed_unix = strftime('%s', 'now')
                WHERE id = NEW.id;
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_edge_reinforcement
            AFTER UPDATE OF reinforcement_count ON edges
            FOR EACH ROW
            BEGIN
                UPDATE edges SET 
                    last_reinforced = datetime('now'),
                    last_reinforced_unix = strftime('%s', 'now')
                WHERE id = NEW.id;
            END
        ''')
        
        conn.commit()
        self.db_manager.return_knowledge_connection(conn)
    
    def _load_graph(self, limit: int = 50000):
        """Load graph with memory-efficient streaming"""
        conn = self.db_manager.get_knowledge_connection()
        cursor = conn.cursor()
        
        # Load nodes in batches ordered by importance
        cursor.execute('''
            SELECT id, name, node_type, attributes, created_at, updated_at, 
                   importance, personas_relevance, access_count, last_accessed, 
                   version, embedding_vector
            FROM nodes 
            ORDER BY importance DESC, access_count DESC
            LIMIT ?
        ''', (limit,))
        
        nodes_loaded = 0
        for row in cursor.fetchall():
            try:
                # Deserialize embedding if present
                embedding_vector = None
                if row[11]:
                    try:
                        embedding_vector = pickle.loads(row[11])
                    except:
                        embedding_vector = None
                
                node = Node(
                    id=row[0],
                    name=row[1],
                    node_type=NodeType(row[2]),
                    attributes=json.loads(row[3]) if row[3] else {},
                    created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                    updated_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    importance=row[6] if row[6] else 0.5,
                    personas_relevance=json.loads(row[7]) if row[7] else {},
                    access_count=row[8] if row[8] else 0,
                    last_accessed=datetime.fromisoformat(row[9]) if row[9] else None,
                    version=row[10] if row[10] else 1,
                    embedding_vector=embedding_vector
                )
                
                self.nodes[node.id] = node
                self.graph.add_node(node.id, node=node)
                nodes_loaded += 1
                
            except Exception as e:
                print(f"Error loading node {row[0]}: {e}")
        
        # Load edges for loaded nodes only
        node_ids = list(self.nodes.keys())
        if node_ids:
            # Use batch loading for edges
            batch_size = 1000
            for i in range(0, len(node_ids), batch_size):
                batch_ids = node_ids[i:i+batch_size]
                placeholders = ','.join(['?' for _ in batch_ids])
                
                cursor.execute(f'''
                    SELECT id, source_id, target_id, edge_type, weight, attributes, 
                           created_at, confidence, last_reinforced, reinforcement_count, decay_rate
                    FROM edges 
                    WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders})
                    ORDER BY weight DESC, confidence DESC
                ''', batch_ids + batch_ids)
                
                for row in cursor.fetchall():
                    try:
                        edge = Edge(
                            id=row[0],
                            source_id=row[1],
                            target_id=row[2],
                            edge_type=EdgeType(row[3]),
                            weight=row[4] if row[4] else 1.0,
                            attributes=json.loads(row[5]) if row[5] else {},
                            created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                            confidence=row[7] if row[7] else 0.5,
                            last_reinforced=datetime.fromisoformat(row[8]) if row[8] else None,
                            reinforcement_count=row[9] if row[9] else 1,
                            decay_rate=row[10] if row[10] else 0.01
                        )
                        
                        # Only add if both nodes exist
                        if edge.source_id in self.nodes and edge.target_id in self.nodes:
                            self.edges[edge.id] = edge
                            self.graph.add_edge(edge.source_id, edge.target_id, 
                                              edge_id=edge.id, edge=edge, weight=edge.weight)
                    
                    except Exception as e:
                        print(f"Error loading edge {row[0]}: {e}")
        
        self.db_manager.return_knowledge_connection(conn)
        print(f"Loaded {nodes_loaded} nodes and {len(self.edges)} edges into memory")
    
    async def add_node_batch(self, nodes_data: List[Tuple[str, NodeType, Optional[Dict[str, Any]], float]]) -> List[Node]:
        """Add multiple nodes in a batch operation"""
        if not nodes_data:
            return []
        
        nodes = []
        timestamp = datetime.now()
        
        for name, node_type, attributes, importance in nodes_data:
            # Generate node ID
            node_id = hashlib.md5(f"{name}{node_type.value}".encode()).hexdigest()[:16]
            
            # Check if already exists
            if node_id in self.nodes:
                nodes.append(self.nodes[node_id])
                continue
            
            node = Node(
                id=node_id,
                name=name,
                node_type=node_type,
                attributes=attributes or {},
                importance=importance,
                created_at=timestamp,
                updated_at=timestamp
            )
            
            nodes.append(node)
            self.nodes[node_id] = node
            self.graph.add_node(node_id, node=node)
        
        # Batch persist to database
        await self._persist_nodes_batch(nodes)
        
        self.query_stats['batch_operations'] += 1
        return nodes
    
    async def add_node(self,
                      name: str,
                      node_type: NodeType,
                      attributes: Optional[Dict[str, Any]] = None,
                      importance: float = 0.5) -> Node:
        """Add a single node with batching optimization"""
        nodes = await self.add_node_batch([(name, node_type, attributes, importance)])
        return nodes[0] if nodes else None
    
    async def add_edge_batch(self, edges_data: List[Tuple[str, str, EdgeType, float, float, Optional[Dict[str, Any]]]]) -> List[Edge]:
        """Add multiple edges in a batch operation"""
        if not edges_data:
            return []
        
        edges = []
        timestamp = datetime.now()
        
        for source_id, target_id, edge_type, weight, confidence, attributes in edges_data:
            # Verify nodes exist
            if source_id not in self.nodes or target_id not in self.nodes:
                continue
            
            # Generate edge ID
            edge_id = hashlib.md5(f"{source_id}{target_id}{edge_type.value}".encode()).hexdigest()[:16]
            
            # Check if already exists
            if edge_id in self.edges:
                existing_edge = self.edges[edge_id]
                existing_edge.weight = (existing_edge.weight + weight) / 2
                existing_edge.confidence = max(existing_edge.confidence, confidence)
                existing_edge.reinforcement_count += 1
                existing_edge.last_reinforced = timestamp
                edges.append(existing_edge)
                continue
            
            edge = Edge(
                id=edge_id,
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                weight=weight,
                confidence=confidence,
                attributes=attributes or {},
                created_at=timestamp
            )
            
            edges.append(edge)
            self.edges[edge_id] = edge
            self.graph.add_edge(source_id, target_id, edge_id=edge_id, edge=edge, weight=weight)
        
        # Batch persist to database
        await self._persist_edges_batch(edges)
        
        self.query_stats['batch_operations'] += 1
        return edges
    
    async def find_related_optimized(self,
                                   node_id: str,
                                   max_depth: int = 2,
                                   edge_types: Optional[List[EdgeType]] = None,
                                   min_weight: float = 0.1) -> Dict[str, Any]:
        """Optimized graph traversal with caching and database assistance"""
        
        # Check cache first
        cache_key = f"related_{node_id}_{max_depth}_{edge_types}_{min_weight}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.query_stats['cache_hits'] += 1
            return cached_result
        
        self.query_stats['cache_misses'] += 1
        
        if node_id not in self.nodes:
            return {'nodes': [], 'edges': []}
        
        # For deep traversals, use database-assisted search
        if max_depth > 2 or len(self.graph.nodes()) > 10000:
            result = await self._find_related_database(node_id, max_depth, edge_types, min_weight)
        else:
            result = await self._find_related_memory(node_id, max_depth, edge_types, min_weight)
        
        # Cache the result
        self.cache.put(cache_key, result)
        return result
    
    async def _find_related_database(self, node_id: str, max_depth: int, edge_types: Optional[List[EdgeType]], min_weight: float) -> Dict[str, Any]:
        """Database-assisted graph traversal for large graphs"""
        conn = self.db_manager.get_knowledge_connection()
        cursor = conn.cursor()
        
        # Use recursive CTE for graph traversal
        edge_type_filter = ""
        params = [node_id, min_weight]
        
        if edge_types:
            edge_type_placeholders = ','.join(['?' for _ in edge_types])
            edge_type_filter = f"AND e.edge_type IN ({edge_type_placeholders})"
            params.extend([et.value for et in edge_types])
        
        params.append(max_depth)
        
        # Recursive graph traversal query
        traversal_query = f'''
            WITH RECURSIVE graph_traversal(node_id, depth, path) AS (
                -- Base case
                SELECT ?, 0, ?
                
                UNION ALL
                
                -- Recursive case
                SELECT 
                    e.target_id,
                    gt.depth + 1,
                    gt.path || ',' || e.target_id
                FROM graph_traversal gt
                JOIN edges e ON gt.node_id = e.source_id
                WHERE gt.depth < ?
                  AND e.weight >= ?
                  {edge_type_filter}
                  AND e.target_id NOT IN (
                      SELECT value FROM json_each('[' || gt.path || ']')
                  )  -- Avoid cycles
            )
            SELECT DISTINCT 
                n.id, n.name, n.node_type, n.importance,
                gt.depth, gt.path
            FROM graph_traversal gt
            JOIN nodes n ON gt.node_id = n.id
            WHERE gt.depth > 0
            ORDER BY gt.depth, n.importance DESC
            LIMIT 1000
        '''
        
        cursor.execute(traversal_query, [node_id, node_id] + params)
        related_nodes = []
        
        for row in cursor.fetchall():
            if row[0] in self.nodes:
                related_nodes.append(self.nodes[row[0]])
        
        # Get edges between found nodes
        if related_nodes:
            node_ids = [node_id] + [n.id for n in related_nodes]
            placeholders = ','.join(['?' for _ in node_ids])
            
            cursor.execute(f'''
                SELECT e.id, e.source_id, e.target_id, e.edge_type, e.weight, e.confidence
                FROM edges e
                WHERE e.source_id IN ({placeholders}) 
                  AND e.target_id IN ({placeholders})
                  AND e.weight >= ?
                ORDER BY e.weight DESC
            ''', node_ids + node_ids + [min_weight])
            
            related_edges = []
            for row in cursor.fetchall():
                if row[0] in self.edges:
                    related_edges.append(self.edges[row[0]])
        else:
            related_edges = []
        
        self.db_manager.return_knowledge_connection(conn)
        self.query_stats['db_queries'] += 1
        
        return {'nodes': related_nodes, 'edges': related_edges}
    
    async def _find_related_memory(self, node_id: str, max_depth: int, edge_types: Optional[List[EdgeType]], min_weight: float) -> Dict[str, Any]:
        """Memory-based graph traversal for smaller graphs"""
        related = {'nodes': [], 'edges': []}
        visited = set()
        queue = [(node_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            if depth > 0 and current_id in self.nodes:
                related['nodes'].append(self.nodes[current_id])
                # Update access count
                self.nodes[current_id].access_count += 1
                self.nodes[current_id].last_accessed = datetime.now()
            
            # Get neighbors
            if current_id in self.graph:
                for neighbor_id in self.graph.neighbors(current_id):
                    if neighbor_id in visited:
                        continue
                    
                    edge_data = self.graph[current_id][neighbor_id]
                    edge = edge_data['edge']
                    
                    # Filter by edge type and weight
                    if edge_types and edge.edge_type not in edge_types:
                        continue
                    if edge.weight < min_weight:
                        continue
                    
                    related['edges'].append(edge)
                    
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, depth + 1))
        
        return related
    
    async def spreading_activation_optimized(self,
                                           seed_nodes: List[str],
                                           iterations: int = 3,
                                           decay: float = 0.5,
                                           min_activation: float = 0.1) -> Dict[str, float]:
        """Optimized spreading activation with early termination and batch updates"""
        
        # Check cache
        cache_key = f"activation_{sorted(seed_nodes)}_{iterations}_{decay}_{min_activation}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.query_stats['cache_hits'] += 1
            return cached_result
        
        self.query_stats['cache_misses'] += 1
        
        # Initialize activation levels
        activations = defaultdict(float)
        
        # Set initial activation
        for node_id in seed_nodes:
            if node_id in self.nodes:
                activations[node_id] = 1.0
        
        # Spread activation with early termination
        for iteration in range(iterations):
            new_activations = defaultdict(float)
            changed_nodes = 0
            
            for node_id, activation in list(activations.items()):
                if activation < min_activation:
                    continue
                
                # Spread to neighbors
                if node_id in self.graph:
                    for neighbor_id in self.graph.neighbors(node_id):
                        edge_data = self.graph[node_id][neighbor_id]
                        edge = edge_data['edge']
                        
                        spread = activation * edge.weight * decay
                        if spread >= min_activation:
                            new_activations[neighbor_id] += spread
                            changed_nodes += 1
            
            # Apply new activations
            for node_id, activation in new_activations.items():
                activations[node_id] = min(1.0, activation)
            
            # Early termination if no significant changes
            if changed_nodes < 5:
                break
        
        # Filter and sort results
        result = {
            node_id: activation 
            for node_id, activation in activations.items()
            if activation >= min_activation
        }
        
        result = dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        
        # Cache result
        self.cache.put(cache_key, result)
        
        return result
    
    async def calculate_centrality_optimized(self, centrality_type: str = 'betweenness') -> Dict[str, float]:
        """Optimized centrality calculation with caching and sampling"""
        
        cache_key = f"centrality_{centrality_type}_{len(self.graph.nodes())}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.query_stats['cache_hits'] += 1
            return cached_result
        
        self.query_stats['cache_misses'] += 1
        
        # For large graphs, use approximation algorithms
        if len(self.graph.nodes()) > 5000:
            if centrality_type == 'betweenness':
                # Use approximate betweenness centrality
                k = min(1000, len(self.graph.nodes()) // 10)
                centrality = nx.betweenness_centrality(self.graph, k=k)
            else:
                # Use degree centrality as fallback for large graphs
                centrality = nx.degree_centrality(self.graph)
        else:
            # Exact algorithms for smaller graphs
            if centrality_type == 'betweenness':
                centrality = nx.betweenness_centrality(self.graph)
            elif centrality_type == 'closeness':
                centrality = nx.closeness_centrality(self.graph)
            elif centrality_type == 'eigenvector':
                try:
                    centrality = nx.eigenvector_centrality(self.graph, max_iter=200)
                except:
                    centrality = nx.degree_centrality(self.graph)
            else:
                centrality = nx.degree_centrality(self.graph)
        
        # Update node importance based on centrality
        for node_id, score in centrality.items():
            if node_id in self.nodes:
                # Blend with existing importance
                self.nodes[node_id].importance = (
                    self.nodes[node_id].importance * 0.7 + score * 0.3
                )
        
        # Cache result
        self.cache.put(cache_key, centrality)
        
        return centrality
    
    async def get_subgraph_optimized(self,
                                   node_types: Optional[List[NodeType]] = None,
                                   edge_types: Optional[List[EdgeType]] = None,
                                   min_importance: float = 0.0,
                                   max_nodes: int = 1000) -> nx.DiGraph:
        """Get optimized subgraph with caching"""
        
        # Generate cache key
        cache_key = f"subgraph_{node_types}_{edge_types}_{min_importance}_{max_nodes}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.query_stats['cache_hits'] += 1
            return cached_result
        
        self.query_stats['cache_misses'] += 1
        
        # Use database query for large graphs
        if len(self.graph.nodes()) > 5000:
            subgraph = await self._get_subgraph_database(node_types, edge_types, min_importance, max_nodes)
        else:
            subgraph = await self._get_subgraph_memory(node_types, edge_types, min_importance, max_nodes)
        
        # Cache result
        self.cache.put(cache_key, subgraph)
        
        return subgraph
    
    async def _get_subgraph_database(self, node_types, edge_types, min_importance, max_nodes) -> nx.DiGraph:
        """Database-assisted subgraph extraction"""
        conn = self.db_manager.get_knowledge_connection()
        cursor = conn.cursor()
        
        # Build node filter
        node_filter = ""
        params = [min_importance]
        
        if node_types:
            type_placeholders = ','.join(['?' for _ in node_types])
            node_filter = f"AND node_type IN ({type_placeholders})"
            params.extend([nt.value for nt in node_types])
        
        params.append(max_nodes)
        
        # Get filtered nodes
        cursor.execute(f'''
            SELECT id, name, node_type, importance, attributes
            FROM nodes 
            WHERE importance >= ? {node_filter}
            ORDER BY importance DESC, access_count DESC
            LIMIT ?
        ''', params)
        
        filtered_nodes = {}
        for row in cursor.fetchall():
            if row[0] in self.nodes:
                filtered_nodes[row[0]] = self.nodes[row[0]]
        
        if not filtered_nodes:
            self.db_manager.return_knowledge_connection(conn)
            return nx.DiGraph()
        
        # Get edges between filtered nodes
        node_ids = list(filtered_nodes.keys())
        placeholders = ','.join(['?' for _ in node_ids])
        
        edge_filter = ""
        edge_params = node_ids + node_ids
        
        if edge_types:
            edge_type_placeholders = ','.join(['?' for _ in edge_types])
            edge_filter = f"AND edge_type IN ({edge_type_placeholders})"
            edge_params.extend([et.value for et in edge_types])
        
        cursor.execute(f'''
            SELECT id, source_id, target_id, edge_type, weight, confidence
            FROM edges
            WHERE source_id IN ({placeholders}) 
              AND target_id IN ({placeholders}) {edge_filter}
        ''', edge_params)
        
        # Create subgraph
        subgraph = nx.DiGraph()
        
        # Add nodes
        for node_id, node in filtered_nodes.items():
            subgraph.add_node(node_id, node=node)
        
        # Add edges
        for row in cursor.fetchall():
            if row[0] in self.edges:
                edge = self.edges[row[0]]
                subgraph.add_edge(edge.source_id, edge.target_id, 
                                edge_id=edge.id, edge=edge, weight=edge.weight)
        
        self.db_manager.return_knowledge_connection(conn)
        self.query_stats['db_queries'] += 1
        
        return subgraph
    
    async def _get_subgraph_memory(self, node_types, edge_types, min_importance, max_nodes) -> nx.DiGraph:
        """Memory-based subgraph extraction"""
        # Filter nodes
        filtered_nodes = []
        for node_id, node in self.nodes.items():
            if node_types and node.node_type not in node_types:
                continue
            if node.importance < min_importance:
                continue
            filtered_nodes.append(node_id)
        
        # Limit nodes by importance
        filtered_nodes.sort(key=lambda nid: self.nodes[nid].importance, reverse=True)
        filtered_nodes = filtered_nodes[:max_nodes]
        
        # Create subgraph
        subgraph = self.graph.subgraph(filtered_nodes).copy()
        
        # Filter edges if specified
        if edge_types:
            edges_to_remove = []
            for u, v, data in subgraph.edges(data=True):
                if 'edge' in data and data['edge'].edge_type not in edge_types:
                    edges_to_remove.append((u, v))
            subgraph.remove_edges_from(edges_to_remove)
        
        return subgraph
    
    async def _persist_nodes_batch(self, nodes: List[Node]):
        """Persist multiple nodes in a single transaction"""
        if not nodes:
            return
        
        conn = self.db_manager.get_knowledge_connection()
        cursor = conn.cursor()
        
        batch_data = []
        for node in nodes:
            # Serialize embedding if present
            embedding_blob = None
            if node.embedding_vector:
                embedding_blob = pickle.dumps(node.embedding_vector)
            
            timestamp_unix = int(node.created_at.timestamp())
            updated_unix = int(node.updated_at.timestamp())
            last_accessed_unix = int(node.last_accessed.timestamp()) if node.last_accessed else None
            
            batch_data.append((
                node.id,
                node.name,
                node.node_type.value,
                json.dumps(node.attributes),
                node.created_at.isoformat(),
                node.updated_at.isoformat(),
                timestamp_unix,
                updated_unix,
                node.importance,
                json.dumps(node.personas_relevance),
                node.access_count,
                node.last_accessed.isoformat() if node.last_accessed else None,
                last_accessed_unix,
                node.version,
                embedding_blob,
                node.name.lower(),
                ' '.join([node.name.lower(), node.node_type.value] + 
                        [str(v).lower() for v in node.attributes.values() if isinstance(v, (str, int, float))])
            ))
        
        cursor.executemany('''
            INSERT OR REPLACE INTO nodes 
            (id, name, node_type, attributes, created_at, updated_at, created_at_unix, updated_at_unix,
             importance, personas_relevance, access_count, last_accessed, last_accessed_unix, 
             version, embedding_vector, name_lower, search_terms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch_data)
        
        conn.commit()
        self.db_manager.return_knowledge_connection(conn)
    
    async def _persist_edges_batch(self, edges: List[Edge]):
        """Persist multiple edges in a single transaction"""
        if not edges:
            return
        
        conn = self.db_manager.get_knowledge_connection()
        cursor = conn.cursor()
        
        batch_data = []
        for edge in edges:
            timestamp_unix = int(edge.created_at.timestamp())
            reinforced_unix = int(edge.last_reinforced.timestamp()) if edge.last_reinforced else None
            
            batch_data.append((
                edge.id,
                edge.source_id,
                edge.target_id,
                edge.edge_type.value,
                edge.weight,
                json.dumps(edge.attributes),
                edge.created_at.isoformat(),
                timestamp_unix,
                edge.confidence,
                edge.last_reinforced.isoformat() if edge.last_reinforced else None,
                reinforced_unix,
                edge.reinforcement_count,
                edge.decay_rate
            ))
        
        cursor.executemany('''
            INSERT OR REPLACE INTO edges 
            (id, source_id, target_id, edge_type, weight, attributes, created_at, created_at_unix,
             confidence, last_reinforced, last_reinforced_unix, reinforcement_count, decay_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch_data)
        
        conn.commit()
        self.db_manager.return_knowledge_connection(conn)
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics with caching"""
        cache_key = "graph_stats"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        stats = {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'avg_node_degree': 0,
            'max_node_degree': 0,
            'graph_density': 0,
            'node_types': defaultdict(int),
            'edge_types': defaultdict(int),
            'performance': self.query_stats.copy(),
            'cache_efficiency': 0
        }
        
        if self.graph.nodes():
            # Calculate degree statistics
            degrees = [self.graph.degree(node) for node in self.graph.nodes()]
            stats['avg_node_degree'] = sum(degrees) / len(degrees)
            stats['max_node_degree'] = max(degrees) if degrees else 0
            
            # Calculate density
            n = len(self.graph.nodes())
            m = len(self.graph.edges())
            stats['graph_density'] = m / (n * (n - 1)) if n > 1 else 0
        
        # Count node types
        for node in self.nodes.values():
            stats['node_types'][node.node_type.value] += 1
        
        # Count edge types
        for edge in self.edges.values():
            stats['edge_types'][edge.edge_type.value] += 1
        
        # Calculate cache efficiency
        total_queries = stats['performance']['cache_hits'] + stats['performance']['cache_misses']
        if total_queries > 0:
            stats['cache_efficiency'] = stats['performance']['cache_hits'] / total_queries * 100
        
        # Cache the result
        self.cache.put(cache_key, stats)
        
        return stats
    
    def clear_cache(self):
        """Clear the performance cache"""
        self.cache.clear()
        self.query_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'db_queries': 0,
            'batch_operations': 0
        }
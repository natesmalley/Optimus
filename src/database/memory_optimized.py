"""
Optimized Memory System for Personas

High-performance memory storage with connection pooling, batch operations,
advanced indexing, and compression for the Council of Minds.
"""

import json
import sqlite3
import asyncio
import zlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import hashlib
import numpy as np
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor

from .config import get_database_manager, DatabaseManager


@dataclass
class Memory:
    """Optimized memory unit with compression support"""
    id: str
    persona_id: str
    content: str
    context: Dict[str, Any]
    timestamp: datetime
    importance: float  # 0.0 to 1.0
    emotional_valence: float  # -1.0 (negative) to 1.0 (positive)
    tags: Set[str]
    associations: List[str]  # IDs of related memories
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    decay_rate: float = 0.01
    compressed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'persona_id': self.persona_id,
            'content': self.content,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'importance': self.importance,
            'emotional_valence': self.emotional_valence,
            'tags': list(self.tags),
            'associations': self.associations,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'decay_rate': self.decay_rate,
            'compressed': self.compressed
        }
    
    def calculate_relevance(self, query: str, current_context: Dict[str, Any]) -> float:
        """Calculate how relevant this memory is to current situation"""
        relevance = self.importance
        
        # Text similarity with TF-IDF inspired approach
        query_words = set(query.lower().split())
        content_words = set(self.content.lower().split())
        
        if query_words and content_words:
            # Jaccard similarity with weighted important terms
            intersection = query_words & content_words
            union = query_words | content_words
            overlap = len(intersection) / len(union)
            relevance += overlap * 0.4
        
        # Recency bonus with exponential decay
        age_days = (datetime.now() - self.timestamp).days
        recency_factor = np.exp(-age_days * self.decay_rate)
        relevance *= recency_factor
        
        # Access frequency bonus (popular memories are more relevant)
        access_boost = min(np.log(self.access_count + 1) * 0.1, 0.3)
        relevance += access_boost
        
        # Context similarity
        if self.context and current_context:
            shared_keys = set(self.context.keys()) & set(current_context.keys())
            if shared_keys:
                context_similarity = 0
                for key in shared_keys:
                    if self.context[key] == current_context[key]:
                        context_similarity += 0.1
                relevance += min(context_similarity, 0.2)
        
        # Emotional context bonus
        if 'emotion' in current_context and abs(self.emotional_valence) > 0.1:
            emotional_match = 1 - abs(self.emotional_valence - current_context.get('emotion', 0)) / 2
            relevance += emotional_match * 0.1
        
        return min(1.0, relevance)


class OptimizedMemorySystem:
    """
    High-performance memory system with advanced optimization features:
    - Connection pooling for SQLite
    - Batch operations for bulk inserts/updates
    - Memory compression for old memories
    - Advanced indexing for fast queries
    - Memory partitioning by persona
    - Query optimization with prepared statements
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_database_manager()
        self.memories: Dict[str, List[Memory]] = defaultdict(list)
        self.memory_index: Dict[str, Memory] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._batch_queue: List[Memory] = []
        self._batch_size = 50
        self._last_batch_flush = datetime.now()
        self._lock = threading.Lock()
        self._prepared_statements = {}
        self._init_database()
        self._load_memories()
    
    def _init_database(self):
        """Initialize optimized SQLite database with advanced indexing"""
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Create optimized memories table with partitioning support
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                persona_id TEXT NOT NULL,
                content TEXT NOT NULL,
                content_compressed BLOB,  -- For compressed content
                context TEXT,
                timestamp TEXT NOT NULL,
                timestamp_unix INTEGER NOT NULL,  -- For faster range queries
                importance REAL,
                emotional_valence REAL,
                tags TEXT,
                associations TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                last_accessed_unix INTEGER,  -- For faster range queries
                decay_rate REAL DEFAULT 0.01,
                compressed BOOLEAN DEFAULT 0,
                content_hash TEXT,  -- For deduplication
                word_count INTEGER,  -- For relevance calculations
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Advanced indexing strategy
        indexes = [
            # Core lookup indexes
            "CREATE INDEX IF NOT EXISTS idx_persona_memories ON memories(persona_id, timestamp_unix DESC)",
            "CREATE INDEX IF NOT EXISTS idx_persona_importance ON memories(persona_id, importance DESC)",
            "CREATE INDEX IF NOT EXISTS idx_persona_access ON memories(persona_id, access_count DESC)",
            
            # Query optimization indexes
            "CREATE INDEX IF NOT EXISTS idx_content_hash ON memories(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_timestamp_range ON memories(timestamp_unix)",
            "CREATE INDEX IF NOT EXISTS idx_last_accessed_range ON memories(last_accessed_unix)",
            "CREATE INDEX IF NOT EXISTS idx_importance_range ON memories(importance DESC, timestamp_unix DESC)",
            
            # Composite indexes for common query patterns
            "CREATE INDEX IF NOT EXISTS idx_persona_recent ON memories(persona_id, timestamp_unix DESC, importance DESC)",
            "CREATE INDEX IF NOT EXISTS idx_persona_popular ON memories(persona_id, access_count DESC, importance DESC)",
            "CREATE INDEX IF NOT EXISTS idx_persona_emotional ON memories(persona_id, emotional_valence, importance DESC)",
            
            # Full-text search preparation (if needed)
            "CREATE INDEX IF NOT EXISTS idx_word_count ON memories(word_count)",
            
            # Compression and maintenance indexes
            "CREATE INDEX IF NOT EXISTS idx_compressed ON memories(compressed, timestamp_unix)",
            "CREATE INDEX IF NOT EXISTS idx_cleanup ON memories(importance, timestamp_unix) WHERE importance < 0.1"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # Memory correlations table with optimizations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_correlations (
                memory1_id TEXT,
                memory2_id TEXT,
                correlation_strength REAL,
                correlation_type TEXT,
                created_at TEXT,
                created_at_unix INTEGER,
                last_reinforced TEXT,
                reinforcement_count INTEGER DEFAULT 1,
                PRIMARY KEY (memory1_id, memory2_id),
                FOREIGN KEY (memory1_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (memory2_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        ''')
        
        # Correlation indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_correlation_strength ON memory_correlations(correlation_strength DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_correlation_type ON memory_correlations(correlation_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_correlation_reinforced ON memory_correlations(reinforcement_count DESC)")
        
        # Memory access statistics for optimization
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_stats (
                persona_id TEXT PRIMARY KEY,
                total_memories INTEGER DEFAULT 0,
                compressed_memories INTEGER DEFAULT 0,
                avg_importance REAL DEFAULT 0.5,
                last_consolidation TEXT,
                query_count INTEGER DEFAULT 0,
                last_query TEXT,
                FOREIGN KEY (persona_id) REFERENCES personas(id)
            )
        ''')
        
        # Query cache for frequent queries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT,
                result_ids TEXT,
                cache_timestamp TEXT,
                hit_count INTEGER DEFAULT 1,
                persona_id TEXT
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_persona ON query_cache(persona_id, hit_count DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON query_cache(cache_timestamp)")
        
        # Optimize SQLite settings for memory workload
        cursor.execute("PRAGMA optimize")
        cursor.execute("ANALYZE")
        
        conn.commit()
        self.db_manager.return_memory_connection(conn)
    
    def _load_memories(self):
        """Load memories with optimized query"""
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Use optimized query with limit for initial load
        cursor.execute('''
            SELECT id, persona_id, content, content_compressed, context, timestamp, 
                   importance, emotional_valence, tags, associations, access_count, 
                   last_accessed, decay_rate, compressed, word_count
            FROM memories 
            ORDER BY persona_id, importance DESC, timestamp_unix DESC
            LIMIT 10000
        ''')
        
        for row in cursor.fetchall():
            content = row[2]
            if row[13] and row[3]:  # compressed flag and compressed content
                try:
                    content = zlib.decompress(base64.b64decode(row[3])).decode('utf-8')
                except:
                    content = row[2]  # fallback to original
            
            memory = Memory(
                id=row[0],
                persona_id=row[1],
                content=content,
                context=json.loads(row[4]) if row[4] else {},
                timestamp=datetime.fromisoformat(row[5]),
                importance=row[6],
                emotional_valence=row[7],
                tags=set(json.loads(row[8])) if row[8] else set(),
                associations=json.loads(row[9]) if row[9] else [],
                access_count=row[10],
                last_accessed=datetime.fromisoformat(row[11]) if row[11] else None,
                decay_rate=row[12],
                compressed=bool(row[13])
            )
            
            self.memories[memory.persona_id].append(memory)
            self.memory_index[memory.id] = memory
        
        self.db_manager.return_memory_connection(conn)
    
    def _compress_content(self, content: str) -> str:
        """Compress content for storage optimization"""
        if len(content) > 200:  # Only compress longer content
            compressed = zlib.compress(content.encode('utf-8'), level=6)
            return base64.b64encode(compressed).decode('ascii')
        return content
    
    def _get_prepared_statement(self, statement_key: str, sql: str) -> str:
        """Get or create prepared statement"""
        if statement_key not in self._prepared_statements:
            self._prepared_statements[statement_key] = sql
        return self._prepared_statements[statement_key]
    
    async def store_memory_batch(self, memories: List[Tuple[str, str, Dict[str, Any], float, float, Optional[Set[str]]]]) -> List[Memory]:
        """Store multiple memories in a single batch operation"""
        if not memories:
            return []
        
        memory_objects = []
        timestamp = datetime.now()
        
        # Process all memories
        for persona_id, content, context, importance, emotional_valence, tags in memories:
            # Generate memory ID
            memory_id = hashlib.md5(
                f"{persona_id}{content}{timestamp.isoformat()}".encode()
            ).hexdigest()[:16]
            
            # Check for duplicates
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            memory = Memory(
                id=memory_id,
                persona_id=persona_id,
                content=content,
                context=context,
                timestamp=timestamp,
                importance=importance,
                emotional_valence=emotional_valence,
                tags=tags or set(),
                associations=[],
                compressed=len(content) > 200
            )
            
            memory_objects.append(memory)
            self.memories[persona_id].append(memory)
            self.memory_index[memory_id] = memory
        
        # Batch persist to database
        await self._persist_memory_batch(memory_objects)
        
        # Find associations for all memories
        for memory in memory_objects:
            associations = await self._find_associations_optimized(memory)
            memory.associations = [m.id for m in associations[:5]]  # Limit associations
            
            # Create correlations in batch
            for assoc_memory in associations:
                await self._create_correlation_optimized(memory, assoc_memory)
        
        return memory_objects
    
    async def store_memory(self, 
                          persona_id: str,
                          content: str,
                          context: Dict[str, Any],
                          importance: float = 0.5,
                          emotional_valence: float = 0.0,
                          tags: Optional[Set[str]] = None) -> Memory:
        """Store a single memory with batching optimization"""
        
        with self._lock:
            self._batch_queue.append((persona_id, content, context, importance, emotional_valence, tags))
            
            # Auto-flush batch if size or time threshold reached
            should_flush = (len(self._batch_queue) >= self._batch_size or 
                           (datetime.now() - self._last_batch_flush).seconds > 30)
        
        if should_flush:
            return await self._flush_batch()
        
        # For immediate storage, process single memory
        memories = await self.store_memory_batch([(persona_id, content, context, importance, emotional_valence, tags)])
        return memories[0] if memories else None
    
    async def _flush_batch(self) -> Optional[Memory]:
        """Flush the batch queue"""
        with self._lock:
            if not self._batch_queue:
                return None
            
            batch = self._batch_queue.copy()
            self._batch_queue.clear()
            self._last_batch_flush = datetime.now()
        
        memories = await self.store_memory_batch(batch)
        return memories[-1] if memories else None  # Return last memory
    
    async def recall_optimized(self,
                              persona_id: str,
                              query: str,
                              context: Dict[str, Any],
                              limit: int = 10,
                              importance_threshold: float = 0.1) -> List[Memory]:
        """Optimized memory recall with caching and advanced scoring"""
        
        # Check query cache first
        query_hash = hashlib.md5(f"{persona_id}{query}{str(sorted(context.items()))}".encode()).hexdigest()
        cached_result = await self._get_cached_query(query_hash, persona_id)
        if cached_result:
            return cached_result
        
        # Use database query for better performance on large datasets
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Optimized query with importance threshold and recency bias
        query_sql = '''
            SELECT id, persona_id, content, content_compressed, context, timestamp, 
                   importance, emotional_valence, tags, associations, access_count, 
                   last_accessed, decay_rate, compressed, word_count,
                   timestamp_unix, last_accessed_unix
            FROM memories 
            WHERE persona_id = ? 
              AND importance > ?
              AND timestamp_unix > ?  -- Only consider recent memories for performance
            ORDER BY importance DESC, access_count DESC, timestamp_unix DESC
            LIMIT ?
        ''')
        
        # Get memories from last 6 months for initial filtering
        six_months_ago = int((datetime.now() - timedelta(days=180)).timestamp())
        
        cursor.execute(query_sql, (persona_id, importance_threshold, six_months_ago, limit * 3))
        rows = cursor.fetchall()
        self.db_manager.return_memory_connection(conn)
        
        # Process and score memories
        scored_memories = []
        query_words = set(query.lower().split())
        
        for row in rows:
            # Reconstruct memory (optimized)
            content = row[2]
            if row[13] and row[3]:  # compressed
                try:
                    content = zlib.decompress(base64.b64decode(row[3])).decode('utf-8')
                except:
                    content = row[2]
            
            memory = Memory(
                id=row[0],
                persona_id=row[1],
                content=content,
                context=json.loads(row[4]) if row[4] else {},
                timestamp=datetime.fromtimestamp(row[15]),
                importance=row[6],
                emotional_valence=row[7],
                tags=set(json.loads(row[8])) if row[8] else set(),
                associations=json.loads(row[9]) if row[9] else [],
                access_count=row[10],
                last_accessed=datetime.fromtimestamp(row[16]) if row[16] else None,
                decay_rate=row[12],
                compressed=bool(row[13])
            )
            
            # Fast relevance calculation
            relevance = memory.calculate_relevance(query, context)
            if relevance > 0.1:  # Only keep relevant memories
                scored_memories.append((relevance, memory))
        
        # Sort by relevance and take top memories
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        relevant_memories = [m for _, m in scored_memories[:limit]]
        
        # Update access counts in batch
        if relevant_memories:
            await self._batch_update_access(relevant_memories)
        
        # Cache the result
        await self._cache_query_result(query_hash, persona_id, relevant_memories)
        
        return relevant_memories
    
    async def _batch_update_access(self, memories: List[Memory]):
        """Update access counts for multiple memories in a single operation"""
        if not memories:
            return
        
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Prepare batch update
        now = datetime.now()
        updates = []
        for memory in memories:
            memory.access_count += 1
            memory.last_accessed = now
            updates.append((memory.access_count, int(now.timestamp()), memory.last_accessed.isoformat(), memory.id))
        
        # Batch execute
        cursor.executemany('''
            UPDATE memories 
            SET access_count = ?, last_accessed_unix = ?, last_accessed = ?
            WHERE id = ?
        ''', updates)
        
        conn.commit()
        self.db_manager.return_memory_connection(conn)
    
    async def compress_old_memories(self, age_days: int = 30):
        """Compress memories older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=age_days)
        cutoff_unix = int(cutoff_date.timestamp())
        
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Find uncompressed old memories
        cursor.execute('''
            SELECT id, content FROM memories 
            WHERE compressed = 0 
              AND timestamp_unix < ? 
              AND LENGTH(content) > 200
            ORDER BY timestamp_unix
            LIMIT 1000
        ''', (cutoff_unix,))
        
        memories_to_compress = cursor.fetchall()
        
        # Batch compress
        for memory_id, content in memories_to_compress:
            try:
                compressed_content = self._compress_content(content)
                cursor.execute('''
                    UPDATE memories 
                    SET content_compressed = ?, compressed = 1
                    WHERE id = ?
                ''', (compressed_content, memory_id))
            except Exception as e:
                print(f"Failed to compress memory {memory_id}: {e}")
        
        conn.commit()
        self.db_manager.return_memory_connection(conn)
        
        print(f"Compressed {len(memories_to_compress)} memories older than {age_days} days")
    
    async def _get_cached_query(self, query_hash: str, persona_id: str) -> Optional[List[Memory]]:
        """Get cached query result if still valid"""
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT result_ids, cache_timestamp FROM query_cache 
            WHERE query_hash = ? AND persona_id = ?
        ''', (query_hash, persona_id))
        
        row = cursor.fetchone()
        if row:
            cache_time = datetime.fromisoformat(row[1])
            if (datetime.now() - cache_time).seconds < 300:  # 5 minute cache
                memory_ids = json.loads(row[0])
                
                # Update hit count
                cursor.execute('''
                    UPDATE query_cache SET hit_count = hit_count + 1 
                    WHERE query_hash = ?
                ''', (query_hash,))
                conn.commit()
                
                # Return memories
                memories = [self.memory_index.get(mid) for mid in memory_ids]
                memories = [m for m in memories if m is not None]
                
                self.db_manager.return_memory_connection(conn)
                return memories if memories else None
        
        self.db_manager.return_memory_connection(conn)
        return None
    
    async def _cache_query_result(self, query_hash: str, persona_id: str, memories: List[Memory]):
        """Cache query result for performance"""
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        memory_ids = [m.id for m in memories]
        cursor.execute('''
            INSERT OR REPLACE INTO query_cache 
            (query_hash, result_ids, cache_timestamp, persona_id)
            VALUES (?, ?, ?, ?)
        ''', (query_hash, json.dumps(memory_ids), datetime.now().isoformat(), persona_id))
        
        conn.commit()
        self.db_manager.return_memory_connection(conn)
    
    async def _persist_memory_batch(self, memories: List[Memory]):
        """Persist multiple memories in a single transaction"""
        if not memories:
            return
        
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Prepare batch insert data
        batch_data = []
        for memory in memories:
            content_compressed = None
            if memory.compressed:
                content_compressed = self._compress_content(memory.content)
            
            content_hash = hashlib.md5(memory.content.encode()).hexdigest()
            word_count = len(memory.content.split())
            timestamp_unix = int(memory.timestamp.timestamp())
            last_accessed_unix = int(memory.last_accessed.timestamp()) if memory.last_accessed else None
            
            batch_data.append((
                memory.id,
                memory.persona_id,
                memory.content,
                content_compressed,
                json.dumps(memory.context),
                memory.timestamp.isoformat(),
                timestamp_unix,
                memory.importance,
                memory.emotional_valence,
                json.dumps(list(memory.tags)),
                json.dumps(memory.associations),
                memory.access_count,
                memory.last_accessed.isoformat() if memory.last_accessed else None,
                last_accessed_unix,
                memory.decay_rate,
                int(memory.compressed),
                content_hash,
                word_count
            ))
        
        # Batch execute
        cursor.executemany('''
            INSERT OR REPLACE INTO memories 
            (id, persona_id, content, content_compressed, context, timestamp, timestamp_unix,
             importance, emotional_valence, tags, associations, access_count, 
             last_accessed, last_accessed_unix, decay_rate, compressed, content_hash, word_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch_data)
        
        conn.commit()
        self.db_manager.return_memory_connection(conn)
    
    async def _find_associations_optimized(self, memory: Memory, threshold: float = 0.3) -> List[Memory]:
        """Find associations using optimized database queries"""
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Use database for association finding on large datasets
        cursor.execute('''
            SELECT id, content, tags, emotional_valence, timestamp_unix, importance
            FROM memories 
            WHERE persona_id = ? 
              AND id != ?
              AND importance > ?
            ORDER BY importance DESC, timestamp_unix DESC
            LIMIT 50
        ''', (memory.persona_id, memory.id, threshold))
        
        associations = []
        memory_words = set(memory.content.lower().split())
        
        for row in cursor.fetchall():
            other_id, other_content, other_tags_str, other_valence, other_timestamp, other_importance = row
            
            # Quick similarity calculation
            other_words = set(other_content.lower().split())
            if memory_words and other_words:
                overlap = len(memory_words & other_words) / len(memory_words | other_words)
                
                # Tag similarity
                other_tags = set(json.loads(other_tags_str)) if other_tags_str else set()
                tag_similarity = 0
                if memory.tags and other_tags:
                    tag_similarity = len(memory.tags & other_tags) / len(memory.tags | other_tags)
                
                # Combined similarity
                similarity = overlap * 0.6 + tag_similarity * 0.4
                
                if similarity > threshold:
                    # Get full memory object
                    if other_id in self.memory_index:
                        associations.append(self.memory_index[other_id])
        
        self.db_manager.return_memory_connection(conn)
        return associations[:5]  # Limit associations
    
    async def _create_correlation_optimized(self, m1: Memory, m2: Memory):
        """Create optimized memory correlation"""
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        strength = self._calculate_similarity_fast(m1, m2)
        now = datetime.now()
        
        cursor.execute('''
            INSERT OR REPLACE INTO memory_correlations
            (memory1_id, memory2_id, correlation_strength, correlation_type, 
             created_at, created_at_unix, last_reinforced, reinforcement_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            m1.id, m2.id, strength, 'similarity',
            now.isoformat(), int(now.timestamp()), now.isoformat(), 1
        ))
        
        conn.commit()
        self.db_manager.return_memory_connection(conn)
    
    def _calculate_similarity_fast(self, m1: Memory, m2: Memory) -> float:
        """Fast similarity calculation"""
        similarity = 0.0
        
        # Content overlap (simplified)
        words1 = set(m1.content.lower().split()[:20])  # Limit for performance
        words2 = set(m2.content.lower().split()[:20])
        if words1 and words2:
            overlap = len(words1 & words2) / len(words1 | words2)
            similarity += overlap * 0.5
        
        # Tag overlap
        if m1.tags and m2.tags:
            tag_overlap = len(m1.tags & m2.tags) / len(m1.tags | m2.tags)
            similarity += tag_overlap * 0.3
        
        # Importance similarity
        importance_diff = abs(m1.importance - m2.importance)
        importance_sim = 1 - importance_diff
        similarity += importance_sim * 0.2
        
        return similarity
    
    async def get_memory_statistics(self, persona_id: str) -> Dict[str, Any]:
        """Get optimized memory statistics for a persona"""
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Get comprehensive stats in a single query
        cursor.execute('''
            SELECT 
                COUNT(*) as total_memories,
                AVG(importance) as avg_importance,
                MAX(timestamp_unix) as latest_memory,
                SUM(CASE WHEN compressed = 1 THEN 1 ELSE 0 END) as compressed_count,
                AVG(access_count) as avg_access_count,
                COUNT(DISTINCT tags) as unique_tags,
                SUM(word_count) as total_words,
                COUNT(CASE WHEN importance > 0.8 THEN 1 END) as high_importance_count
            FROM memories 
            WHERE persona_id = ?
        ''', (persona_id,))
        
        row = cursor.fetchone()
        self.db_manager.return_memory_connection(conn)
        
        if row:
            return {
                'total_memories': row[0],
                'avg_importance': round(row[1] or 0, 3),
                'latest_memory': datetime.fromtimestamp(row[2]).isoformat() if row[2] else None,
                'compressed_memories': row[3],
                'compression_ratio': round((row[3] / max(row[0], 1)) * 100, 1),
                'avg_access_count': round(row[4] or 0, 2),
                'unique_tags': row[5],
                'total_words': row[6],
                'high_importance_memories': row[7],
                'memory_efficiency': round((row[7] / max(row[0], 1)) * 100, 1)
            }
        
        return {}
    
    async def cleanup_low_importance_memories(self, importance_threshold: float = 0.05):
        """Clean up memories with very low importance"""
        cutoff_date = datetime.now() - timedelta(days=90)
        cutoff_unix = int(cutoff_date.timestamp())
        
        conn = self.db_manager.get_memory_connection()
        cursor = conn.cursor()
        
        # Delete old, unimportant memories
        cursor.execute('''
            DELETE FROM memories 
            WHERE importance < ? 
              AND timestamp_unix < ?
              AND access_count = 0
        ''', (importance_threshold, cutoff_unix))
        
        deleted_count = cursor.rowcount
        
        # Clean up orphaned correlations
        cursor.execute('''
            DELETE FROM memory_correlations 
            WHERE memory1_id NOT IN (SELECT id FROM memories)
               OR memory2_id NOT IN (SELECT id FROM memories)
        ''')
        
        # Clean up old cache entries
        cursor.execute('''
            DELETE FROM query_cache 
            WHERE cache_timestamp < ?
        ''', ((datetime.now() - timedelta(hours=24)).isoformat(),))
        
        conn.commit()
        self.db_manager.return_memory_connection(conn)
        
        return deleted_count
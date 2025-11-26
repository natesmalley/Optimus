"""
Long-term Memory System for Personas

Provides persistent memory storage, retrieval, and association capabilities
for each persona to maintain context across sessions and learn from experiences.
"""

import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import numpy as np
from collections import defaultdict

@dataclass
class Memory:
    """A single memory unit"""
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
    decay_rate: float = 0.01  # How fast memory fades
    
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
            'decay_rate': self.decay_rate
        }
    
    def calculate_relevance(self, query: str, current_context: Dict[str, Any]) -> float:
        """Calculate how relevant this memory is to current situation"""
        relevance = self.importance
        
        # Text similarity
        query_words = set(query.lower().split())
        content_words = set(self.content.lower().split())
        overlap = len(query_words & content_words) / max(len(query_words), 1)
        relevance += overlap * 0.3
        
        # Recency bonus
        age_days = (datetime.now() - self.timestamp).days
        recency_factor = max(0, 1 - (age_days * self.decay_rate))
        relevance *= recency_factor
        
        # Access frequency bonus
        relevance += min(self.access_count * 0.01, 0.2)
        
        # Context similarity
        if self.context and current_context:
            shared_keys = set(self.context.keys()) & set(current_context.keys())
            if shared_keys:
                relevance += len(shared_keys) * 0.05
        
        return min(1.0, relevance)


class MemorySystem:
    """
    Manages long-term memory for all personas with persistence,
    association, and retrieval capabilities.
    """
    
    def __init__(self, db_path: str = "optimus_memory.db"):
        self.db_path = db_path
        self.memories: Dict[str, List[Memory]] = defaultdict(list)
        self.memory_index: Dict[str, Memory] = {}
        self._init_database()
        self._load_memories()
        
    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                persona_id TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT,
                timestamp TEXT NOT NULL,
                importance REAL,
                emotional_valence REAL,
                tags TEXT,
                associations TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                decay_rate REAL DEFAULT 0.01,
                FOREIGN KEY (persona_id) REFERENCES personas(id)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_persona_memories 
            ON memories(persona_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memory_timestamp 
            ON memories(timestamp)
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_correlations (
                memory1_id TEXT,
                memory2_id TEXT,
                correlation_strength REAL,
                correlation_type TEXT,
                created_at TEXT,
                PRIMARY KEY (memory1_id, memory2_id),
                FOREIGN KEY (memory1_id) REFERENCES memories(id),
                FOREIGN KEY (memory2_id) REFERENCES memories(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_memories(self):
        """Load memories from database into memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM memories')
        rows = cursor.fetchall()
        
        for row in rows:
            memory = Memory(
                id=row[0],
                persona_id=row[1],
                content=row[2],
                context=json.loads(row[3]) if row[3] else {},
                timestamp=datetime.fromisoformat(row[4]),
                importance=row[5],
                emotional_valence=row[6],
                tags=set(json.loads(row[7])) if row[7] else set(),
                associations=json.loads(row[8]) if row[8] else [],
                access_count=row[9],
                last_accessed=datetime.fromisoformat(row[10]) if row[10] else None,
                decay_rate=row[11]
            )
            
            self.memories[memory.persona_id].append(memory)
            self.memory_index[memory.id] = memory
        
        conn.close()
    
    async def store_memory(self, 
                          persona_id: str,
                          content: str,
                          context: Dict[str, Any],
                          importance: float = 0.5,
                          emotional_valence: float = 0.0,
                          tags: Optional[Set[str]] = None) -> Memory:
        """Store a new memory for a persona"""
        
        # Generate memory ID
        memory_id = hashlib.md5(
            f"{persona_id}{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Create memory object
        memory = Memory(
            id=memory_id,
            persona_id=persona_id,
            content=content,
            context=context,
            timestamp=datetime.now(),
            importance=importance,
            emotional_valence=emotional_valence,
            tags=tags or set(),
            associations=[]
        )
        
        # Find associations with existing memories
        associations = await self._find_associations(memory)
        memory.associations = [m.id for m in associations]
        
        # Store in memory
        self.memories[persona_id].append(memory)
        self.memory_index[memory_id] = memory
        
        # Persist to database
        await self._persist_memory(memory)
        
        # Create correlations
        for assoc_memory in associations:
            await self._create_correlation(memory, assoc_memory)
        
        return memory
    
    async def recall(self,
                    persona_id: str,
                    query: str,
                    context: Dict[str, Any],
                    limit: int = 10) -> List[Memory]:
        """Recall relevant memories for a persona"""
        
        persona_memories = self.memories.get(persona_id, [])
        if not persona_memories:
            return []
        
        # Calculate relevance for each memory
        scored_memories = []
        for memory in persona_memories:
            relevance = memory.calculate_relevance(query, context)
            scored_memories.append((relevance, memory))
        
        # Sort by relevance and take top memories
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        relevant_memories = [m for _, m in scored_memories[:limit]]
        
        # Update access counts
        for memory in relevant_memories:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
            await self._update_memory_access(memory)
        
        return relevant_memories
    
    async def consolidate_memories(self, persona_id: str):
        """
        Consolidate similar memories to prevent memory bloat.
        Simulates how humans compress and generalize experiences.
        """
        persona_memories = self.memories.get(persona_id, [])
        if len(persona_memories) < 50:  # Don't consolidate until enough memories
            return
        
        # Group similar memories
        memory_clusters = await self._cluster_memories(persona_memories)
        
        for cluster in memory_clusters:
            if len(cluster) < 3:  # Don't consolidate small clusters
                continue
            
            # Create consolidated memory
            consolidated_content = self._summarize_cluster(cluster)
            avg_importance = sum(m.importance for m in cluster) / len(cluster)
            avg_valence = sum(m.emotional_valence for m in cluster) / len(cluster)
            
            # Merge tags
            all_tags = set()
            for m in cluster:
                all_tags.update(m.tags)
            
            # Store consolidated memory
            consolidated = await self.store_memory(
                persona_id=persona_id,
                content=consolidated_content,
                context={'type': 'consolidated', 'source_count': len(cluster)},
                importance=min(1.0, avg_importance * 1.2),  # Boost importance
                emotional_valence=avg_valence,
                tags=all_tags
            )
            
            # Mark original memories for gradual decay
            for memory in cluster:
                memory.decay_rate *= 2  # Faster decay for consolidated memories
    
    async def _find_associations(self, 
                                memory: Memory,
                                threshold: float = 0.3) -> List[Memory]:
        """Find memories associated with a new memory"""
        
        associations = []
        persona_memories = self.memories.get(memory.persona_id, [])
        
        for existing_memory in persona_memories:
            if existing_memory.id == memory.id:
                continue
            
            # Calculate similarity
            similarity = self._calculate_similarity(memory, existing_memory)
            
            if similarity > threshold:
                associations.append(existing_memory)
        
        # Sort by similarity and limit
        associations = associations[:5]  # Max 5 associations
        
        return associations
    
    def _calculate_similarity(self, m1: Memory, m2: Memory) -> float:
        """Calculate similarity between two memories"""
        
        similarity = 0.0
        
        # Content overlap
        words1 = set(m1.content.lower().split())
        words2 = set(m2.content.lower().split())
        if words1 and words2:
            overlap = len(words1 & words2) / len(words1 | words2)
            similarity += overlap * 0.4
        
        # Tag overlap
        if m1.tags and m2.tags:
            tag_overlap = len(m1.tags & m2.tags) / len(m1.tags | m2.tags)
            similarity += tag_overlap * 0.3
        
        # Temporal proximity
        time_diff = abs((m1.timestamp - m2.timestamp).days)
        temporal_similarity = max(0, 1 - (time_diff / 365))  # Within a year
        similarity += temporal_similarity * 0.2
        
        # Emotional similarity
        emotional_diff = abs(m1.emotional_valence - m2.emotional_valence)
        emotional_similarity = 1 - (emotional_diff / 2)
        similarity += emotional_similarity * 0.1
        
        return similarity
    
    async def _cluster_memories(self, memories: List[Memory]) -> List[List[Memory]]:
        """Cluster similar memories together"""
        # Simple clustering based on similarity
        clusters = []
        used = set()
        
        for memory in memories:
            if memory.id in used:
                continue
            
            cluster = [memory]
            used.add(memory.id)
            
            for other in memories:
                if other.id in used:
                    continue
                
                if self._calculate_similarity(memory, other) > 0.6:
                    cluster.append(other)
                    used.add(other.id)
            
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return clusters
    
    def _summarize_cluster(self, cluster: List[Memory]) -> str:
        """Create a summary of a memory cluster"""
        # Simple approach: take most important elements
        contents = [m.content for m in sorted(cluster, 
                                             key=lambda x: x.importance, 
                                             reverse=True)]
        
        # Return a generalized version
        if len(contents) == 2:
            return f"Generally: {contents[0][:100]}. Also: {contents[1][:50]}"
        else:
            return f"Pattern observed across {len(contents)} experiences: {contents[0][:150]}"
    
    async def _persist_memory(self, memory: Memory):
        """Save memory to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO memories 
            (id, persona_id, content, context, timestamp, importance, 
             emotional_valence, tags, associations, access_count, 
             last_accessed, decay_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory.id,
            memory.persona_id,
            memory.content,
            json.dumps(memory.context),
            memory.timestamp.isoformat(),
            memory.importance,
            memory.emotional_valence,
            json.dumps(list(memory.tags)),
            json.dumps(memory.associations),
            memory.access_count,
            memory.last_accessed.isoformat() if memory.last_accessed else None,
            memory.decay_rate
        ))
        
        conn.commit()
        conn.close()
    
    async def _update_memory_access(self, memory: Memory):
        """Update memory access statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE memories 
            SET access_count = ?, last_accessed = ?
            WHERE id = ?
        ''', (memory.access_count, memory.last_accessed.isoformat(), memory.id))
        
        conn.commit()
        conn.close()
    
    async def _create_correlation(self, m1: Memory, m2: Memory):
        """Create correlation between two memories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        strength = self._calculate_similarity(m1, m2)
        
        cursor.execute('''
            INSERT OR REPLACE INTO memory_correlations
            (memory1_id, memory2_id, correlation_strength, correlation_type, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (m1.id, m2.id, strength, 'similarity', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    async def forget_gradually(self):
        """Simulate gradual forgetting of less important memories"""
        for persona_id, memories in self.memories.items():
            for memory in memories:
                # Reduce importance based on decay rate
                age_days = (datetime.now() - memory.timestamp).days
                decay_factor = memory.decay_rate * age_days
                
                # Less accessed memories decay faster
                if memory.access_count == 0:
                    decay_factor *= 2
                
                memory.importance = max(0, memory.importance - decay_factor)
                
                # Remove memories that have become completely irrelevant
                if memory.importance < 0.01:
                    self.memories[persona_id].remove(memory)
                    del self.memory_index[memory.id]
                    await self._delete_memory(memory.id)
    
    async def _delete_memory(self, memory_id: str):
        """Delete a memory from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
        cursor.execute('DELETE FROM memory_correlations WHERE memory1_id = ? OR memory2_id = ?', 
                      (memory_id, memory_id))
        
        conn.commit()
        conn.close()
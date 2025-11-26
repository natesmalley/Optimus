"""
Blackboard System - Shared Knowledge Space for Persona Collaboration

The blackboard acts as a central repository where all personas can:
- Post their insights and analyses
- Read other personas' contributions
- Build upon collective knowledge
- Track decision evolution
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class EntryType(Enum):
    """Types of entries that can be posted to the blackboard"""
    INSIGHT = "insight"          # General observation or analysis
    RECOMMENDATION = "recommendation"  # Specific action suggestion
    CONCERN = "concern"          # Risk or issue identified
    QUESTION = "question"        # Need for clarification
    DATA = "data"               # Factual information or metrics
    VOTE = "vote"               # Voting on a decision
    CONSENSUS = "consensus"     # Final agreed decision


@dataclass
class BlackboardEntry:
    """A single entry on the blackboard"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    persona_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    entry_type: EntryType = EntryType.INSIGHT
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5  # 0.0 to 1.0
    references: List[str] = field(default_factory=list)  # IDs of related entries
    tags: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization"""
        return {
            'id': self.id,
            'persona_id': self.persona_id,
            'timestamp': self.timestamp.isoformat(),
            'entry_type': self.entry_type.value,
            'content': self.content,
            'metadata': self.metadata,
            'confidence': self.confidence,
            'references': self.references,
            'tags': list(self.tags)
        }
    
    def relates_to(self, other_entry_id: str):
        """Mark this entry as related to another"""
        if other_entry_id not in self.references:
            self.references.append(other_entry_id)


class Blackboard:
    """
    Central knowledge repository for multi-persona collaboration
    
    Features:
    - Thread-safe async operations
    - Topic-based organization
    - Entry filtering and search
    - Knowledge persistence
    - Real-time updates via subscriptions
    """
    
    def __init__(self):
        self.entries: Dict[str, List[BlackboardEntry]] = {}  # topic -> entries
        self.all_entries: Dict[str, BlackboardEntry] = {}  # id -> entry
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}  # topic -> queues
        self.lock = asyncio.Lock()
        self.topics: Set[str] = set()
        
    async def post(self, topic: str, entry: BlackboardEntry) -> str:
        """
        Post a new entry to the blackboard
        
        Args:
            topic: The topic/context for this entry
            entry: The blackboard entry to post
            
        Returns:
            The ID of the posted entry
        """
        async with self.lock:
            # Add to topic-specific list
            if topic not in self.entries:
                self.entries[topic] = []
                self.topics.add(topic)
            
            self.entries[topic].append(entry)
            self.all_entries[entry.id] = entry
            
            # Notify subscribers
            await self._notify_subscribers(topic, entry)
            
            logger.debug(f"Posted {entry.entry_type.value} from {entry.persona_id} to {topic}")
            
            return entry.id
    
    async def read(self, 
                   topic: Optional[str] = None,
                   persona_id: Optional[str] = None,
                   entry_type: Optional[EntryType] = None,
                   since: Optional[datetime] = None,
                   limit: int = 100) -> List[BlackboardEntry]:
        """
        Read entries from the blackboard with filtering
        
        Args:
            topic: Filter by topic (None for all topics)
            persona_id: Filter by persona who posted
            entry_type: Filter by type of entry
            since: Only entries after this timestamp
            limit: Maximum number of entries to return
            
        Returns:
            List of matching entries, sorted by timestamp
        """
        async with self.lock:
            entries = []
            
            # Collect entries from specified topic or all topics
            if topic:
                entries = self.entries.get(topic, []).copy()
            else:
                for topic_entries in self.entries.values():
                    entries.extend(topic_entries)
            
            # Apply filters
            if persona_id:
                entries = [e for e in entries if e.persona_id == persona_id]
            
            if entry_type:
                entries = [e for e in entries if e.entry_type == entry_type]
            
            if since:
                entries = [e for e in entries if e.timestamp > since]
            
            # Sort by timestamp and apply limit
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            return entries[:limit]
    
    async def get_entry(self, entry_id: str) -> Optional[BlackboardEntry]:
        """Get a specific entry by ID"""
        async with self.lock:
            return self.all_entries.get(entry_id)
    
    async def search(self, query: str, topic: Optional[str] = None) -> List[BlackboardEntry]:
        """
        Search entries by content
        
        Args:
            query: Search string (case-insensitive)
            topic: Optionally limit search to specific topic
            
        Returns:
            Matching entries sorted by relevance
        """
        query_lower = query.lower()
        entries = await self.read(topic=topic, limit=1000)
        
        # Simple relevance scoring
        scored_entries = []
        for entry in entries:
            score = 0
            content_lower = entry.content.lower()
            
            # Exact match scores highest
            if query_lower == content_lower:
                score = 10
            # Contains query
            elif query_lower in content_lower:
                score = 5
            # Word-level matches
            else:
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                matching_words = query_words & content_words
                score = len(matching_words)
            
            if score > 0:
                scored_entries.append((score, entry))
        
        # Sort by score and return entries
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        return [entry for score, entry in scored_entries]
    
    async def get_consensus_trail(self, topic: str) -> List[BlackboardEntry]:
        """
        Get the decision-making trail for a topic
        
        Returns entries in chronological order showing how consensus was reached
        """
        entries = await self.read(topic=topic, limit=1000)
        entries.sort(key=lambda e: e.timestamp)
        return entries
    
    async def subscribe(self, topic: str) -> asyncio.Queue:
        """
        Subscribe to real-time updates for a topic
        
        Returns:
            An async queue that will receive new entries
        """
        async with self.lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            
            queue = asyncio.Queue()
            self.subscribers[topic].append(queue)
            return queue
    
    async def unsubscribe(self, topic: str, queue: asyncio.Queue):
        """Unsubscribe from a topic"""
        async with self.lock:
            if topic in self.subscribers:
                self.subscribers[topic].remove(queue)
    
    async def _notify_subscribers(self, topic: str, entry: BlackboardEntry):
        """Notify all subscribers of a new entry"""
        if topic in self.subscribers:
            for queue in self.subscribers[topic]:
                try:
                    await queue.put(entry)
                except asyncio.QueueFull:
                    logger.warning(f"Subscriber queue full for topic {topic}")
    
    async def clear_topic(self, topic: str):
        """Clear all entries for a specific topic"""
        async with self.lock:
            if topic in self.entries:
                # Remove from all_entries
                for entry in self.entries[topic]:
                    self.all_entries.pop(entry.id, None)
                
                # Clear topic entries
                self.entries[topic] = []
                
                logger.info(f"Cleared all entries for topic {topic}")
    
    async def get_statistics(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about blackboard usage
        
        Returns:
            Dictionary with stats like entry counts, active personas, etc.
        """
        entries = await self.read(topic=topic, limit=10000)
        
        if not entries:
            return {
                'total_entries': 0,
                'topics': [],
                'active_personas': [],
                'entry_types': {}
            }
        
        # Calculate statistics
        persona_counts = {}
        entry_type_counts = {}
        confidence_sum = 0
        
        for entry in entries:
            persona_counts[entry.persona_id] = persona_counts.get(entry.persona_id, 0) + 1
            entry_type_counts[entry.entry_type.value] = entry_type_counts.get(entry.entry_type.value, 0) + 1
            confidence_sum += entry.confidence
        
        return {
            'total_entries': len(entries),
            'topics': list(self.topics),
            'active_personas': list(persona_counts.keys()),
            'persona_activity': persona_counts,
            'entry_types': entry_type_counts,
            'average_confidence': confidence_sum / len(entries) if entries else 0,
            'time_range': {
                'start': min(e.timestamp for e in entries).isoformat() if entries else None,
                'end': max(e.timestamp for e in entries).isoformat() if entries else None
            }
        }
    
    def export_to_json(self, topic: Optional[str] = None) -> str:
        """Export blackboard entries to JSON for persistence or analysis"""
        entries = asyncio.run(self.read(topic=topic, limit=10000))
        return json.dumps([e.to_dict() for e in entries], indent=2)
    
    async def import_from_json(self, json_str: str, topic: str):
        """Import entries from JSON"""
        data = json.loads(json_str)
        for entry_data in data:
            entry = BlackboardEntry(
                id=entry_data['id'],
                persona_id=entry_data['persona_id'],
                timestamp=datetime.fromisoformat(entry_data['timestamp']),
                entry_type=EntryType(entry_data['entry_type']),
                content=entry_data['content'],
                metadata=entry_data.get('metadata', {}),
                confidence=entry_data.get('confidence', 0.5),
                references=entry_data.get('references', []),
                tags=set(entry_data.get('tags', []))
            )
            await self.post(topic, entry)
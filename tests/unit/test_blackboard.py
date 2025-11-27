"""
Unit tests for blackboard operations and data management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import MagicMock, AsyncMock, patch

from src.council.blackboard import (
    Blackboard, BlackboardEntry, EntryType,
    BlackboardError, InvalidTopicError, EntryNotFoundError
)


class TestBlackboardEntry:
    """Test BlackboardEntry creation and validation"""
    
    def test_entry_creation(self):
        """Test creating a valid blackboard entry"""
        entry = BlackboardEntry(
            persona_id="strategist",
            entry_type=EntryType.INSIGHT,
            content="This is a valuable insight",
            metadata={"importance": "high", "category": "architecture"},
            tags={"insight", "architecture", "strategy"}
        )
        
        assert entry.persona_id == "strategist"
        assert entry.entry_type == EntryType.INSIGHT
        assert entry.content == "This is a valuable insight"
        assert entry.metadata["importance"] == "high"
        assert "architecture" in entry.tags
        assert entry.timestamp is not None
        assert entry.entry_id is not None
    
    def test_entry_validation(self):
        """Test entry validation rules"""
        # Test empty content
        with pytest.raises(ValueError):
            BlackboardEntry(
                persona_id="test",
                entry_type=EntryType.INSIGHT,
                content=""  # Empty content should fail
            )
        
        # Test empty persona_id
        with pytest.raises(ValueError):
            BlackboardEntry(
                persona_id="",  # Empty persona_id should fail
                entry_type=EntryType.INSIGHT,
                content="Valid content"
            )
    
    def test_entry_serialization(self):
        """Test entry can be serialized to dict"""
        entry = BlackboardEntry(
            persona_id="analyst",
            entry_type=EntryType.RECOMMENDATION,
            content="Use PostgreSQL for data persistence",
            metadata={"database_type": "relational", "performance": "high"},
            tags={"database", "recommendation"}
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict["persona_id"] == "analyst"
        assert entry_dict["entry_type"] == "recommendation"
        assert entry_dict["content"] == "Use PostgreSQL for data persistence"
        assert entry_dict["metadata"]["database_type"] == "relational"
        assert "database" in entry_dict["tags"]
        assert "timestamp" in entry_dict
        assert "entry_id" in entry_dict
    
    def test_entry_types(self):
        """Test all entry types are valid"""
        for entry_type in EntryType:
            entry = BlackboardEntry(
                persona_id="test",
                entry_type=entry_type,
                content=f"Test content for {entry_type.value}"
            )
            assert entry.entry_type == entry_type


class TestBlackboard:
    """Test core Blackboard functionality"""
    
    @pytest.fixture
    async def blackboard(self):
        """Create fresh blackboard for testing"""
        bb = Blackboard()
        await bb.initialize()
        return bb
    
    async def test_blackboard_initialization(self, blackboard):
        """Test blackboard initializes properly"""
        assert blackboard.is_initialized is True
        assert isinstance(blackboard.topics, dict)
        assert isinstance(blackboard.entry_index, dict)
    
    async def test_post_entry(self, blackboard):
        """Test posting entry to blackboard"""
        entry = BlackboardEntry(
            persona_id="strategist",
            entry_type=EntryType.INSIGHT,
            content="Microservices improve scalability",
            tags={"architecture", "scalability"}
        )
        
        topic = "architecture_discussion"
        await blackboard.post(topic, entry)
        
        # Verify entry was stored
        entries = await blackboard.get_entries(topic)
        assert len(entries) == 1
        assert entries[0].content == "Microservices improve scalability"
        assert entries[0].persona_id == "strategist"
    
    async def test_post_multiple_entries(self, blackboard):
        """Test posting multiple entries to same topic"""
        topic = "security_discussion"
        
        entries = [
            BlackboardEntry(
                persona_id="guardian",
                entry_type=EntryType.CONCERN,
                content="SQL injection vulnerability"
            ),
            BlackboardEntry(
                persona_id="strategist", 
                entry_type=EntryType.RECOMMENDATION,
                content="Implement input validation"
            ),
            BlackboardEntry(
                persona_id="pragmatist",
                entry_type=EntryType.INSIGHT,
                content="Use parameterized queries"
            )
        ]
        
        for entry in entries:
            await blackboard.post(topic, entry)
        
        retrieved = await blackboard.get_entries(topic)
        assert len(retrieved) == 3
        
        # Verify order (should be chronological)
        persona_ids = [e.persona_id for e in retrieved]
        assert persona_ids == ["guardian", "strategist", "pragmatist"]
    
    async def test_get_entries_empty_topic(self, blackboard):
        """Test getting entries from empty topic"""
        entries = await blackboard.get_entries("nonexistent_topic")
        assert entries == []
    
    async def test_get_entries_by_type(self, blackboard):
        """Test filtering entries by type"""
        topic = "mixed_discussion"
        
        await blackboard.post(topic, BlackboardEntry(
            persona_id="strategist",
            entry_type=EntryType.INSIGHT,
            content="Architecture insight"
        ))
        await blackboard.post(topic, BlackboardEntry(
            persona_id="guardian",
            entry_type=EntryType.CONCERN,
            content="Security concern"
        ))
        await blackboard.post(topic, BlackboardEntry(
            persona_id="analyst",
            entry_type=EntryType.INSIGHT,
            content="Performance insight"
        ))
        
        # Get only insights
        insights = await blackboard.get_entries_by_type(topic, EntryType.INSIGHT)
        assert len(insights) == 2
        assert all(e.entry_type == EntryType.INSIGHT for e in insights)
        
        # Get only concerns
        concerns = await blackboard.get_entries_by_type(topic, EntryType.CONCERN)
        assert len(concerns) == 1
        assert concerns[0].content == "Security concern"
    
    async def test_get_entries_by_persona(self, blackboard):
        """Test filtering entries by persona"""
        topic = "persona_test"
        
        await blackboard.post(topic, BlackboardEntry(
            persona_id="strategist",
            entry_type=EntryType.INSIGHT,
            content="Strategic insight 1"
        ))
        await blackboard.post(topic, BlackboardEntry(
            persona_id="analyst",
            entry_type=EntryType.INSIGHT,
            content="Analytical insight"
        ))
        await blackboard.post(topic, BlackboardEntry(
            persona_id="strategist",
            entry_type=EntryType.RECOMMENDATION,
            content="Strategic recommendation"
        ))
        
        strategist_entries = await blackboard.get_entries_by_persona(topic, "strategist")
        assert len(strategist_entries) == 2
        assert all(e.persona_id == "strategist" for e in strategist_entries)
        
        analyst_entries = await blackboard.get_entries_by_persona(topic, "analyst")
        assert len(analyst_entries) == 1
        assert analyst_entries[0].content == "Analytical insight"
    
    async def test_get_recent_entries(self, blackboard):
        """Test getting recent entries with time limits"""
        topic = "time_test"
        
        # Post entries with artificial time gaps
        old_entry = BlackboardEntry(
            persona_id="old_persona",
            entry_type=EntryType.INSIGHT,
            content="Old entry"
        )
        # Manually set old timestamp
        old_entry.timestamp = datetime.now() - timedelta(hours=2)
        
        recent_entry = BlackboardEntry(
            persona_id="recent_persona",
            entry_type=EntryType.INSIGHT,
            content="Recent entry"
        )
        
        await blackboard.post(topic, old_entry)
        await blackboard.post(topic, recent_entry)
        
        # Get entries from last hour
        recent = await blackboard.get_recent_entries(topic, minutes=60)
        assert len(recent) == 1
        assert recent[0].content == "Recent entry"
    
    async def test_search_entries(self, blackboard):
        """Test searching entries by content"""
        topic = "search_test"
        
        entries = [
            BlackboardEntry(
                persona_id="p1",
                entry_type=EntryType.INSIGHT,
                content="Database performance is critical"
            ),
            BlackboardEntry(
                persona_id="p2", 
                entry_type=EntryType.INSIGHT,
                content="Security measures are important"
            ),
            BlackboardEntry(
                persona_id="p3",
                entry_type=EntryType.INSIGHT,
                content="Database scaling strategies"
            )
        ]
        
        for entry in entries:
            await blackboard.post(topic, entry)
        
        # Search for database-related entries
        database_entries = await blackboard.search_entries(topic, "database")
        assert len(database_entries) == 2
        assert all("database" in e.content.lower() for e in database_entries)
        
        # Search for security entries
        security_entries = await blackboard.search_entries(topic, "security")
        assert len(security_entries) == 1
        assert "security" in security_entries[0].content.lower()
    
    async def test_get_statistics(self, blackboard):
        """Test getting blackboard statistics"""
        topic = "stats_test"
        
        # Post various types of entries
        entries = [
            BlackboardEntry(persona_id="p1", entry_type=EntryType.QUESTION, content="Question 1"),
            BlackboardEntry(persona_id="p1", entry_type=EntryType.INSIGHT, content="Insight 1"),
            BlackboardEntry(persona_id="p2", entry_type=EntryType.INSIGHT, content="Insight 2"),
            BlackboardEntry(persona_id="p3", entry_type=EntryType.CONCERN, content="Concern 1"),
            BlackboardEntry(persona_id="p2", entry_type=EntryType.RECOMMENDATION, content="Rec 1")
        ]
        
        for entry in entries:
            await blackboard.post(topic, entry)
        
        stats = await blackboard.get_statistics(topic)
        
        assert stats["total_entries"] == 5
        assert stats["unique_personas"] == 3
        assert stats["entry_types"]["insight"] == 2
        assert stats["entry_types"]["question"] == 1
        assert stats["entry_types"]["concern"] == 1
        assert stats["entry_types"]["recommendation"] == 1
        assert "timeline" in stats
    
    async def test_clear_topic(self, blackboard):
        """Test clearing a topic"""
        topic = "clear_test"
        
        # Add some entries
        for i in range(3):
            await blackboard.post(topic, BlackboardEntry(
                persona_id=f"p{i}",
                entry_type=EntryType.INSIGHT,
                content=f"Entry {i}"
            ))
        
        # Verify entries exist
        entries = await blackboard.get_entries(topic)
        assert len(entries) == 3
        
        # Clear topic
        await blackboard.clear_topic(topic)
        
        # Verify topic is empty
        entries = await blackboard.get_entries(topic)
        assert len(entries) == 0


class TestBlackboardConcurrency:
    """Test blackboard under concurrent access"""
    
    @pytest.fixture
    async def blackboard(self):
        """Create blackboard for concurrency testing"""
        bb = Blackboard()
        await bb.initialize()
        return bb
    
    async def test_concurrent_posts(self, blackboard):
        """Test concurrent posting to same topic"""
        topic = "concurrent_test"
        
        async def post_entries(persona_id: str, count: int):
            """Post multiple entries from a persona"""
            for i in range(count):
                entry = BlackboardEntry(
                    persona_id=persona_id,
                    entry_type=EntryType.INSIGHT,
                    content=f"Entry {i} from {persona_id}"
                )
                await blackboard.post(topic, entry)
                await asyncio.sleep(0.01)  # Small delay to simulate real usage
        
        # Start concurrent posting tasks
        tasks = [
            asyncio.create_task(post_entries("persona1", 5)),
            asyncio.create_task(post_entries("persona2", 5)),
            asyncio.create_task(post_entries("persona3", 5))
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all entries were posted
        entries = await blackboard.get_entries(topic)
        assert len(entries) == 15
        
        # Verify entries from each persona
        persona1_entries = [e for e in entries if e.persona_id == "persona1"]
        persona2_entries = [e for e in entries if e.persona_id == "persona2"] 
        persona3_entries = [e for e in entries if e.persona_id == "persona3"]
        
        assert len(persona1_entries) == 5
        assert len(persona2_entries) == 5
        assert len(persona3_entries) == 5
    
    async def test_concurrent_read_write(self, blackboard):
        """Test concurrent reading and writing"""
        topic = "read_write_test"
        
        async def writer():
            """Continuously write entries"""
            for i in range(10):
                entry = BlackboardEntry(
                    persona_id="writer",
                    entry_type=EntryType.INSIGHT,
                    content=f"Writer entry {i}"
                )
                await blackboard.post(topic, entry)
                await asyncio.sleep(0.01)
        
        async def reader():
            """Continuously read entries"""
            read_counts = []
            for _ in range(10):
                entries = await blackboard.get_entries(topic)
                read_counts.append(len(entries))
                await asyncio.sleep(0.01)
            return read_counts
        
        # Start writer and reader concurrently
        writer_task = asyncio.create_task(writer())
        reader_task = asyncio.create_task(reader())
        
        await asyncio.gather(writer_task, reader_task)
        
        # Verify final state
        final_entries = await blackboard.get_entries(topic)
        assert len(final_entries) == 10


class TestBlackboardPersistence:
    """Test blackboard data persistence features"""
    
    @pytest.fixture
    async def persistent_blackboard(self, temp_database):
        """Create blackboard with persistence"""
        # Mock persistence layer
        with patch('src.council.blackboard.MemoryManager') as mock_memory:
            mock_instance = MagicMock()
            mock_instance.store_blackboard_entry = AsyncMock()
            mock_instance.get_blackboard_entries = AsyncMock(return_value=[])
            mock_memory.return_value = mock_instance
            
            bb = Blackboard(enable_persistence=True)
            await bb.initialize()
            
            yield bb, mock_instance
    
    async def test_persistent_entry_storage(self, persistent_blackboard):
        """Test entries are persisted to storage"""
        blackboard, mock_memory = persistent_blackboard
        
        entry = BlackboardEntry(
            persona_id="strategist",
            entry_type=EntryType.INSIGHT,
            content="Important strategic insight"
        )
        
        await blackboard.post("persistent_topic", entry)
        
        # Verify persistence was called
        mock_memory.store_blackboard_entry.assert_called_once()
    
    async def test_load_from_persistence(self, persistent_blackboard):
        """Test loading entries from persistence"""
        blackboard, mock_memory = persistent_blackboard
        
        # Mock stored entries
        stored_entries = [
            {
                "entry_id": "test_id_1",
                "persona_id": "strategist",
                "entry_type": "insight",
                "content": "Stored insight",
                "metadata": {},
                "tags": [],
                "timestamp": datetime.now().isoformat()
            }
        ]
        mock_memory.get_blackboard_entries.return_value = stored_entries
        
        # Load entries
        entries = await blackboard.load_topic("stored_topic")
        
        assert len(entries) == 1
        assert entries[0].content == "Stored insight"
        mock_memory.get_blackboard_entries.assert_called_once()


class TestBlackboardErrorHandling:
    """Test blackboard error handling and edge cases"""
    
    @pytest.fixture
    async def blackboard(self):
        """Create blackboard for error testing"""
        bb = Blackboard()
        await bb.initialize()
        return bb
    
    async def test_invalid_topic_name(self, blackboard):
        """Test handling of invalid topic names"""
        with pytest.raises(InvalidTopicError):
            await blackboard.post("", BlackboardEntry(
                persona_id="test",
                entry_type=EntryType.INSIGHT,
                content="Test content"
            ))
        
        with pytest.raises(InvalidTopicError):
            await blackboard.post("   ", BlackboardEntry(
                persona_id="test",
                entry_type=EntryType.INSIGHT,
                content="Test content"
            ))
    
    async def test_get_nonexistent_entry(self, blackboard):
        """Test getting entry that doesn't exist"""
        with pytest.raises(EntryNotFoundError):
            await blackboard.get_entry_by_id("nonexistent_id")
    
    async def test_memory_limits(self, blackboard):
        """Test blackboard behavior under memory pressure"""
        topic = "memory_test"
        
        # Post many entries to test memory limits
        for i in range(1000):
            entry = BlackboardEntry(
                persona_id=f"persona_{i%10}",
                entry_type=EntryType.INSIGHT,
                content=f"Large content entry number {i} " + "x" * 100
            )
            await blackboard.post(topic, entry)
        
        # Verify entries are still accessible
        entries = await blackboard.get_entries(topic)
        assert len(entries) <= 1000  # May be pruned due to limits
        
        # Verify statistics still work
        stats = await blackboard.get_statistics(topic)
        assert stats["total_entries"] > 0
    
    async def test_corrupted_entry_handling(self, blackboard):
        """Test handling of corrupted entries"""
        topic = "corruption_test"
        
        # Create entry with potentially problematic data
        entry = BlackboardEntry(
            persona_id="test",
            entry_type=EntryType.INSIGHT,
            content="Normal content",
            metadata={"nested": {"deeply": {"problematic": None}}}
        )
        
        # Should handle gracefully
        await blackboard.post(topic, entry)
        entries = await blackboard.get_entries(topic)
        assert len(entries) == 1


class TestBlackboardIntegration:
    """Test blackboard integration with other components"""
    
    async def test_consensus_trail_creation(self):
        """Test creating consensus trail"""
        blackboard = Blackboard()
        await blackboard.initialize()
        
        topic = "consensus_test"
        
        # Simulate deliberation process
        entries = [
            BlackboardEntry(
                persona_id="orchestrator",
                entry_type=EntryType.QUESTION,
                content="Should we use microservices?"
            ),
            BlackboardEntry(
                persona_id="strategist",
                entry_type=EntryType.INSIGHT,
                content="Microservices improve scalability"
            ),
            BlackboardEntry(
                persona_id="guardian",
                entry_type=EntryType.CONCERN,
                content="Increased complexity"
            ),
            BlackboardEntry(
                persona_id="consensus_engine",
                entry_type=EntryType.CONSENSUS,
                content="Adopt microservices with careful planning",
                metadata={
                    "confidence": 0.8,
                    "agreement_level": 0.75,
                    "method": "weighted_majority"
                }
            )
        ]
        
        for entry in entries:
            await blackboard.post(topic, entry)
        
        # Get consensus trail
        trail = await blackboard.get_consensus_trail(topic)
        
        assert len(trail) == 4
        assert trail[0].entry_type == EntryType.QUESTION
        assert trail[-1].entry_type == EntryType.CONSENSUS
        assert "microservices" in trail[-1].content.lower()
    
    async def test_knowledge_graph_integration(self):
        """Test blackboard integration with knowledge graph"""
        blackboard = Blackboard()
        await blackboard.initialize()
        
        topic = "knowledge_test"
        
        # Post entries with entity references
        entry = BlackboardEntry(
            persona_id="analyst",
            entry_type=EntryType.INSIGHT,
            content="PostgreSQL offers excellent ACID compliance",
            metadata={
                "entities": ["PostgreSQL", "ACID"],
                "relationships": [("PostgreSQL", "offers", "ACID compliance")]
            }
        )
        
        await blackboard.post(topic, entry)
        
        # Verify entry is stored and searchable
        entries = await blackboard.search_entries(topic, "PostgreSQL")
        assert len(entries) == 1
        assert "PostgreSQL" in entries[0].content
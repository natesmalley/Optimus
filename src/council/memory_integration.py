"""
Memory System Integration

Integration layer that provides backward compatibility while using
the optimized memory system underneath.
"""

from .memory import Memory as OriginalMemory, MemorySystem as OriginalMemorySystem
from ..database.memory_optimized import OptimizedMemorySystem, Memory as OptimizedMemory
from ..database.config import get_database_manager
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import asyncio


class MemorySystemAdapter:
    """
    Adapter class that provides backward compatibility for the existing
    MemorySystem interface while using the optimized implementation.
    """
    
    def __init__(self, db_path: str = "optimus_memory.db"):
        """Initialize with backward compatibility"""
        self.db_path = db_path
        self.db_manager = get_database_manager()
        self.optimized_system = OptimizedMemorySystem(self.db_manager)
        
        # Maintain compatibility with existing interface
        self.memories: Dict[str, List[OriginalMemory]] = {}
        self.memory_index: Dict[str, OriginalMemory] = {}
        
        # Initialize in async context if needed
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the system is initialized"""
        if not self._initialized:
            await self.db_manager.initialize()
            self._initialized = True
    
    def _convert_to_original_memory(self, optimized_memory: OptimizedMemory) -> OriginalMemory:
        """Convert optimized memory to original format"""
        return OriginalMemory(
            id=optimized_memory.id,
            persona_id=optimized_memory.persona_id,
            content=optimized_memory.content,
            context=optimized_memory.context,
            timestamp=optimized_memory.timestamp,
            importance=optimized_memory.importance,
            emotional_valence=optimized_memory.emotional_valence,
            tags=optimized_memory.tags,
            associations=optimized_memory.associations,
            access_count=optimized_memory.access_count,
            last_accessed=optimized_memory.last_accessed,
            decay_rate=optimized_memory.decay_rate
        )
    
    async def store_memory(self, 
                          persona_id: str,
                          content: str,
                          context: Dict[str, Any],
                          importance: float = 0.5,
                          emotional_valence: float = 0.0,
                          tags: Optional[Set[str]] = None) -> OriginalMemory:
        """Store memory using optimized system"""
        await self._ensure_initialized()
        
        optimized_memory = await self.optimized_system.store_memory(
            persona_id=persona_id,
            content=content,
            context=context,
            importance=importance,
            emotional_valence=emotional_valence,
            tags=tags
        )
        
        # Convert to original format for compatibility
        memory = self._convert_to_original_memory(optimized_memory)
        
        # Update compatibility indexes
        if persona_id not in self.memories:
            self.memories[persona_id] = []
        self.memories[persona_id].append(memory)
        self.memory_index[memory.id] = memory
        
        return memory
    
    async def recall(self,
                    persona_id: str,
                    query: str,
                    context: Dict[str, Any],
                    limit: int = 10) -> List[OriginalMemory]:
        """Recall memories using optimized system"""
        await self._ensure_initialized()
        
        optimized_memories = await self.optimized_system.recall_optimized(
            persona_id=persona_id,
            query=query,
            context=context,
            limit=limit
        )
        
        # Convert to original format
        memories = [self._convert_to_original_memory(mem) for mem in optimized_memories]
        
        # Update compatibility indexes
        for memory in memories:
            self.memory_index[memory.id] = memory
            if persona_id not in self.memories:
                self.memories[persona_id] = []
            # Update existing memory in list if it exists
            existing_indices = [i for i, m in enumerate(self.memories[persona_id]) if m.id == memory.id]
            if existing_indices:
                self.memories[persona_id][existing_indices[0]] = memory
            else:
                self.memories[persona_id].append(memory)
        
        return memories
    
    async def consolidate_memories(self, persona_id: str):
        """Consolidate memories using optimized system"""
        await self._ensure_initialized()
        
        # Use optimized memory statistics for consolidation decisions
        stats = await self.optimized_system.get_memory_statistics(persona_id)
        
        if stats.get('total_memories', 0) > 100:  # More conservative threshold
            # Use optimized cleanup
            deleted_count = await self.optimized_system.cleanup_low_importance_memories(
                importance_threshold=0.1
            )
            
            # Update compatibility indexes by removing deleted memories
            if persona_id in self.memories:
                self.memories[persona_id] = [
                    m for m in self.memories[persona_id] 
                    if m.importance >= 0.1
                ]
    
    async def forget_gradually(self):
        """Perform gradual forgetting using optimized system"""
        await self._ensure_initialized()
        
        # Use optimized compression and cleanup
        await self.optimized_system.compress_old_memories(age_days=30)
        await self.optimized_system.cleanup_low_importance_memories(importance_threshold=0.05)
        
        # Clear compatibility indexes (they'll be rebuilt on demand)
        self.memories.clear()
        self.memory_index.clear()


# Create a global instance that can be used as a drop-in replacement
_global_memory_system = None


def get_optimized_memory_system() -> MemorySystemAdapter:
    """Get the global optimized memory system instance"""
    global _global_memory_system
    if _global_memory_system is None:
        _global_memory_system = MemorySystemAdapter()
    return _global_memory_system


# Backward compatibility: provide the same interface as the original
class MemorySystem(MemorySystemAdapter):
    """
    Drop-in replacement for the original MemorySystem class.
    Uses the optimized implementation while maintaining full compatibility.
    """
    pass

# Alias for backwards compatibility
MemoryIntegration = MemorySystemAdapter
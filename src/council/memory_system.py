"""
Advanced Memory System for Optimus Council of Minds

Provides persistent memory storage, retrieval, and learning capabilities
for each persona using PostgreSQL as the backend. Enables context-aware
responses and learning from past deliberations.
"""

import asyncio
import hashlib
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

from sqlalchemy import (
    select, update, delete, func, and_, or_, desc, asc,
    text
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..database.config import get_database_manager
from ..models.memory import (
    DeliberationMemory,
    PersonaResponseMemory, 
    ContextMemory,
    PersonaLearningPattern,
    MemoryAssociation,
    MemoryMetrics
)
from .persona import PersonaResponse

# Forward declarations to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .orchestrator import DeliberationRequest, DeliberationResult

logger = logging.getLogger(__name__)


@dataclass
class MemoryQuery:
    """Query for memory retrieval"""
    query_text: str
    context: Dict[str, Any]
    persona_name: Optional[str] = None
    topic: Optional[str] = None
    limit: int = 10
    min_relevance: float = 0.3
    include_context: bool = True
    time_range: Optional[Tuple[datetime, datetime]] = None


@dataclass 
class MemoryRecall:
    """Result of memory recall operation"""
    memories: List[DeliberationMemory]
    relevance_scores: List[float]
    context_memories: List[ContextMemory]
    learning_patterns: List[PersonaLearningPattern]
    total_found: int
    query_time: float


class PersonaMemorySystem:
    """
    Advanced memory system for Council of Minds personas.
    Provides persistent storage, intelligent retrieval, and adaptive learning.
    """

    def __init__(self):
        self._db_manager = get_database_manager()
        self._similarity_cache: Dict[str, float] = {}
        self._performance_metrics: Dict[str, Any] = defaultdict(list)

    async def initialize(self):
        """Initialize the memory system"""
        await self._db_manager.initialize()
        await self._create_search_indexes()
        logger.info("PersonaMemorySystem initialized successfully")

    async def _create_search_indexes(self):
        """Create advanced search indexes for better performance"""
        async with self._db_manager.get_postgres_session() as session:
            # Create text search indexes for queries
            await session.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_deliberation_query_tsvector 
                ON deliberation_memories 
                USING GIN (to_tsvector('english', query));
            """))
            
            # Create similarity search indexes
            await session.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_persona_response_tsvector 
                ON persona_response_memories 
                USING GIN (to_tsvector('english', response || ' ' || reasoning));
            """))
            
            await session.commit()

    async def store_deliberation(self, 
                                request: "DeliberationRequest", 
                                result: "DeliberationResult") -> DeliberationMemory:
        """
        Store a complete deliberation session in memory.
        
        Args:
            request: Original deliberation request
            result: Complete deliberation result
            
        Returns:
            DeliberationMemory: Stored deliberation record
        """
        start_time = datetime.now()
        
        async with self._db_manager.get_postgres_session() as session:
            try:
                # Calculate query hash for similarity matching
                query_hash = hashlib.sha256(request.query.encode()).hexdigest()
                
                # Determine importance score based on consensus and time
                importance = await self._calculate_importance(result)
                
                # Extract tags from query and context
                tags = await self._extract_tags(request.query, request.context)
                
                # Create deliberation memory
                deliberation = DeliberationMemory(
                    query=request.query,
                    topic=request.topic or "general",
                    context=request.context,
                    consensus_result=result.consensus.to_dict(),
                    consensus_confidence=result.consensus.confidence,
                    consensus_method=result.consensus.method.value,
                    deliberation_time=result.deliberation_time,
                    persona_count=len(result.persona_responses),
                    query_hash=query_hash,
                    tags=tags,
                    importance_score=importance
                )
                
                session.add(deliberation)
                await session.flush()  # Get the ID
                
                # Store persona responses
                persona_responses = []
                for response in result.persona_responses:
                    response_memory = await self._store_persona_response(
                        session, deliberation.id, response, result
                    )
                    persona_responses.append(response_memory)
                
                # Create associations with similar deliberations
                await self._create_memory_associations(session, deliberation)
                
                # Update learning patterns for personas
                await self._update_learning_patterns(session, deliberation, persona_responses)
                
                await session.commit()
                
                # Record performance metrics
                storage_time = (datetime.now() - start_time).total_seconds()
                await self._record_metric("storage_latency", storage_time, {"deliberation_id": str(deliberation.id)})
                
                logger.info(f"Stored deliberation memory: {deliberation.id} in {storage_time:.3f}s")
                return deliberation
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to store deliberation memory: {e}")
                raise

    async def _store_persona_response(self,
                                     session: AsyncSession,
                                     deliberation_id,
                                     response: PersonaResponse,
                                     result: "DeliberationResult") -> PersonaResponseMemory:
        """Store an individual persona response"""
        
        # Calculate agreement score with other personas
        agreement_score = await self._calculate_agreement_score(response, result.persona_responses)
        
        response_memory = PersonaResponseMemory(
            deliberation_id=deliberation_id,
            persona_name=response.persona_name,
            persona_role=response.persona_role,
            response=response.response,
            reasoning=response.reasoning,
            confidence=response.confidence,
            response_time=response.response_time,
            tools_used=response.tools_used or [],
            context_considered=response.context_used or {},
            agreement_score=agreement_score
        )
        
        session.add(response_memory)
        await session.flush()
        
        # Store context memories if available
        if response.context_used:
            for context_type, context_data in response.context_used.items():
                context_memory = ContextMemory(
                    response_id=response_memory.id,
                    context_type=context_type,
                    context_data=context_data if isinstance(context_data, dict) else {"value": context_data},
                    relevance_score=0.5,  # Default relevance
                    source_type="deliberation",
                    source_id=str(deliberation_id)
                )
                session.add(context_memory)
        
        return response_memory

    async def recall_memories(self, query: MemoryQuery) -> MemoryRecall:
        """
        Recall relevant memories based on a query.
        
        Args:
            query: Memory query parameters
            
        Returns:
            MemoryRecall: Retrieved memories with relevance scores
        """
        start_time = datetime.now()
        
        async with self._db_manager.get_postgres_session() as session:
            # Build the base query
            base_query = select(DeliberationMemory)
            
            # Add filters
            filters = []
            
            # Time range filter
            if query.time_range:
                filters.append(DeliberationMemory.created_at.between(*query.time_range))
            
            # Topic filter
            if query.topic:
                filters.append(DeliberationMemory.topic == query.topic)
            
            # Minimum importance filter
            filters.append(DeliberationMemory.importance_score >= query.min_relevance)
            
            if filters:
                base_query = base_query.where(and_(*filters))
            
            # Execute text search query
            search_results = await self._execute_similarity_search(
                session, query.query_text, base_query, query.limit * 2
            )
            
            # Calculate relevance scores
            memories_with_scores = []
            for memory in search_results:
                relevance = await self._calculate_relevance_score(
                    memory, query.query_text, query.context
                )
                if relevance >= query.min_relevance:
                    memories_with_scores.append((memory, relevance))
            
            # Sort by relevance and limit
            memories_with_scores.sort(key=lambda x: x[1], reverse=True)
            memories_with_scores = memories_with_scores[:query.limit]
            
            memories = [m[0] for m in memories_with_scores]
            relevance_scores = [m[1] for m in memories_with_scores]
            
            # Get context memories if requested
            context_memories = []
            if query.include_context and memories:
                memory_ids = [m.id for m in memories]
                context_query = select(ContextMemory).join(PersonaResponseMemory).where(
                    PersonaResponseMemory.deliberation_id.in_(memory_ids)
                )
                context_result = await session.execute(context_query)
                context_memories = context_result.scalars().all()
            
            # Get relevant learning patterns for persona
            learning_patterns = []
            if query.persona_name:
                pattern_query = select(PersonaLearningPattern).where(
                    PersonaLearningPattern.persona_name == query.persona_name
                ).order_by(desc(PersonaLearningPattern.strength)).limit(5)
                pattern_result = await session.execute(pattern_query)
                learning_patterns = pattern_result.scalars().all()
            
            # Update access counts for accessed memories
            if memories:
                await self._update_memory_access_counts(session, [m.id for m in memories])
            
            await session.commit()
            
            # Record performance metrics
            query_time = (datetime.now() - start_time).total_seconds()
            await self._record_metric("recall_latency", query_time, {
                "memories_found": len(memories),
                "persona": query.persona_name
            })
            
            return MemoryRecall(
                memories=memories,
                relevance_scores=relevance_scores,
                context_memories=context_memories,
                learning_patterns=learning_patterns,
                total_found=len(search_results),
                query_time=query_time
            )

    async def _execute_similarity_search(self,
                                        session: AsyncSession,
                                        query_text: str,
                                        base_query,
                                        limit: int) -> List[DeliberationMemory]:
        """Execute text similarity search using PostgreSQL full-text search"""
        
        # Use PostgreSQL's text search capabilities
        similarity_query = base_query.where(
            func.to_tsvector('english', DeliberationMemory.query).op('@@')(
                func.plainto_tsquery('english', query_text)
            )
        ).order_by(
            func.ts_rank(
                func.to_tsvector('english', DeliberationMemory.query),
                func.plainto_tsquery('english', query_text)
            ).desc(),
            desc(DeliberationMemory.importance_score),
            desc(DeliberationMemory.created_at)
        ).limit(limit)
        
        result = await session.execute(similarity_query)
        return result.scalars().all()

    async def _calculate_relevance_score(self,
                                       memory: DeliberationMemory,
                                       query_text: str,
                                       context: Dict[str, Any]) -> float:
        """Calculate relevance score for a memory given current query and context"""
        
        relevance = memory.importance_score * 0.4  # Base importance
        
        # Text similarity (simple word overlap for now)
        query_words = set(query_text.lower().split())
        memory_words = set(memory.query.lower().split())
        if query_words and memory_words:
            overlap = len(query_words & memory_words) / len(query_words | memory_words)
            relevance += overlap * 0.3
        
        # Context similarity
        if memory.context and context:
            shared_keys = set(memory.context.keys()) & set(context.keys())
            if shared_keys:
                context_similarity = len(shared_keys) / len(set(memory.context.keys()) | set(context.keys()))
                relevance += context_similarity * 0.2
        
        # Recency factor (more recent is more relevant)
        age_days = (datetime.now() - memory.created_at).days
        recency_factor = max(0, 1 - (age_days / 365))  # Decay over a year
        relevance *= (0.7 + 0.3 * recency_factor)
        
        # Consensus confidence boost
        relevance += memory.consensus_confidence * 0.1
        
        return min(1.0, relevance)

    async def find_similar_memories(self,
                                  query_text: str,
                                  limit: int = 5,
                                  threshold: float = 0.3) -> List[Tuple[DeliberationMemory, float]]:
        """Find memories similar to a given query"""
        
        memory_query = MemoryQuery(
            query_text=query_text,
            context={},
            limit=limit,
            min_relevance=threshold
        )
        
        recall_result = await self.recall_memories(memory_query)
        
        return list(zip(recall_result.memories, recall_result.relevance_scores))

    async def _calculate_importance(self, result: "DeliberationResult") -> float:
        """Calculate importance score for a deliberation"""
        
        importance = 0.5  # Base importance
        
        # Consensus confidence contributes to importance
        importance += result.consensus.confidence * 0.3
        
        # Deliberation time (longer may be more important)
        if result.deliberation_time > 10.0:  # If it took more than 10 seconds
            importance += min(0.2, result.deliberation_time / 100.0)
        
        # Number of personas involved
        importance += min(0.2, len(result.persona_responses) / 20.0)
        
        return min(1.0, importance)

    async def _extract_tags(self, query: str, context: Dict[str, Any]) -> List[str]:
        """Extract tags from query and context for categorization"""
        
        tags = []
        
        # Simple keyword extraction (could be enhanced with NLP)
        words = query.lower().split()
        important_words = [w for w in words if len(w) > 4 and w.isalpha()]
        tags.extend(important_words[:5])  # Limit to 5 words
        
        # Add context-based tags
        if "project" in context:
            tags.append("project-specific")
        if "error" in query.lower():
            tags.append("error-resolution")
        if any(word in query.lower() for word in ["how", "why", "what", "when", "where"]):
            tags.append("question")
        
        return list(set(tags))  # Remove duplicates

    async def _calculate_agreement_score(self,
                                       response: PersonaResponse,
                                       all_responses: List[PersonaResponse]) -> float:
        """Calculate how much other personas agreed with this response"""
        
        if len(all_responses) <= 1:
            return 0.5  # Default for single response
        
        # Simple similarity comparison (could be enhanced)
        agreements = 0
        comparisons = 0
        
        for other in all_responses:
            if other.persona_name != response.persona_name:
                # Simple word overlap similarity
                response_words = set(response.response.lower().split())
                other_words = set(other.response.lower().split())
                
                if response_words and other_words:
                    overlap = len(response_words & other_words) / len(response_words | other_words)
                    agreements += overlap
                    comparisons += 1
        
        return agreements / comparisons if comparisons > 0 else 0.5

    async def _create_memory_associations(self,
                                        session: AsyncSession,
                                        new_memory: DeliberationMemory):
        """Create associations between the new memory and existing similar ones"""
        
        # Find similar existing memories
        similar_query = select(DeliberationMemory).where(
            and_(
                DeliberationMemory.id != new_memory.id,
                DeliberationMemory.query_hash != new_memory.query_hash,
                func.to_tsvector('english', DeliberationMemory.query).op('@@')(
                    func.plainto_tsquery('english', new_memory.query)
                )
            )
        ).limit(5)
        
        result = await session.execute(similar_query)
        similar_memories = result.scalars().all()
        
        # Create associations
        for similar in similar_memories:
            similarity = await self._calculate_memory_similarity(new_memory, similar)
            
            if similarity > 0.3:  # Threshold for creating association
                association = MemoryAssociation(
                    source_memory_id=new_memory.id,
                    target_memory_id=similar.id,
                    association_type="similar",
                    strength=similarity,
                    discovered_by="text_similarity",
                    association_metadata={"similarity_score": similarity}
                )
                session.add(association)

    async def _calculate_memory_similarity(self,
                                         memory1: DeliberationMemory,
                                         memory2: DeliberationMemory) -> float:
        """Calculate similarity between two memories"""
        
        # Cache key for this comparison
        cache_key = f"{memory1.id}:{memory2.id}"
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        
        similarity = 0.0
        
        # Query similarity
        words1 = set(memory1.query.lower().split())
        words2 = set(memory2.query.lower().split())
        if words1 and words2:
            query_sim = len(words1 & words2) / len(words1 | words2)
            similarity += query_sim * 0.4
        
        # Tag similarity
        if memory1.tags and memory2.tags:
            tags1 = set(memory1.tags)
            tags2 = set(memory2.tags)
            tag_sim = len(tags1 & tags2) / len(tags1 | tags2)
            similarity += tag_sim * 0.3
        
        # Context similarity
        if memory1.context and memory2.context:
            ctx1_keys = set(memory1.context.keys())
            ctx2_keys = set(memory2.context.keys())
            if ctx1_keys and ctx2_keys:
                ctx_sim = len(ctx1_keys & ctx2_keys) / len(ctx1_keys | ctx2_keys)
                similarity += ctx_sim * 0.2
        
        # Temporal proximity
        time_diff = abs((memory1.created_at - memory2.created_at).days)
        temporal_sim = max(0, 1 - time_diff / 365)  # Decay over a year
        similarity += temporal_sim * 0.1
        
        # Cache the result
        self._similarity_cache[cache_key] = similarity
        return similarity

    async def _update_learning_patterns(self,
                                      session: AsyncSession,
                                      deliberation: DeliberationMemory,
                                      responses: List[PersonaResponseMemory]):
        """Update learning patterns for personas based on their responses"""
        
        for response in responses:
            # Update confidence pattern
            await self._update_pattern(
                session,
                response.persona_name,
                "confidence_pattern",
                deliberation.topic or "general",
                {"confidence": response.confidence, "agreement": response.agreement_score}
            )
            
            # Update response time pattern
            await self._update_pattern(
                session,
                response.persona_name,
                "response_time_pattern", 
                deliberation.topic or "general",
                {"response_time": response.response_time, "confidence": response.confidence}
            )

    async def _update_pattern(self,
                            session: AsyncSession,
                            persona_name: str,
                            pattern_type: str,
                            context: str,
                            data: Dict[str, Any]):
        """Update or create a learning pattern"""
        
        # Check if pattern exists
        existing_query = select(PersonaLearningPattern).where(
            and_(
                PersonaLearningPattern.persona_name == persona_name,
                PersonaLearningPattern.pattern_type == pattern_type,
                PersonaLearningPattern.pattern_context == context
            )
        )
        
        result = await session.execute(existing_query)
        existing_pattern = result.scalar_one_or_none()
        
        if existing_pattern:
            # Update existing pattern
            existing_pattern.pattern_data = {
                **existing_pattern.pattern_data,
                **data,
                "last_update": datetime.now().isoformat()
            }
            existing_pattern.observation_count += 1
            existing_pattern.last_reinforced = datetime.now()
            existing_pattern.strength = min(1.0, existing_pattern.strength + 0.1)
        else:
            # Create new pattern
            new_pattern = PersonaLearningPattern(
                persona_name=persona_name,
                pattern_type=pattern_type,
                pattern_context=context,
                pattern_data=data,
                strength=0.1,
                confidence=0.5,
                observation_count=1,
                last_reinforced=datetime.now()
            )
            session.add(new_pattern)

    async def _update_memory_access_counts(self,
                                         session: AsyncSession,
                                         memory_ids: List):
        """Update access counts for accessed memories"""
        
        update_stmt = (
            update(DeliberationMemory)
            .where(DeliberationMemory.id.in_(memory_ids))
            .values(updated_at=datetime.now())
        )
        
        await session.execute(update_stmt)

    async def _record_metric(self,
                            metric_type: str,
                            value: float,
                            metadata: Dict[str, Any]):
        """Record performance metrics"""
        
        async with self._db_manager.get_postgres_session() as session:
            metric = MemoryMetrics(
                metric_type=metric_type,
                metric_scope="global",
                value=value,
                metric_metadata=metadata,
                measurement_period=datetime.now()
            )
            session.add(metric)
            await session.commit()

    async def get_persona_memory_summary(self, persona_name: str) -> Dict[str, Any]:
        """Get memory statistics and patterns for a specific persona"""
        
        async with self._db_manager.get_postgres_session() as session:
            # Get response count
            response_count_query = select(func.count(PersonaResponseMemory.id)).where(
                PersonaResponseMemory.persona_name == persona_name
            )
            response_count_result = await session.execute(response_count_query)
            response_count = response_count_result.scalar()
            
            # Get average confidence
            avg_confidence_query = select(func.avg(PersonaResponseMemory.confidence)).where(
                PersonaResponseMemory.persona_name == persona_name
            )
            avg_confidence_result = await session.execute(avg_confidence_query)
            avg_confidence = avg_confidence_result.scalar() or 0.0
            
            # Get learning patterns
            patterns_query = select(PersonaLearningPattern).where(
                PersonaLearningPattern.persona_name == persona_name
            ).order_by(desc(PersonaLearningPattern.strength))
            patterns_result = await session.execute(patterns_query)
            patterns = patterns_result.scalars().all()
            
            return {
                "persona_name": persona_name,
                "total_responses": response_count,
                "average_confidence": float(avg_confidence),
                "learning_patterns": len(patterns),
                "strongest_patterns": [
                    {
                        "type": p.pattern_type,
                        "context": p.pattern_context,
                        "strength": p.strength,
                        "observations": p.observation_count
                    } for p in patterns[:5]
                ]
            }

    async def consolidate_old_memories(self, days_threshold: int = 90):
        """Consolidate old memories to prevent database bloat"""
        
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        async with self._db_manager.get_postgres_session() as session:
            # Find old, low-importance memories
            old_memories_query = select(DeliberationMemory).where(
                and_(
                    DeliberationMemory.created_at < cutoff_date,
                    DeliberationMemory.importance_score < 0.3
                )
            )
            
            result = await session.execute(old_memories_query)
            old_memories = result.scalars().all()
            
            logger.info(f"Found {len(old_memories)} old memories for potential consolidation")
            
            # Group similar memories and mark for consolidation
            # This is a simplified approach - could be enhanced
            consolidation_count = 0
            for memory in old_memories:
                if memory.importance_score < 0.2:  # Very low importance
                    # Just reduce importance further instead of deleting
                    memory.importance_score = max(0.1, memory.importance_score * 0.9)
                    consolidation_count += 1
            
            await session.commit()
            logger.info(f"Consolidated {consolidation_count} old memories")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on memory system"""
        
        async with self._db_manager.get_postgres_session() as session:
            # Count memories
            memory_count_query = select(func.count(DeliberationMemory.id))
            memory_count_result = await session.execute(memory_count_query)
            memory_count = memory_count_result.scalar()
            
            # Count responses
            response_count_query = select(func.count(PersonaResponseMemory.id))
            response_count_result = await session.execute(response_count_query)
            response_count = response_count_result.scalar()
            
            # Get latest memory
            latest_query = select(DeliberationMemory.created_at).order_by(
                desc(DeliberationMemory.created_at)
            ).limit(1)
            latest_result = await session.execute(latest_query)
            latest_memory = latest_result.scalar()
            
            return {
                "status": "healthy",
                "total_deliberations": memory_count,
                "total_responses": response_count,
                "latest_memory": latest_memory.isoformat() if latest_memory else None,
                "cache_size": len(self._similarity_cache)
            }


# Global instance
_memory_system: Optional[PersonaMemorySystem] = None


async def get_memory_system() -> PersonaMemorySystem:
    """Get the global memory system instance"""
    global _memory_system
    if _memory_system is None:
        _memory_system = PersonaMemorySystem()
        await _memory_system.initialize()
    return _memory_system
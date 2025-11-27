"""
Knowledge Graph PostgreSQL Models

Defines PostgreSQL models for persistent knowledge graph storage with
advanced indexing for graph traversal and analytics.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum

from sqlalchemy import (
    String, Text, DateTime, Float, Integer, Boolean, 
    ForeignKey, Index, func, JSON, ARRAY, LargeBinary
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


# Define PostgreSQL enums
class NodeTypeEnum(Enum):
    """Enhanced node types for the knowledge graph"""
    CONCEPT = "concept"
    PERSON = "person" 
    PROJECT = "project"
    TECHNOLOGY = "technology"
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
    PATTERN = "pattern"
    INSIGHT = "insight"
    RELATIONSHIP = "relationship"
    WORKFLOW = "workflow"
    TOOL = "tool"
    PERSONA = "persona"
    PROBLEM = "problem"
    SOLUTION = "solution"
    DEPENDENCY = "dependency"


class EdgeTypeEnum(Enum):
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
    IMPLEMENTS = "implements"
    USES = "uses"
    DEPENDS_ON = "depends_on"
    CONTAINS = "contains"
    TRIGGERS = "triggers"
    DERIVES_FROM = "derives_from"
    SOLVED_BY = "solved_by"
    RECOMMENDS = "recommends"
    COMPETES_WITH = "competes_with"
    BUILT_WITH = "built_with"


class GraphNode(Base, TimestampMixin):
    """
    Knowledge graph nodes with advanced tracking and semantic features.
    Supports projects, technologies, decisions, personas, and concepts.
    """
    __tablename__ = "graph_nodes"

    # Core node properties
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    node_type: Mapped[NodeTypeEnum] = mapped_column(
        ENUM(NodeTypeEnum, name="node_type_enum"), 
        nullable=False, 
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Node attributes and metadata
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Importance and activation
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, index=True)
    activation_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    
    # Persona relevance mapping
    personas_relevance: Mapped[Dict[str, float]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Access and performance tracking
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Semantic similarity support
    embedding_vector: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    
    # Search optimization
    name_lower: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    search_terms: Mapped[str] = mapped_column(Text, nullable=False, default="")
    
    # Source tracking
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    outgoing_edges: Mapped[List["GraphEdge"]] = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.source_id",
        back_populates="source_node",
        cascade="all, delete-orphan"
    )
    
    incoming_edges: Mapped[List["GraphEdge"]] = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.target_id",
        back_populates="target_node",
        cascade="all, delete-orphan"
    )
    
    clusters: Mapped[List["GraphCluster"]] = relationship(
        "GraphCluster",
        secondary="cluster_memberships",
        back_populates="nodes"
    )

    # Advanced indexes for graph operations
    __table_args__ = (
        # Basic indexes
        Index('ix_graph_nodes_type_importance', 'node_type', 'importance'),
        Index('ix_graph_nodes_name_type', 'name_lower', 'node_type'),
        Index('ix_graph_nodes_access_count', 'access_count'),
        Index('ix_graph_nodes_last_accessed', 'last_accessed'),
        
        # Search indexes
        Index('ix_graph_nodes_search_gin', 'search_terms', postgresql_using='gin'),
        Index('ix_graph_nodes_tags_gin', 'tags', postgresql_using='gin'),
        Index('ix_graph_nodes_attributes_gin', 'attributes', postgresql_using='gin'),
        Index('ix_graph_nodes_personas_gin', 'personas_relevance', postgresql_using='gin'),
        
        # Performance indexes
        Index('ix_graph_nodes_type_created', 'node_type', 'created_at'),
        Index('ix_graph_nodes_importance_created', 'importance', 'created_at'),
        Index('ix_graph_nodes_source', 'source_type', 'source_id'),
        
        # Composite indexes for common queries
        Index('ix_graph_nodes_active_important', 'activation_level', 'importance'),
        Index('ix_graph_nodes_confidence_access', 'confidence_score', 'access_count'),
    )


class GraphEdge(Base, TimestampMixin):
    """
    Knowledge graph edges with advanced relationship tracking.
    Supports weighted relationships with confidence and decay.
    """
    __tablename__ = "graph_edges"

    # Edge endpoints
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Edge type and properties
    edge_type: Mapped[EdgeTypeEnum] = mapped_column(
        ENUM(EdgeTypeEnum, name="edge_type_enum"),
        nullable=False,
        index=True
    )
    
    # Relationship strength and confidence
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, index=True)
    
    # Edge metadata
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Reinforcement learning
    reinforcement_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_reinforced: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decay_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.01)
    
    # Source tracking
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")
    discovered_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Context information
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Performance tracking
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    source_node: Mapped["GraphNode"] = relationship(
        "GraphNode",
        foreign_keys=[source_id],
        back_populates="outgoing_edges"
    )
    
    target_node: Mapped["GraphNode"] = relationship(
        "GraphNode", 
        foreign_keys=[target_id],
        back_populates="incoming_edges"
    )

    # Indexes for graph traversal optimization
    __table_args__ = (
        # Core graph traversal indexes
        Index('ix_graph_edges_source_type', 'source_id', 'edge_type'),
        Index('ix_graph_edges_target_type', 'target_id', 'edge_type'),
        Index('ix_graph_edges_type_weight', 'edge_type', 'weight'),
        
        # Bidirectional traversal
        Index('ix_graph_edges_bidirectional', 'source_id', 'target_id'),
        Index('ix_graph_edges_reverse_bidirectional', 'target_id', 'source_id'),
        
        # Performance indexes
        Index('ix_graph_edges_source_weight', 'source_id', 'weight'),
        Index('ix_graph_edges_target_weight', 'target_id', 'weight'),
        Index('ix_graph_edges_confidence_weight', 'confidence', 'weight'),
        
        # Temporal indexes
        Index('ix_graph_edges_reinforced', 'last_reinforced'),
        Index('ix_graph_edges_access_pattern', 'access_count', 'last_accessed'),
        
        # Graph algorithm optimization
        Index('ix_graph_edges_traversal_optimized', 'source_id', 'edge_type', 'weight'),
        Index('ix_graph_edges_reverse_traversal', 'target_id', 'edge_type', 'weight'),
        
        # Search and filtering
        Index('ix_graph_edges_tags_gin', 'tags', postgresql_using='gin'),
        Index('ix_graph_edges_attributes_gin', 'attributes', postgresql_using='gin'),
        Index('ix_graph_edges_context_gin', 'context', postgresql_using='gin'),
        
        # Prevent duplicate edges
        Index('ix_graph_edges_unique_relationship', 'source_id', 'target_id', 'edge_type', unique=True),
    )


class GraphCluster(Base, TimestampMixin):
    """
    Discovered communities and clusters in the knowledge graph.
    Enables pattern recognition and organizational insights.
    """
    __tablename__ = "graph_clusters"

    # Cluster properties
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cluster_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Cluster metrics
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    modularity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cohesion_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Cluster metadata
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Discovery information
    discovered_by_algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    discovery_parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    
    # Temporal tracking
    stability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    last_validated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    nodes: Mapped[List["GraphNode"]] = relationship(
        "GraphNode",
        secondary="cluster_memberships", 
        back_populates="clusters"
    )

    # Indexes for cluster analysis
    __table_args__ = (
        Index('ix_graph_clusters_type', 'cluster_type'),
        Index('ix_graph_clusters_size', 'size'),
        Index('ix_graph_clusters_density', 'density'),
        Index('ix_graph_clusters_modularity', 'modularity'),
        Index('ix_graph_clusters_algorithm', 'discovered_by_algorithm'),
        Index('ix_graph_clusters_confidence', 'confidence'),
        Index('ix_graph_clusters_stability', 'stability_score'),
        Index('ix_graph_clusters_tags_gin', 'tags', postgresql_using='gin'),
        Index('ix_graph_clusters_attributes_gin', 'attributes', postgresql_using='gin'),
    )


class ClusterMembership(Base):
    """
    Association table for node cluster membership with strength scoring.
    """
    __tablename__ = "cluster_memberships"

    # Foreign keys
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_clusters.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True
    )
    
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True
    )
    
    # Membership properties
    membership_strength: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_core_member: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    membership_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Temporal tracking
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    last_validated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Indexes for membership queries
    __table_args__ = (
        Index('ix_cluster_memberships_cluster', 'cluster_id'),
        Index('ix_cluster_memberships_node', 'node_id'),
        Index('ix_cluster_memberships_strength', 'membership_strength'),
        Index('ix_cluster_memberships_core', 'is_core_member'),
    )


class GraphPathCache(Base, TimestampMixin):
    """
    Cached frequently computed graph paths for performance optimization.
    """
    __tablename__ = "graph_path_cache"

    # Path endpoints
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Path parameters
    path_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 'shortest', 'strongest', 'semantic'
    max_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    edge_types_filter: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    
    # Path data
    path_nodes: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    path_edges: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    total_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    path_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Cache management
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_accessed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Invalidation tracking
    graph_version_when_computed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Indexes for path queries
    __table_args__ = (
        Index('ix_graph_path_cache_endpoints', 'source_id', 'target_id'),
        Index('ix_graph_path_cache_type', 'path_type'),
        Index('ix_graph_path_cache_access', 'access_count'),
        Index('ix_graph_path_cache_expires', 'expires_at'),
        Index('ix_graph_path_cache_version', 'graph_version_when_computed'),
        # Unique constraint for caching
        Index('ix_graph_path_cache_unique', 'source_id', 'target_id', 'path_type', 'max_depth', unique=True),
    )


class GraphStatistics(Base, TimestampMixin):
    """
    Precomputed graph statistics and metrics for analytics and monitoring.
    """
    __tablename__ = "graph_statistics"

    # Statistic identification
    statistic_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(100), nullable=False)  # 'global', 'cluster', 'node_type'
    scope_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Metric values
    value: Mapped[float] = mapped_column(Float, nullable=False)
    statistic_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Computation details
    computed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    computation_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Validity tracking
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    graph_version_when_computed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Indexes for statistics queries
    __table_args__ = (
        Index('ix_graph_statistics_type', 'statistic_type'),
        Index('ix_graph_statistics_scope', 'scope', 'scope_id'),
        Index('ix_graph_statistics_valid', 'valid_until'),
        Index('ix_graph_statistics_version', 'graph_version_when_computed'),
        Index('ix_graph_statistics_metadata_gin', 'statistic_metadata', postgresql_using='gin'),
    )
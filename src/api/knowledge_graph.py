"""
Knowledge Graph API Endpoints
=============================

Comprehensive REST API for the Optimus Knowledge Graph System.
Provides endpoints for nodes, edges, clusters, insights, and graph analytics.

Features:
- Node and edge management with filtering and pagination
- Cross-project pattern discovery and insights
- Technology compatibility mapping and recommendations
- Decision network analysis and learnings
- Graph clustering and community detection
- Visualization export and analytics
- Path finding between concepts
- Real-time graph statistics and performance metrics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..config import get_db_session
from ..council.optimus_knowledge_graph import OptimusKnowledgeGraph
from ..models.knowledge_graph import (
    GraphNode, GraphEdge, GraphCluster, 
    NodeTypeEnum, EdgeTypeEnum
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Global knowledge graph instance
_knowledge_graph: Optional[OptimusKnowledgeGraph] = None

async def get_knowledge_graph() -> OptimusKnowledgeGraph:
    """Get or create knowledge graph instance"""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = OptimusKnowledgeGraph()
        await _knowledge_graph.initialize()
    return _knowledge_graph

# =================== REQUEST/RESPONSE MODELS ===================

class NodeResponse(BaseModel):
    """Response model for graph nodes"""
    id: str
    name: str
    node_type: str
    attributes: Dict[str, Any]
    importance: float
    access_count: int
    last_accessed: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class EdgeResponse(BaseModel):
    """Response model for graph edges"""
    id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float
    confidence: float
    attributes: Dict[str, Any]
    reinforcement_count: int
    last_reinforced: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class NodeCreateRequest(BaseModel):
    """Request model for creating nodes"""
    name: str = Field(..., min_length=1, max_length=255)
    node_type: NodeTypeEnum
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    importance: float = Field(0.5, ge=0.0, le=1.0)


class EdgeCreateRequest(BaseModel):
    """Request model for creating edges"""
    source_id: UUID
    target_id: UUID
    edge_type: EdgeTypeEnum
    weight: float = Field(1.0, ge=0.0, le=1.0)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProjectInsightResponse(BaseModel):
    """Response model for project insights"""
    insight_type: str
    title: str
    description: str
    confidence: float
    evidence: List[str]
    related_projects: List[str]
    recommendations: List[str]
    impact_score: float


class TechnologyMappingResponse(BaseModel):
    """Response model for technology mappings"""
    technology: str
    usage_count: int
    success_rate: float
    compatible_technologies: List[str]
    competing_technologies: List[str]
    recommended_projects: List[str]
    skill_requirements: List[str]


class ClusterResponse(BaseModel):
    """Response model for graph clusters"""
    cluster_id: int
    size: int
    node_types: Dict[str, int]
    avg_importance: float
    dominant_type: Optional[str]
    members: List[str]


class GraphStatsResponse(BaseModel):
    """Response model for graph statistics"""
    total_nodes: int
    total_edges: int
    graph_nodes: int
    graph_edges: int
    density: float
    node_type_distribution: Dict[str, int]
    edge_type_distribution: Dict[str, int]
    avg_clustering: float
    performance_stats: Dict[str, Any]


class PathResponse(BaseModel):
    """Response model for path finding"""
    source: str
    target: str
    path: List[NodeResponse]
    path_length: int
    exists: bool


# =================== NODE ENDPOINTS ===================

@router.get("/nodes", response_model=List[NodeResponse])
async def list_nodes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    node_type: Optional[NodeTypeEnum] = Query(None, description="Filter by node type"),
    search: Optional[str] = Query(None, description="Search in node names"),
    min_importance: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum importance"),
    sort_by: str = Query("importance", description="Sort field: importance, name, created_at, access_count"),
    sort_desc: bool = Query(True, description="Sort descending"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List graph nodes with filtering, search, and pagination.
    
    Returns nodes with their attributes, importance scores, and access patterns.
    """
    try:
        query = select(GraphNode)
        
        # Apply filters
        filters = []
        if node_type:
            filters.append(GraphNode.node_type == node_type)
        if search:
            filters.append(GraphNode.name.ilike(f"%{search}%"))
        if min_importance is not None:
            filters.append(GraphNode.importance >= min_importance)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply sorting
        if sort_by == "importance":
            sort_field = GraphNode.importance
        elif sort_by == "name":
            sort_field = GraphNode.name
        elif sort_by == "created_at":
            sort_field = GraphNode.created_at
        elif sort_by == "access_count":
            sort_field = GraphNode.access_count
        else:
            sort_field = GraphNode.importance
        
        if sort_desc:
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        nodes = result.scalars().all()
        
        return [NodeResponse(
            id=str(node.id),
            name=node.name,
            node_type=node.node_type.value,
            attributes=node.attributes,
            importance=node.importance,
            access_count=node.access_count,
            last_accessed=node.last_accessed,
            created_at=node.created_at
        ) for node in nodes]
        
    except Exception as e:
        logger.error(f"Error listing nodes: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve nodes")


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed information about a specific node.
    
    Includes all attributes, relationships, and metadata.
    """
    try:
        query = select(GraphNode).where(GraphNode.id == UUID(node_id))
        result = await session.execute(query)
        node = result.scalar_one_or_none()
        
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Update access count
        node.access_count += 1
        node.last_accessed = datetime.now()
        await session.commit()
        
        return NodeResponse(
            id=str(node.id),
            name=node.name,
            node_type=node.node_type.value,
            attributes=node.attributes,
            importance=node.importance,
            access_count=node.access_count,
            last_accessed=node.last_accessed,
            created_at=node.created_at
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node {node_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve node")


@router.post("/nodes", response_model=NodeResponse)
async def create_node(
    node_request: NodeCreateRequest,
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Create a new node in the knowledge graph.
    
    Automatically generates search terms and handles duplicate detection.
    """
    try:
        node = await kg.add_node(
            name=node_request.name,
            node_type=node_request.node_type,
            attributes=node_request.attributes,
            importance=node_request.importance
        )
        
        return NodeResponse(
            id=str(node.id),
            name=node.name,
            node_type=node.node_type.value,
            attributes=node.attributes,
            importance=node.importance,
            access_count=node.access_count,
            last_accessed=node.last_accessed,
            created_at=node.created_at
        )
        
    except Exception as e:
        logger.error(f"Error creating node: {e}")
        raise HTTPException(status_code=500, detail="Failed to create node")


# =================== EDGE ENDPOINTS ===================

@router.get("/edges", response_model=List[EdgeResponse])
async def list_edges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    edge_type: Optional[EdgeTypeEnum] = Query(None, description="Filter by edge type"),
    source_id: Optional[str] = Query(None, description="Filter by source node ID"),
    target_id: Optional[str] = Query(None, description="Filter by target node ID"),
    min_weight: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum edge weight"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    List graph edges with filtering and pagination.
    
    Returns edges with weights, confidence scores, and relationship metadata.
    """
    try:
        query = select(GraphEdge)
        
        # Apply filters
        filters = []
        if edge_type:
            filters.append(GraphEdge.edge_type == edge_type)
        if source_id:
            filters.append(GraphEdge.source_id == UUID(source_id))
        if target_id:
            filters.append(GraphEdge.target_id == UUID(target_id))
        if min_weight is not None:
            filters.append(GraphEdge.weight >= min_weight)
        if min_confidence is not None:
            filters.append(GraphEdge.confidence >= min_confidence)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Order by weight (strongest connections first)
        query = query.order_by(desc(GraphEdge.weight)).offset(skip).limit(limit)
        
        result = await session.execute(query)
        edges = result.scalars().all()
        
        return [EdgeResponse(
            id=str(edge.id),
            source_id=str(edge.source_id),
            target_id=str(edge.target_id),
            edge_type=edge.edge_type.value,
            weight=edge.weight,
            confidence=edge.confidence,
            attributes=edge.attributes,
            reinforcement_count=edge.reinforcement_count,
            last_reinforced=edge.last_reinforced,
            created_at=edge.created_at
        ) for edge in edges]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        logger.error(f"Error listing edges: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve edges")


@router.post("/edges", response_model=EdgeResponse)
async def create_edge(
    edge_request: EdgeCreateRequest,
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Create a new edge in the knowledge graph.
    
    Automatically handles duplicate detection and reinforcement.
    """
    try:
        edge = await kg.add_edge(
            source_id=edge_request.source_id,
            target_id=edge_request.target_id,
            edge_type=edge_request.edge_type,
            weight=edge_request.weight,
            confidence=edge_request.confidence,
            attributes=edge_request.attributes
        )
        
        return EdgeResponse(
            id=str(edge.id),
            source_id=str(edge.source_id),
            target_id=str(edge.target_id),
            edge_type=edge.edge_type.value,
            weight=edge.weight,
            confidence=edge.confidence,
            attributes=edge.attributes,
            reinforcement_count=edge.reinforcement_count,
            last_reinforced=edge.last_reinforced,
            created_at=edge.created_at
        )
        
    except Exception as e:
        logger.error(f"Error creating edge: {e}")
        raise HTTPException(status_code=500, detail="Failed to create edge")


# =================== INSIGHTS AND PATTERNS ===================

@router.get("/insights", response_model=List[ProjectInsightResponse])
async def get_cross_project_insights(
    limit: int = Query(20, ge=1, le=50, description="Maximum insights to return"),
    insight_type: Optional[str] = Query(None, description="Filter by insight type"),
    min_impact: Optional[float] = Query(None, ge=0.0, description="Minimum impact score"),
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Get cross-project insights and intelligence.
    
    Discovers patterns, technology usage, and decision networks
    across all projects in the knowledge graph.
    """
    try:
        insights = await kg.get_cross_project_insights(limit=limit)
        
        # Apply filters
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]
        if min_impact is not None:
            insights = [i for i in insights if i.impact_score >= min_impact]
        
        return [ProjectInsightResponse(
            insight_type=insight.insight_type,
            title=insight.title,
            description=insight.description,
            confidence=insight.confidence,
            evidence=insight.evidence,
            related_projects=insight.related_projects,
            recommendations=insight.recommendations,
            impact_score=insight.impact_score
        ) for insight in insights]
        
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve insights")


@router.get("/technologies", response_model=List[TechnologyMappingResponse])
async def get_technology_patterns(
    min_usage: int = Query(1, ge=1, description="Minimum usage count"),
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Get technology usage patterns and compatibility mappings.
    
    Analyzes technology adoption, success rates, and compatibility
    patterns across all projects.
    """
    try:
        mappings = await kg.discover_technology_patterns()
        
        # Filter by minimum usage
        filtered_mappings = [m for m in mappings if m.usage_count >= min_usage]
        
        return [TechnologyMappingResponse(
            technology=mapping.technology,
            usage_count=mapping.usage_count,
            success_rate=mapping.success_rate,
            compatible_technologies=mapping.compatible_technologies,
            competing_technologies=mapping.competing_technologies,
            recommended_projects=mapping.recommended_projects,
            skill_requirements=mapping.skill_requirements
        ) for mapping in filtered_mappings]
        
    except Exception as e:
        logger.error(f"Error getting technology patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve technology patterns")


@router.get("/clusters", response_model=List[ClusterResponse])
async def get_graph_clusters(
    min_size: int = Query(3, ge=2, description="Minimum cluster size"),
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Get graph clustering analysis and community detection results.
    
    Uses community detection algorithms to identify related
    groups of nodes and their characteristics.
    """
    try:
        clusters = await kg.cluster_analysis()
        
        # Filter by minimum size
        filtered_clusters = [c for c in clusters if c['size'] >= min_size]
        
        return [ClusterResponse(
            cluster_id=cluster['cluster_id'],
            size=cluster['size'],
            node_types=cluster['node_types'],
            avg_importance=cluster['avg_importance'],
            dominant_type=cluster['dominant_type'],
            members=cluster['members']
        ) for cluster in filtered_clusters]
        
    except Exception as e:
        logger.error(f"Error getting clusters: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve clusters")


@router.get("/path", response_model=PathResponse)
async def find_concept_path(
    source: str = Query(..., description="Source concept name"),
    target: str = Query(..., description="Target concept name"),
    max_depth: int = Query(4, ge=1, le=10, description="Maximum path depth"),
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Find conceptual path between two nodes in the knowledge graph.
    
    Uses graph traversal algorithms to find connections between
    concepts, technologies, or other entities.
    """
    try:
        path_nodes = await kg.find_path_between_concepts(
            source_name=source,
            target_name=target,
            max_depth=max_depth
        )
        
        path_response = [NodeResponse(
            id=str(node.id),
            name=node.name,
            node_type=node.node_type.value,
            attributes=node.attributes,
            importance=node.importance,
            access_count=node.access_count,
            last_accessed=node.last_accessed,
            created_at=node.created_at
        ) for node in path_nodes]
        
        return PathResponse(
            source=source,
            target=target,
            path=path_response,
            path_length=len(path_response),
            exists=len(path_response) > 0
        )
        
    except Exception as e:
        logger.error(f"Error finding path from {source} to {target}: {e}")
        raise HTTPException(status_code=500, detail="Failed to find path")


# =================== ANALYTICS AND STATISTICS ===================

@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_statistics(
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Get comprehensive knowledge graph statistics.
    
    Returns node/edge counts, type distributions, density metrics,
    and performance statistics.
    """
    try:
        stats = await kg.get_graph_statistics()
        
        return GraphStatsResponse(
            total_nodes=stats['total_nodes'],
            total_edges=stats['total_edges'],
            graph_nodes=stats['graph_nodes'],
            graph_edges=stats['graph_edges'],
            density=stats['density'],
            node_type_distribution=stats['node_type_distribution'],
            edge_type_distribution=stats['edge_type_distribution'],
            avg_clustering=stats['avg_clustering'],
            performance_stats=stats['performance_stats']
        )
        
    except Exception as e:
        logger.error(f"Error getting graph statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/visualization")
async def export_for_visualization(
    format: str = Query("json", description="Export format: json, d3"),
    node_limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit nodes for performance"),
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Export graph data for visualization tools.
    
    Returns graph structure in formats suitable for D3.js,
    Cytoscape, or other visualization libraries.
    """
    try:
        viz_data = await kg.export_for_visualization(format=format)
        
        # Apply node limit if specified
        if node_limit and len(viz_data['nodes']) > node_limit:
            # Keep highest importance nodes
            viz_data['nodes'] = sorted(
                viz_data['nodes'], 
                key=lambda n: n['importance'], 
                reverse=True
            )[:node_limit]
            
            # Filter edges to only include those between remaining nodes
            node_ids = {n['id'] for n in viz_data['nodes']}
            viz_data['edges'] = [
                e for e in viz_data['edges'] 
                if e['source'] in node_ids and e['target'] in node_ids
            ]
            
            viz_data['metadata']['filtered'] = True
            viz_data['metadata']['node_limit_applied'] = node_limit
        
        return viz_data
        
    except Exception as e:
        logger.error(f"Error exporting for visualization: {e}")
        raise HTTPException(status_code=500, detail="Failed to export visualization data")


# =================== SPECIALIZED ENDPOINTS ===================

@router.get("/personas/expertise")
async def get_persona_expertise(
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Get expertise mapping for all personas in the knowledge graph.
    
    Shows what technologies, skills, and concepts each persona
    is most connected to and knowledgeable about.
    """
    try:
        expertise_map = await kg.calculate_persona_expertise()
        
        return {
            "personas": expertise_map,
            "total_personas": len(expertise_map),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting persona expertise: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve persona expertise")


@router.get("/projects/{technology}/related")
async def find_related_projects(
    technology: str,
    max_results: int = Query(10, ge=1, le=50, description="Maximum results"),
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Find projects related to a specific technology.
    
    Discovers projects using similar or compatible technologies
    and provides recommendations for technology adoption.
    """
    try:
        insights = await kg.find_related_projects(
            technology=technology,
            max_results=max_results
        )
        
        return {
            "technology": technology,
            "insights": [ProjectInsightResponse(
                insight_type=insight.insight_type,
                title=insight.title,
                description=insight.description,
                confidence=insight.confidence,
                evidence=insight.evidence,
                related_projects=insight.related_projects,
                recommendations=insight.recommendations,
                impact_score=insight.impact_score
            ) for insight in insights],
            "count": len(insights)
        }
        
    except Exception as e:
        logger.error(f"Error finding related projects for {technology}: {e}")
        raise HTTPException(status_code=500, detail="Failed to find related projects")


@router.post("/analyze")
async def trigger_graph_analysis(
    background_tasks: BackgroundTasks,
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Trigger comprehensive graph analysis and pattern discovery.
    
    Runs advanced analytics including community detection,
    centrality analysis, and pattern discovery in the background.
    """
    try:
        # Clear existing caches to force recalculation
        kg._centrality_cache.clear()
        kg._community_cache = None
        kg._path_cache.clear()
        
        # Run analysis in background
        background_tasks.add_task(_run_comprehensive_analysis, kg)
        
        return {
            "message": "Graph analysis initiated",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering graph analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate analysis")


async def _run_comprehensive_analysis(kg: OptimusKnowledgeGraph):
    """Run comprehensive graph analysis in background"""
    try:
        logger.info("Starting comprehensive graph analysis")
        
        # Run clustering analysis
        await kg.cluster_analysis()
        
        # Generate insights
        await kg.get_cross_project_insights()
        
        # Update technology patterns
        await kg.discover_technology_patterns()
        
        logger.info("Comprehensive graph analysis completed")
        
    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {e}")


@router.get("/health")
async def knowledge_graph_health_check(
    kg: OptimusKnowledgeGraph = Depends(get_knowledge_graph)
):
    """
    Check knowledge graph system health and performance.
    
    Returns connectivity status, cache statistics, and performance metrics.
    """
    try:
        stats = await kg.get_graph_statistics()
        
        health_status = "healthy" if stats['total_nodes'] > 0 else "empty"
        if stats['performance_stats']['cache_misses'] > stats['performance_stats']['cache_hits'] * 2:
            health_status = "degraded"
        
        return {
            "status": health_status,
            "nodes": stats['total_nodes'],
            "edges": stats['total_edges'],
            "density": stats['density'],
            "cache_performance": {
                "hit_rate": stats['performance_stats']['cache_hits'] / 
                          (stats['performance_stats']['cache_hits'] + stats['performance_stats']['cache_misses'])
                          if (stats['performance_stats']['cache_hits'] + stats['performance_stats']['cache_misses']) > 0 else 0,
                "cache_hits": stats['performance_stats']['cache_hits'],
                "cache_misses": stats['performance_stats']['cache_misses']
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Knowledge graph health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
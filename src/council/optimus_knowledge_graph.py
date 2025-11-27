"""
Optimus Knowledge Graph System

Enhanced knowledge graph for cross-project intelligence, pattern discovery,
and decision support. Integrates with PostgreSQL for persistence and provides
analytics for project optimization and technology recommendations.
"""

import asyncio
import uuid
import hashlib
import numpy as np
import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from collections import defaultdict, deque
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.config import get_database_manager
from ..models.knowledge_graph import (
    GraphNode, GraphEdge, GraphCluster, ClusterMembership,
    GraphPathCache, GraphStatistics, NodeTypeEnum, EdgeTypeEnum
)


@dataclass
class ProjectInsight:
    """Cross-project intelligence and recommendations"""
    insight_type: str
    title: str
    description: str
    confidence: float
    evidence: List[str]
    related_projects: List[str]
    recommendations: List[str]
    impact_score: float


@dataclass
class TechnologyMapping:
    """Technology usage and compatibility mapping"""
    technology: str
    usage_count: int
    success_rate: float
    compatible_technologies: List[str]
    competing_technologies: List[str]
    recommended_projects: List[str]
    skill_requirements: List[str]


@dataclass
class DecisionNetwork:
    """Network of connected decisions and outcomes"""
    decision_id: str
    related_decisions: List[str]
    outcome_quality: float
    factors_considered: List[str]
    lessons_learned: List[str]
    applicability_contexts: List[str]


class OptimusKnowledgeGraph:
    """
    Advanced knowledge graph for Optimus project intelligence.
    
    Features:
    - Cross-project pattern discovery
    - Technology compatibility mapping
    - Decision support networks
    - Persona expertise mapping
    - Performance optimization insights
    """
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_database_manager()
        self.graph = nx.DiGraph()
        self.node_cache: Dict[str, GraphNode] = {}
        self.edge_cache: Dict[str, GraphEdge] = {}
        
        # Analytics caches
        self._centrality_cache: Dict[str, Dict[str, float]] = {}
        self._community_cache: Optional[List[Set[str]]] = None
        self._path_cache: Dict[Tuple[str, str], List[str]] = {}
        
        # Performance tracking
        self.query_stats = {
            'nodes_loaded': 0,
            'edges_loaded': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'db_queries': 0
        }
    
    @asynccontextmanager
    async def get_session(self):
        """Get async database session"""
        async with self.db_manager.get_async_session() as session:
            yield session
    
    async def initialize(self):
        """Initialize the knowledge graph"""
        await self._load_graph_into_memory()
    
    async def _load_graph_into_memory(self, limit: int = 10000):
        """Load graph data into memory for fast operations"""
        async with self.get_session() as session:
            # Load nodes with importance ordering
            nodes_query = (
                select(GraphNode)
                .options(selectinload(GraphNode.outgoing_edges))
                .order_by(desc(GraphNode.importance), desc(GraphNode.access_count))
                .limit(limit)
            )
            
            result = await session.execute(nodes_query)
            nodes = result.scalars().all()
            
            # Cache nodes and add to NetworkX graph
            for node in nodes:
                self.node_cache[str(node.id)] = node
                self.graph.add_node(str(node.id), node=node)
                
            self.query_stats['nodes_loaded'] = len(nodes)
            
            # Load edges for cached nodes
            if self.node_cache:
                node_ids = list(self.node_cache.keys())
                edges_query = (
                    select(GraphEdge)
                    .where(
                        and_(
                            GraphEdge.source_id.in_([uuid.UUID(nid) for nid in node_ids]),
                            GraphEdge.target_id.in_([uuid.UUID(nid) for nid in node_ids])
                        )
                    )
                    .order_by(desc(GraphEdge.weight))
                )
                
                result = await session.execute(edges_query)
                edges = result.scalars().all()
                
                for edge in edges:
                    source_id = str(edge.source_id)
                    target_id = str(edge.target_id)
                    
                    if source_id in self.node_cache and target_id in self.node_cache:
                        self.edge_cache[str(edge.id)] = edge
                        self.graph.add_edge(
                            source_id, target_id,
                            edge_id=str(edge.id),
                            edge=edge,
                            weight=edge.weight
                        )
                
                self.query_stats['edges_loaded'] = len(edges)
    
    async def add_project_node(self, 
                              project_name: str,
                              project_path: str,
                              technologies: List[str],
                              status: str = "active",
                              attributes: Optional[Dict[str, Any]] = None) -> GraphNode:
        """Add a project node with technology relationships"""
        
        # Create project node
        project_node = await self.add_node(
            name=project_name,
            node_type=NodeTypeEnum.PROJECT,
            attributes={
                "path": project_path,
                "status": status,
                "technologies": technologies,
                **(attributes or {})
            },
            importance=0.8  # Projects are important nodes
        )
        
        # Create technology nodes and relationships
        for tech in technologies:
            tech_node = await self.add_node(
                name=tech,
                node_type=NodeTypeEnum.TECHNOLOGY,
                importance=0.6
            )
            
            # Project uses technology
            await self.add_edge(
                source_id=project_node.id,
                target_id=tech_node.id,
                edge_type=EdgeTypeEnum.USES,
                weight=1.0,
                confidence=0.9
            )
        
        return project_node
    
    async def add_decision_node(self,
                               decision_title: str,
                               context: Dict[str, Any],
                               outcome: Dict[str, Any],
                               personas_involved: List[str],
                               confidence: float = 0.7) -> GraphNode:
        """Add a decision node with context and outcome tracking"""
        
        decision_node = await self.add_node(
            name=decision_title,
            node_type=NodeTypeEnum.DECISION,
            attributes={
                "context": context,
                "outcome": outcome,
                "personas_involved": personas_involved,
                "decision_date": datetime.now().isoformat()
            },
            importance=confidence
        )
        
        # Connect to persona nodes
        for persona_name in personas_involved:
            persona_node = await self.add_node(
                name=persona_name,
                node_type=NodeTypeEnum.PERSONA,
                importance=0.7
            )
            
            await self.add_edge(
                source_id=persona_node.id,
                target_id=decision_node.id,
                edge_type=EdgeTypeEnum.INFLUENCES,
                weight=0.8,
                confidence=0.8
            )
        
        return decision_node
    
    async def add_problem_solution_pair(self,
                                       problem_description: str,
                                       solution_description: str,
                                       success_rate: float,
                                       context: Dict[str, Any]) -> Tuple[GraphNode, GraphNode]:
        """Add problem and solution nodes with relationship"""
        
        problem_node = await self.add_node(
            name=problem_description,
            node_type=NodeTypeEnum.PROBLEM,
            attributes=context,
            importance=0.6
        )
        
        solution_node = await self.add_node(
            name=solution_description,
            node_type=NodeTypeEnum.SOLUTION,
            attributes={
                "success_rate": success_rate,
                **context
            },
            importance=success_rate
        )
        
        await self.add_edge(
            source_id=problem_node.id,
            target_id=solution_node.id,
            edge_type=EdgeTypeEnum.SOLVED_BY,
            weight=success_rate,
            confidence=success_rate,
            attributes={"context": context}
        )
        
        return problem_node, solution_node
    
    async def add_node(self,
                      name: str,
                      node_type: NodeTypeEnum,
                      attributes: Optional[Dict[str, Any]] = None,
                      importance: float = 0.5) -> GraphNode:
        """Add a node to the knowledge graph"""
        
        async with self.get_session() as session:
            # Check if node already exists
            existing_query = select(GraphNode).where(
                and_(
                    GraphNode.name == name,
                    GraphNode.node_type == node_type
                )
            )
            result = await session.execute(existing_query)
            existing_node = result.scalar_one_or_none()
            
            if existing_node:
                # Update existing node
                existing_node.attributes.update(attributes or {})
                existing_node.importance = max(existing_node.importance, importance)
                existing_node.access_count += 1
                existing_node.last_accessed = datetime.now()
                existing_node.updated_at = datetime.now()
                
                await session.commit()
                self.node_cache[str(existing_node.id)] = existing_node
                return existing_node
            
            # Create new node
            node = GraphNode(
                name=name,
                node_type=node_type,
                attributes=attributes or {},
                importance=importance,
                name_lower=name.lower(),
                search_terms=self._generate_search_terms(name, node_type, attributes)
            )
            
            session.add(node)
            await session.commit()
            await session.refresh(node)
            
            # Cache and add to graph
            self.node_cache[str(node.id)] = node
            self.graph.add_node(str(node.id), node=node)
            
            return node
    
    async def add_edge(self,
                      source_id: uuid.UUID,
                      target_id: uuid.UUID,
                      edge_type: EdgeTypeEnum,
                      weight: float = 1.0,
                      confidence: float = 0.5,
                      attributes: Optional[Dict[str, Any]] = None) -> GraphEdge:
        """Add an edge to the knowledge graph"""
        
        async with self.get_session() as session:
            # Check if edge already exists
            existing_query = select(GraphEdge).where(
                and_(
                    GraphEdge.source_id == source_id,
                    GraphEdge.target_id == target_id,
                    GraphEdge.edge_type == edge_type
                )
            )
            result = await session.execute(existing_query)
            existing_edge = result.scalar_one_or_none()
            
            if existing_edge:
                # Reinforce existing edge
                existing_edge.weight = (existing_edge.weight + weight) / 2
                existing_edge.confidence = max(existing_edge.confidence, confidence)
                existing_edge.reinforcement_count += 1
                existing_edge.last_reinforced = datetime.now()
                existing_edge.access_count += 1
                existing_edge.last_accessed = datetime.now()
                
                if attributes:
                    existing_edge.attributes.update(attributes)
                
                await session.commit()
                self.edge_cache[str(existing_edge.id)] = existing_edge
                return existing_edge
            
            # Create new edge
            edge = GraphEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                weight=weight,
                confidence=confidence,
                attributes=attributes or {}
            )
            
            session.add(edge)
            await session.commit()
            await session.refresh(edge)
            
            # Cache and add to graph
            self.edge_cache[str(edge.id)] = edge
            if str(source_id) in self.node_cache and str(target_id) in self.node_cache:
                self.graph.add_edge(
                    str(source_id), str(target_id),
                    edge_id=str(edge.id),
                    edge=edge,
                    weight=weight
                )
            
            return edge
    
    def _generate_search_terms(self, name: str, node_type: NodeTypeEnum, attributes: Optional[Dict[str, Any]]) -> str:
        """Generate search terms for full-text search"""
        terms = [name.lower(), node_type.value]
        
        if attributes:
            for key, value in attributes.items():
                if isinstance(value, (str, int, float)):
                    terms.append(str(value).lower())
                elif isinstance(value, list):
                    terms.extend([str(item).lower() for item in value])
        
        return ' '.join(terms)
    
    async def find_related_projects(self, 
                                   technology: str,
                                   max_results: int = 10) -> List[ProjectInsight]:
        """Find projects that use similar technologies"""
        
        async with self.get_session() as session:
            # Find technology node
            tech_query = select(GraphNode).where(
                and_(
                    GraphNode.name.ilike(f"%{technology}%"),
                    GraphNode.node_type == NodeTypeEnum.TECHNOLOGY
                )
            )
            result = await session.execute(tech_query)
            tech_nodes = result.scalars().all()
            
            if not tech_nodes:
                return []
            
            insights = []
            
            for tech_node in tech_nodes:
                # Find projects using this technology
                projects_query = select(GraphNode).join(
                    GraphEdge, GraphEdge.source_id == GraphNode.id
                ).where(
                    and_(
                        GraphEdge.target_id == tech_node.id,
                        GraphEdge.edge_type == EdgeTypeEnum.USES,
                        GraphNode.node_type == NodeTypeEnum.PROJECT
                    )
                ).order_by(desc(GraphEdge.weight))
                
                result = await session.execute(projects_query)
                projects = result.scalars().all()
                
                if projects:
                    insight = ProjectInsight(
                        insight_type="technology_usage",
                        title=f"Projects using {tech_node.name}",
                        description=f"Found {len(projects)} projects using {tech_node.name}",
                        confidence=0.8,
                        evidence=[f"Direct usage relationship with {len(projects)} projects"],
                        related_projects=[p.name for p in projects],
                        recommendations=[
                            f"Consider {tech_node.name} for similar project types",
                            "Review implementation patterns from existing projects"
                        ],
                        impact_score=len(projects) * 0.1
                    )
                    insights.append(insight)
            
            return insights[:max_results]
    
    async def discover_technology_patterns(self) -> List[TechnologyMapping]:
        """Discover technology usage patterns and compatibility"""
        
        async with self.get_session() as session:
            # Get all technology nodes
            tech_query = select(GraphNode).where(
                GraphNode.node_type == NodeTypeEnum.TECHNOLOGY
            )
            result = await session.execute(tech_query)
            technologies = result.scalars().all()
            
            mappings = []
            
            for tech in technologies:
                # Count usage
                usage_query = select(func.count(GraphEdge.id)).where(
                    and_(
                        GraphEdge.target_id == tech.id,
                        GraphEdge.edge_type == EdgeTypeEnum.USES
                    )
                )
                result = await session.execute(usage_query)
                usage_count = result.scalar() or 0
                
                # Find compatible technologies (used together)
                compatible_query = select(GraphNode).join(
                    GraphEdge, GraphEdge.target_id == GraphNode.id
                ).where(
                    and_(
                        GraphEdge.source_id.in_(
                            select(GraphEdge.source_id).where(
                                GraphEdge.target_id == tech.id
                            )
                        ),
                        GraphEdge.edge_type == EdgeTypeEnum.USES,
                        GraphNode.id != tech.id,
                        GraphNode.node_type == NodeTypeEnum.TECHNOLOGY
                    )
                ).distinct()
                
                result = await session.execute(compatible_query)
                compatible_techs = result.scalars().all()
                
                mapping = TechnologyMapping(
                    technology=tech.name,
                    usage_count=usage_count,
                    success_rate=tech.importance,  # Use importance as success rate proxy
                    compatible_technologies=[t.name for t in compatible_techs],
                    competing_technologies=[],  # TODO: Implement competing tech detection
                    recommended_projects=[],    # TODO: Implement project recommendations
                    skill_requirements=[]       # TODO: Implement skill mapping
                )
                
                mappings.append(mapping)
            
            return sorted(mappings, key=lambda m: m.usage_count, reverse=True)
    
    async def find_decision_patterns(self, context_similarity: float = 0.7) -> List[DecisionNetwork]:
        """Find patterns in decision making across contexts"""
        
        async with self.get_session() as session:
            # Get all decision nodes
            decisions_query = select(GraphNode).where(
                GraphNode.node_type == NodeTypeEnum.DECISION
            ).order_by(desc(GraphNode.importance))
            
            result = await session.execute(decisions_query)
            decisions = result.scalars().all()
            
            networks = []
            
            for decision in decisions:
                # Find related decisions through persona connections
                related_query = select(GraphNode).join(
                    GraphEdge, GraphEdge.target_id == GraphNode.id
                ).where(
                    and_(
                        GraphEdge.source_id.in_(
                            select(GraphEdge.source_id).where(
                                and_(
                                    GraphEdge.target_id == decision.id,
                                    GraphEdge.edge_type == EdgeTypeEnum.INFLUENCES
                                )
                            )
                        ),
                        GraphEdge.edge_type == EdgeTypeEnum.INFLUENCES,
                        GraphNode.node_type == NodeTypeEnum.DECISION,
                        GraphNode.id != decision.id
                    )
                )
                
                result = await session.execute(related_query)
                related_decisions = result.scalars().all()
                
                # Extract insights from decision attributes
                context = decision.attributes.get('context', {})
                outcome = decision.attributes.get('outcome', {})
                
                network = DecisionNetwork(
                    decision_id=str(decision.id),
                    related_decisions=[str(d.id) for d in related_decisions],
                    outcome_quality=decision.importance,
                    factors_considered=list(context.keys()) if isinstance(context, dict) else [],
                    lessons_learned=[],  # TODO: Extract from outcome analysis
                    applicability_contexts=[]  # TODO: Determine context patterns
                )
                
                networks.append(network)
            
            return networks
    
    async def calculate_persona_expertise(self) -> Dict[str, List[str]]:
        """Calculate expertise mapping for each persona"""
        
        async with self.get_session() as session:
            # Get persona nodes and their connections
            personas_query = select(GraphNode).where(
                GraphNode.node_type == NodeTypeEnum.PERSONA
            )
            result = await session.execute(personas_query)
            personas = result.scalars().all()
            
            expertise_map = {}
            
            for persona in personas:
                # Find technologies/skills connected to this persona
                expertise_query = select(GraphNode, GraphEdge.weight).join(
                    GraphEdge, GraphEdge.target_id == GraphNode.id
                ).where(
                    and_(
                        GraphEdge.source_id == persona.id,
                        GraphNode.node_type.in_([
                            NodeTypeEnum.TECHNOLOGY,
                            NodeTypeEnum.SKILL,
                            NodeTypeEnum.CONCEPT
                        ])
                    )
                ).order_by(desc(GraphEdge.weight))
                
                result = await session.execute(expertise_query)
                expertise_items = result.all()
                
                expertise_map[persona.name] = [
                    item[0].name for item in expertise_items 
                    if item[1] > 0.5  # Only include strong connections
                ]
            
            return expertise_map
    
    async def get_cross_project_insights(self, limit: int = 20) -> List[ProjectInsight]:
        """Get comprehensive cross-project intelligence"""
        
        insights = []
        
        # Technology pattern insights
        tech_patterns = await self.discover_technology_patterns()
        for pattern in tech_patterns[:5]:
            if pattern.usage_count > 1:
                insight = ProjectInsight(
                    insight_type="technology_pattern",
                    title=f"{pattern.technology} Usage Pattern",
                    description=f"Used in {pattern.usage_count} projects with {len(pattern.compatible_technologies)} compatible technologies",
                    confidence=min(pattern.usage_count / 10.0, 1.0),
                    evidence=[f"Usage count: {pattern.usage_count}"],
                    related_projects=[],
                    recommendations=[
                        f"Consider {pattern.technology} for new projects",
                        f"Pair with: {', '.join(pattern.compatible_technologies[:3])}"
                    ],
                    impact_score=pattern.usage_count * 0.2
                )
                insights.append(insight)
        
        # Decision network insights
        decision_networks = await self.find_decision_patterns()
        for network in decision_networks[:5]:
            if len(network.related_decisions) > 0:
                insight = ProjectInsight(
                    insight_type="decision_pattern",
                    title="Decision Network Pattern",
                    description=f"Decision connected to {len(network.related_decisions)} similar decisions",
                    confidence=network.outcome_quality,
                    evidence=[f"{len(network.factors_considered)} factors considered"],
                    related_projects=[],
                    recommendations=["Apply similar decision framework"],
                    impact_score=len(network.related_decisions) * 0.3
                )
                insights.append(insight)
        
        # Sort by impact score and return top insights
        insights.sort(key=lambda x: x.impact_score, reverse=True)
        return insights[:limit]
    
    async def find_path_between_concepts(self, 
                                       source_name: str,
                                       target_name: str,
                                       max_depth: int = 4) -> List[GraphNode]:
        """Find conceptual path between two nodes"""
        
        # Check memory cache first
        cache_key = (source_name, target_name)
        if cache_key in self._path_cache:
            path_ids = self._path_cache[cache_key]
            return [self.node_cache[nid] for nid in path_ids if nid in self.node_cache]
        
        try:
            # Find nodes in NetworkX graph
            source_nodes = [nid for nid, data in self.graph.nodes(data=True) 
                           if data.get('node') and source_name.lower() in data['node'].name.lower()]
            target_nodes = [nid for nid, data in self.graph.nodes(data=True)
                           if data.get('node') and target_name.lower() in data['node'].name.lower()]
            
            if not source_nodes or not target_nodes:
                return []
            
            # Find shortest path
            try:
                path_ids = nx.shortest_path(self.graph, source_nodes[0], target_nodes[0])
                self._path_cache[cache_key] = path_ids
                return [self.node_cache[nid] for nid in path_ids if nid in self.node_cache]
            except nx.NetworkXNoPath:
                return []
                
        except Exception as e:
            print(f"Error finding path between {source_name} and {target_name}: {e}")
            return []
    
    async def cluster_analysis(self) -> List[Dict[str, Any]]:
        """Perform community detection and clustering analysis"""
        
        if not self._community_cache:
            try:
                # Convert to undirected for community detection
                undirected = self.graph.to_undirected()
                
                # Find communities using Louvain algorithm
                import networkx.algorithms.community as nx_comm
                communities = nx_comm.greedy_modularity_communities(undirected)
                self._community_cache = [set(community) for community in communities]
                
            except Exception as e:
                print(f"Error in community detection: {e}")
                self._community_cache = []
        
        # Convert communities to analysis format
        cluster_analysis = []
        for i, community in enumerate(self._community_cache):
            if len(community) > 2:  # Only consider meaningful clusters
                # Analyze cluster composition
                node_types = defaultdict(int)
                importance_scores = []
                
                for node_id in community:
                    if node_id in self.node_cache:
                        node = self.node_cache[node_id]
                        node_types[node.node_type.value] += 1
                        importance_scores.append(node.importance)
                
                avg_importance = np.mean(importance_scores) if importance_scores else 0
                
                cluster_info = {
                    'cluster_id': i,
                    'size': len(community),
                    'node_types': dict(node_types),
                    'avg_importance': avg_importance,
                    'dominant_type': max(node_types.items(), key=lambda x: x[1])[0] if node_types else None,
                    'members': list(community)
                }
                
                cluster_analysis.append(cluster_info)
        
        return sorted(cluster_analysis, key=lambda x: x['size'], reverse=True)
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics"""
        
        stats = {
            'total_nodes': len(self.node_cache),
            'total_edges': len(self.edge_cache),
            'graph_nodes': self.graph.number_of_nodes(),
            'graph_edges': self.graph.number_of_edges(),
            'density': nx.density(self.graph) if self.graph.number_of_nodes() > 1 else 0,
            'node_type_distribution': defaultdict(int),
            'edge_type_distribution': defaultdict(int),
            'avg_clustering': nx.average_clustering(self.graph.to_undirected()) if self.graph.number_of_nodes() > 0 else 0,
            'performance_stats': self.query_stats.copy()
        }
        
        # Count node types
        for node in self.node_cache.values():
            stats['node_type_distribution'][node.node_type.value] += 1
        
        # Count edge types
        for edge in self.edge_cache.values():
            stats['edge_type_distribution'][edge.edge_type.value] += 1
        
        # Convert defaultdicts to regular dicts
        stats['node_type_distribution'] = dict(stats['node_type_distribution'])
        stats['edge_type_distribution'] = dict(stats['edge_type_distribution'])
        
        return stats
    
    async def export_for_visualization(self, format: str = "json") -> Dict[str, Any]:
        """Export graph data for visualization (D3.js compatible)"""
        
        nodes = []
        edges = []
        
        # Export nodes
        for node_id, node in self.node_cache.items():
            nodes.append({
                'id': node_id,
                'name': node.name,
                'type': node.node_type.value,
                'importance': node.importance,
                'attributes': node.attributes,
                'access_count': node.access_count
            })
        
        # Export edges
        for edge_id, edge in self.edge_cache.items():
            edges.append({
                'id': edge_id,
                'source': str(edge.source_id),
                'target': str(edge.target_id),
                'type': edge.edge_type.value,
                'weight': edge.weight,
                'confidence': edge.confidence
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'format': format
            }
        }
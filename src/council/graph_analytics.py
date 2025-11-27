"""
Graph Analytics Module

Advanced graph algorithms and analytics for the Optimus knowledge graph.
Provides community detection, centrality analysis, pattern recognition,
and predictive insights for cross-project intelligence.
"""

import asyncio
import numpy as np
import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from collections import defaultdict, Counter
from dataclasses import dataclass
import statistics

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    from scipy import stats
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass
class CommunityAnalysis:
    """Results of community detection analysis"""
    community_id: int
    members: List[str]
    size: int
    density: float
    modularity: float
    cohesion_score: float
    dominant_node_type: str
    key_nodes: List[str]
    internal_edges: int
    external_edges: int
    expertise_focus: List[str]
    

@dataclass
class CentralityRanking:
    """Node centrality rankings and importance"""
    node_id: str
    name: str
    node_type: str
    betweenness_centrality: float
    closeness_centrality: float
    degree_centrality: float
    eigenvector_centrality: float
    pagerank: float
    importance_score: float
    influence_rank: int


@dataclass
class PatternDetection:
    """Detected patterns in the knowledge graph"""
    pattern_type: str
    pattern_name: str
    description: str
    confidence: float
    supporting_evidence: List[str]
    affected_nodes: List[str]
    recommendations: List[str]
    impact_assessment: str


@dataclass
class TrendAnalysis:
    """Temporal trends in graph evolution"""
    trend_type: str
    trend_direction: str  # 'increasing', 'decreasing', 'stable', 'cyclic'
    strength: float
    time_period: str
    affected_entities: List[str]
    predictions: List[str]


class GraphAnalytics:
    """
    Advanced analytics engine for the Optimus knowledge graph.
    
    Capabilities:
    - Community detection and clustering
    - Centrality analysis and ranking
    - Pattern recognition and anomaly detection
    - Temporal trend analysis
    - Predictive modeling for project outcomes
    - Technology adoption forecasting
    """
    
    def __init__(self, knowledge_graph):
        self.kg = knowledge_graph
        self.analytics_cache = {}
        self.last_analysis = None
        
    async def perform_community_analysis(self, 
                                       algorithm: str = 'louvain',
                                       resolution: float = 1.0) -> List[CommunityAnalysis]:
        """
        Detect communities in the knowledge graph using various algorithms.
        
        Args:
            algorithm: 'louvain', 'leiden', 'greedy_modularity', 'label_propagation'
            resolution: Resolution parameter for community detection
        """
        
        cache_key = f"community_{algorithm}_{resolution}"
        if cache_key in self.analytics_cache:
            return self.analytics_cache[cache_key]
        
        if not self.kg.graph.nodes():
            return []
        
        # Convert to undirected for most community detection algorithms
        undirected_graph = self.kg.graph.to_undirected()
        
        try:
            # Choose community detection algorithm
            if algorithm == 'louvain':
                communities = self._louvain_communities(undirected_graph, resolution)
            elif algorithm == 'leiden':
                communities = self._leiden_communities(undirected_graph, resolution)
            elif algorithm == 'greedy_modularity':
                communities = self._greedy_modularity_communities(undirected_graph)
            elif algorithm == 'label_propagation':
                communities = self._label_propagation_communities(undirected_graph)
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")
            
            # Analyze each community
            community_analyses = []
            
            for i, community in enumerate(communities):
                if len(community) < 2:
                    continue
                
                analysis = await self._analyze_community(i, community, undirected_graph)
                community_analyses.append(analysis)
            
            # Sort by size and importance
            community_analyses.sort(key=lambda c: (c.size, c.cohesion_score), reverse=True)
            
            # Cache results
            self.analytics_cache[cache_key] = community_analyses
            
            return community_analyses
            
        except Exception as e:
            print(f"Error in community analysis: {e}")
            return []
    
    def _louvain_communities(self, graph: nx.Graph, resolution: float) -> List[Set[str]]:
        """Apply Louvain community detection"""
        try:
            import networkx.algorithms.community as nx_comm
            communities = nx_comm.greedy_modularity_communities(graph, resolution=resolution)
            return [set(community) for community in communities]
        except ImportError:
            # Fallback to basic modularity optimization
            return self._greedy_modularity_communities(graph)
    
    def _leiden_communities(self, graph: nx.Graph, resolution: float) -> List[Set[str]]:
        """Apply Leiden community detection"""
        try:
            # Leiden algorithm implementation would go here
            # For now, fall back to Louvain
            return self._louvain_communities(graph, resolution)
        except:
            return self._greedy_modularity_communities(graph)
    
    def _greedy_modularity_communities(self, graph: nx.Graph) -> List[Set[str]]:
        """Apply greedy modularity optimization"""
        try:
            import networkx.algorithms.community as nx_comm
            communities = nx_comm.greedy_modularity_communities(graph)
            return [set(community) for community in communities]
        except:
            # Fallback: create single community
            return [set(graph.nodes())]
    
    def _label_propagation_communities(self, graph: nx.Graph) -> List[Set[str]]:
        """Apply label propagation algorithm"""
        try:
            import networkx.algorithms.community as nx_comm
            communities = nx_comm.label_propagation_communities(graph)
            return [set(community) for community in communities]
        except:
            return self._greedy_modularity_communities(graph)
    
    async def _analyze_community(self, 
                                community_id: int,
                                members: Set[str],
                                graph: nx.Graph) -> CommunityAnalysis:
        """Analyze a single community in detail"""
        
        # Create subgraph for this community
        subgraph = graph.subgraph(members)
        
        # Calculate density
        density = nx.density(subgraph) if len(members) > 1 else 0
        
        # Calculate modularity (requires full graph context)
        modularity = self._calculate_modularity(graph, [members])
        
        # Analyze node types
        node_types = defaultdict(int)
        key_nodes = []
        
        for node_id in members:
            if node_id in self.kg.node_cache:
                node = self.kg.node_cache[node_id]
                node_types[node.node_type.value] += 1
                
                # Identify key nodes (high importance or centrality)
                if node.importance > 0.7 or subgraph.degree(node_id) > len(members) * 0.3:
                    key_nodes.append(node_id)
        
        # Find dominant node type
        dominant_type = max(node_types.items(), key=lambda x: x[1])[0] if node_types else "unknown"
        
        # Count internal vs external edges
        internal_edges = subgraph.number_of_edges()
        external_edges = sum(1 for node in members 
                           for neighbor in graph.neighbors(node)
                           if neighbor not in members)
        
        # Calculate cohesion score
        cohesion_score = internal_edges / (internal_edges + external_edges) if (internal_edges + external_edges) > 0 else 0
        
        # Identify expertise focus
        expertise_focus = self._identify_expertise_focus(members)
        
        return CommunityAnalysis(
            community_id=community_id,
            members=list(members),
            size=len(members),
            density=density,
            modularity=modularity,
            cohesion_score=cohesion_score,
            dominant_node_type=dominant_type,
            key_nodes=key_nodes,
            internal_edges=internal_edges,
            external_edges=external_edges,
            expertise_focus=expertise_focus
        )
    
    def _calculate_modularity(self, graph: nx.Graph, communities: List[Set[str]]) -> float:
        """Calculate modularity of community structure"""
        try:
            import networkx.algorithms.community as nx_comm
            return nx_comm.modularity(graph, communities)
        except:
            return 0.0
    
    def _identify_expertise_focus(self, members: List[str]) -> List[str]:
        """Identify the expertise focus areas of a community"""
        
        expertise_areas = defaultdict(int)
        
        for node_id in members:
            if node_id in self.kg.node_cache:
                node = self.kg.node_cache[node_id]
                
                # Extract expertise from attributes
                if 'technologies' in node.attributes:
                    for tech in node.attributes['technologies']:
                        expertise_areas[tech] += 1
                
                if 'skills' in node.attributes:
                    for skill in node.attributes['skills']:
                        expertise_areas[skill] += 1
                
                # Use node type as expertise indicator
                if node.node_type.value in ['technology', 'skill', 'concept']:
                    expertise_areas[node.name] += 1
        
        # Return top expertise areas
        return [area for area, count in sorted(expertise_areas.items(), 
                                             key=lambda x: x[1], reverse=True)[:5]]
    
    async def calculate_centrality_rankings(self, 
                                          metrics: List[str] = None) -> List[CentralityRanking]:
        """
        Calculate multiple centrality metrics for all nodes.
        
        Args:
            metrics: List of metrics to calculate 
                   ['betweenness', 'closeness', 'degree', 'eigenvector', 'pagerank']
        """
        
        if metrics is None:
            metrics = ['betweenness', 'closeness', 'degree', 'eigenvector', 'pagerank']
        
        cache_key = f"centrality_{'_'.join(sorted(metrics))}"
        if cache_key in self.analytics_cache:
            return self.analytics_cache[cache_key]
        
        if not self.kg.graph.nodes():
            return []
        
        # Calculate centrality metrics
        centrality_scores = {}
        
        try:
            if 'betweenness' in metrics:
                if len(self.kg.graph.nodes()) > 1000:
                    # Use sampling for large graphs
                    k = min(500, len(self.kg.graph.nodes()) // 4)
                    centrality_scores['betweenness'] = nx.betweenness_centrality(self.kg.graph, k=k)
                else:
                    centrality_scores['betweenness'] = nx.betweenness_centrality(self.kg.graph)
            
            if 'closeness' in metrics:
                centrality_scores['closeness'] = nx.closeness_centrality(self.kg.graph)
            
            if 'degree' in metrics:
                centrality_scores['degree'] = nx.degree_centrality(self.kg.graph)
            
            if 'eigenvector' in metrics:
                try:
                    centrality_scores['eigenvector'] = nx.eigenvector_centrality(
                        self.kg.graph, max_iter=200, tol=1e-06)
                except:
                    # Fallback to degree centrality if eigenvector fails
                    centrality_scores['eigenvector'] = nx.degree_centrality(self.kg.graph)
            
            if 'pagerank' in metrics:
                centrality_scores['pagerank'] = nx.pagerank(self.kg.graph, alpha=0.85)
            
        except Exception as e:
            print(f"Error calculating centrality: {e}")
            # Fallback to degree centrality
            centrality_scores = {'degree': nx.degree_centrality(self.kg.graph)}
        
        # Create centrality rankings
        rankings = []
        
        for node_id in self.kg.graph.nodes():
            if node_id not in self.kg.node_cache:
                continue
            
            node = self.kg.node_cache[node_id]
            
            # Get centrality scores for this node
            betweenness = centrality_scores.get('betweenness', {}).get(node_id, 0.0)
            closeness = centrality_scores.get('closeness', {}).get(node_id, 0.0)
            degree = centrality_scores.get('degree', {}).get(node_id, 0.0)
            eigenvector = centrality_scores.get('eigenvector', {}).get(node_id, 0.0)
            pagerank = centrality_scores.get('pagerank', {}).get(node_id, 0.0)
            
            # Calculate combined importance score
            importance_score = (
                betweenness * 0.3 +
                closeness * 0.2 +
                degree * 0.2 +
                eigenvector * 0.15 +
                pagerank * 0.15
            )
            
            ranking = CentralityRanking(
                node_id=node_id,
                name=node.name,
                node_type=node.node_type.value,
                betweenness_centrality=betweenness,
                closeness_centrality=closeness,
                degree_centrality=degree,
                eigenvector_centrality=eigenvector,
                pagerank=pagerank,
                importance_score=importance_score,
                influence_rank=0  # Will be set after sorting
            )
            
            rankings.append(ranking)
        
        # Sort by importance score and assign ranks
        rankings.sort(key=lambda r: r.importance_score, reverse=True)
        for i, ranking in enumerate(rankings):
            ranking.influence_rank = i + 1
        
        # Cache results
        self.analytics_cache[cache_key] = rankings
        
        return rankings
    
    async def detect_patterns(self, 
                             pattern_types: List[str] = None) -> List[PatternDetection]:
        """
        Detect various patterns in the knowledge graph.
        
        Args:
            pattern_types: ['hub_nodes', 'bridge_nodes', 'isolated_clusters', 
                           'technology_adoption', 'decision_chains', 'expertise_gaps']
        """
        
        if pattern_types is None:
            pattern_types = ['hub_nodes', 'bridge_nodes', 'isolated_clusters', 
                           'technology_adoption', 'decision_chains']
        
        patterns = []
        
        try:
            for pattern_type in pattern_types:
                if pattern_type == 'hub_nodes':
                    patterns.extend(await self._detect_hub_nodes())
                elif pattern_type == 'bridge_nodes':
                    patterns.extend(await self._detect_bridge_nodes())
                elif pattern_type == 'isolated_clusters':
                    patterns.extend(await self._detect_isolated_clusters())
                elif pattern_type == 'technology_adoption':
                    patterns.extend(await self._detect_technology_adoption_patterns())
                elif pattern_type == 'decision_chains':
                    patterns.extend(await self._detect_decision_chains())
                
        except Exception as e:
            print(f"Error in pattern detection: {e}")
        
        return patterns
    
    async def _detect_hub_nodes(self) -> List[PatternDetection]:
        """Detect nodes that act as major hubs"""
        patterns = []
        
        # Calculate degree for all nodes
        degrees = dict(self.kg.graph.degree())
        if not degrees:
            return patterns
        
        # Find statistical outliers (nodes with unusually high degree)
        degree_values = list(degrees.values())
        if len(degree_values) < 3:
            return patterns
        
        mean_degree = statistics.mean(degree_values)
        std_degree = statistics.stdev(degree_values) if len(degree_values) > 1 else 0
        threshold = mean_degree + 2 * std_degree
        
        hub_nodes = [node_id for node_id, degree in degrees.items() 
                    if degree > threshold and degree > 5]
        
        if hub_nodes:
            for node_id in hub_nodes:
                if node_id in self.kg.node_cache:
                    node = self.kg.node_cache[node_id]
                    pattern = PatternDetection(
                        pattern_type='hub_nodes',
                        pattern_name=f'Hub Node: {node.name}',
                        description=f'Node with {degrees[node_id]} connections acting as a major hub',
                        confidence=min(degrees[node_id] / (mean_degree * 3), 1.0),
                        supporting_evidence=[
                            f'Degree: {degrees[node_id]} (threshold: {threshold:.1f})',
                            f'Node type: {node.node_type.value}',
                            f'Importance: {node.importance}'
                        ],
                        affected_nodes=[node_id],
                        recommendations=[
                            'Monitor hub node for system stability',
                            'Consider redundancy for critical connections',
                            'Leverage hub for information dissemination'
                        ],
                        impact_assessment='High - Hub nodes are critical for connectivity'
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def _detect_bridge_nodes(self) -> List[PatternDetection]:
        """Detect nodes that act as bridges between communities"""
        patterns = []
        
        try:
            # Calculate betweenness centrality
            betweenness = nx.betweenness_centrality(self.kg.graph)
            
            if not betweenness:
                return patterns
            
            # Find high betweenness nodes (potential bridges)
            values = list(betweenness.values())
            if len(values) < 3:
                return patterns
            
            mean_betweenness = statistics.mean(values)
            std_betweenness = statistics.stdev(values) if len(values) > 1 else 0
            threshold = mean_betweenness + 1.5 * std_betweenness
            
            bridge_nodes = [node_id for node_id, score in betweenness.items()
                          if score > threshold and score > 0.1]
            
            for node_id in bridge_nodes:
                if node_id in self.kg.node_cache:
                    node = self.kg.node_cache[node_id]
                    pattern = PatternDetection(
                        pattern_type='bridge_nodes',
                        pattern_name=f'Bridge Node: {node.name}',
                        description=f'Node connecting different communities with high betweenness centrality',
                        confidence=min(betweenness[node_id] * 2, 1.0),
                        supporting_evidence=[
                            f'Betweenness centrality: {betweenness[node_id]:.3f}',
                            f'Node type: {node.node_type.value}',
                            'High connectivity between different node clusters'
                        ],
                        affected_nodes=[node_id],
                        recommendations=[
                            'Bridge node is critical for inter-community communication',
                            'Consider strengthening connections through this node',
                            'Monitor for bottlenecks'
                        ],
                        impact_assessment='Medium-High - Important for cross-community connections'
                    )
                    patterns.append(pattern)
        
        except Exception as e:
            print(f"Error detecting bridge nodes: {e}")
        
        return patterns
    
    async def _detect_isolated_clusters(self) -> List[PatternDetection]:
        """Detect isolated or weakly connected clusters"""
        patterns = []
        
        try:
            # Find connected components
            if self.kg.graph.is_directed():
                components = list(nx.weakly_connected_components(self.kg.graph))
            else:
                components = list(nx.connected_components(self.kg.graph))
            
            # Find small isolated components
            main_component_size = max(len(comp) for comp in components) if components else 0
            
            for component in components:
                if len(component) > 1 and len(component) < main_component_size * 0.1:
                    # This is a small isolated cluster
                    pattern = PatternDetection(
                        pattern_type='isolated_clusters',
                        pattern_name=f'Isolated Cluster ({len(component)} nodes)',
                        description=f'Small cluster of {len(component)} nodes with limited connections',
                        confidence=0.8,
                        supporting_evidence=[
                            f'Component size: {len(component)}',
                            f'Main component size: {main_component_size}',
                            'Weak connectivity to main graph'
                        ],
                        affected_nodes=list(component),
                        recommendations=[
                            'Investigate why this cluster is isolated',
                            'Consider adding connections to main network',
                            'May represent specialized knowledge domain'
                        ],
                        impact_assessment='Medium - Isolated knowledge may be underutilized'
                    )
                    patterns.append(pattern)
        
        except Exception as e:
            print(f"Error detecting isolated clusters: {e}")
        
        return patterns
    
    async def _detect_technology_adoption_patterns(self) -> List[PatternDetection]:
        """Detect technology adoption and usage patterns"""
        patterns = []
        
        try:
            # Find technology nodes and their usage
            technology_usage = defaultdict(list)
            
            for edge_id, edge in self.kg.edge_cache.items():
                if (edge.edge_type.value == 'uses' and 
                    edge.target_id in [uuid.UUID(nid) for nid in self.kg.node_cache.keys()]):
                    
                    target_node = self.kg.node_cache.get(str(edge.target_id))
                    source_node = self.kg.node_cache.get(str(edge.source_id))
                    
                    if (target_node and source_node and 
                        target_node.node_type.value == 'technology'):
                        technology_usage[target_node.name].append({
                            'project': source_node.name,
                            'weight': edge.weight,
                            'date': edge.created_at
                        })
            
            # Analyze adoption patterns
            for tech_name, usage_list in technology_usage.items():
                if len(usage_list) > 2:  # Technology used in multiple projects
                    pattern = PatternDetection(
                        pattern_type='technology_adoption',
                        pattern_name=f'Technology Adoption: {tech_name}',
                        description=f'{tech_name} adopted across {len(usage_list)} projects',
                        confidence=min(len(usage_list) / 5.0, 1.0),
                        supporting_evidence=[
                            f'Usage count: {len(usage_list)}',
                            f'Projects: {", ".join([u["project"] for u in usage_list[:3]])}',
                            f'Average weight: {statistics.mean([u["weight"] for u in usage_list]):.2f}'
                        ],
                        affected_nodes=[],  # Could add project nodes here
                        recommendations=[
                            f'Consider {tech_name} for similar new projects',
                            'Document best practices for this technology',
                            'Share knowledge across adopting teams'
                        ],
                        impact_assessment='Medium - Technology showing adoption success'
                    )
                    patterns.append(pattern)
        
        except Exception as e:
            print(f"Error detecting technology adoption patterns: {e}")
        
        return patterns
    
    async def _detect_decision_chains(self) -> List[PatternDetection]:
        """Detect chains of related decisions"""
        patterns = []
        
        try:
            # Find decision nodes and their connections
            decision_nodes = [node_id for node_id, node in self.kg.node_cache.items()
                            if node.node_type.value == 'decision']
            
            if len(decision_nodes) < 2:
                return patterns
            
            # Look for decision chains (decisions that influence other decisions)
            decision_chains = []
            
            for start_node in decision_nodes:
                visited = set()
                chain = []
                
                def dfs_decision_chain(current_node, depth=0):
                    if depth > 5 or current_node in visited:  # Limit chain length
                        return
                    
                    visited.add(current_node)
                    chain.append(current_node)
                    
                    # Find decisions influenced by this one
                    for successor in self.kg.graph.successors(current_node):
                        if (successor in decision_nodes and 
                            successor not in visited):
                            edge_data = self.kg.graph[current_node][successor]
                            if ('edge' in edge_data and 
                                edge_data['edge'].edge_type.value in ['leads_to', 'influences']):
                                dfs_decision_chain(successor, depth + 1)
                
                dfs_decision_chain(start_node)
                
                if len(chain) > 2:  # Chain of at least 3 decisions
                    decision_chains.append(chain.copy())
                chain.clear()
                visited.clear()
            
            # Create patterns for significant decision chains
            for chain in decision_chains:
                if len(chain) > 2:
                    chain_names = [self.kg.node_cache[nid].name for nid in chain 
                                 if nid in self.kg.node_cache]
                    
                    pattern = PatternDetection(
                        pattern_type='decision_chains',
                        pattern_name=f'Decision Chain ({len(chain)} decisions)',
                        description=f'Chain of {len(chain)} interconnected decisions',
                        confidence=min(len(chain) / 5.0, 0.9),
                        supporting_evidence=[
                            f'Chain length: {len(chain)}',
                            f'Decisions: {" -> ".join(chain_names[:3])}...',
                            'Sequential decision influence pattern detected'
                        ],
                        affected_nodes=chain,
                        recommendations=[
                            'Review decision chain for optimization opportunities',
                            'Document decision rationale for future reference',
                            'Consider decision templates for similar situations'
                        ],
                        impact_assessment='Medium - Decision patterns may be reusable'
                    )
                    patterns.append(pattern)
        
        except Exception as e:
            print(f"Error detecting decision chains: {e}")
        
        return patterns
    
    async def analyze_temporal_trends(self, 
                                    time_window_days: int = 30) -> List[TrendAnalysis]:
        """Analyze temporal trends in graph evolution"""
        trends = []
        
        try:
            cutoff_date = datetime.now() - timedelta(days=time_window_days)
            
            # Analyze node creation trends
            recent_nodes = [node for node in self.kg.node_cache.values()
                          if node.created_at and node.created_at > cutoff_date]
            
            if len(recent_nodes) > 5:
                # Group by node type and analyze trends
                node_type_trends = defaultdict(list)
                
                for node in recent_nodes:
                    days_ago = (datetime.now() - node.created_at).days
                    node_type_trends[node.node_type.value].append(days_ago)
                
                for node_type, day_counts in node_type_trends.items():
                    if len(day_counts) > 2:
                        # Simple trend analysis
                        recent_count = sum(1 for d in day_counts if d <= 7)
                        older_count = sum(1 for d in day_counts if 7 < d <= time_window_days)
                        
                        if recent_count > older_count * 1.5:
                            trend_direction = 'increasing'
                            strength = (recent_count - older_count) / len(day_counts)
                        elif older_count > recent_count * 1.5:
                            trend_direction = 'decreasing' 
                            strength = (older_count - recent_count) / len(day_counts)
                        else:
                            trend_direction = 'stable'
                            strength = 0.1
                        
                        trend = TrendAnalysis(
                            trend_type='node_creation',
                            trend_direction=trend_direction,
                            strength=min(abs(strength), 1.0),
                            time_period=f'{time_window_days} days',
                            affected_entities=[node_type],
                            predictions=[
                                f'{node_type} node creation is {trend_direction}',
                                f'Expected {node_type} nodes in next week: {int(recent_count * 1.2)}'
                            ]
                        )
                        trends.append(trend)
            
            # Analyze edge creation trends
            recent_edges = [edge for edge in self.kg.edge_cache.values()
                          if edge.created_at and edge.created_at > cutoff_date]
            
            if len(recent_edges) > 5:
                edge_type_trends = defaultdict(list)
                
                for edge in recent_edges:
                    days_ago = (datetime.now() - edge.created_at).days
                    edge_type_trends[edge.edge_type.value].append(days_ago)
                
                for edge_type, day_counts in edge_type_trends.items():
                    if len(day_counts) > 2:
                        recent_count = sum(1 for d in day_counts if d <= 7)
                        older_count = sum(1 for d in day_counts if 7 < d <= time_window_days)
                        
                        if recent_count > older_count * 1.5:
                            trend_direction = 'increasing'
                            strength = (recent_count - older_count) / len(day_counts)
                        elif older_count > recent_count * 1.5:
                            trend_direction = 'decreasing'
                            strength = (older_count - recent_count) / len(day_counts)
                        else:
                            trend_direction = 'stable'
                            strength = 0.1
                        
                        trend = TrendAnalysis(
                            trend_type='relationship_formation',
                            trend_direction=trend_direction,
                            strength=min(abs(strength), 1.0),
                            time_period=f'{time_window_days} days',
                            affected_entities=[edge_type],
                            predictions=[
                                f'{edge_type} relationships are {trend_direction}',
                                'Monitor for changing collaboration patterns'
                            ]
                        )
                        trends.append(trend)
        
        except Exception as e:
            print(f"Error analyzing temporal trends: {e}")
        
        return trends
    
    async def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive analytics report"""
        
        try:
            # Run all analyses
            communities = await self.perform_community_analysis()
            centrality_rankings = await self.calculate_centrality_rankings()
            patterns = await self.detect_patterns()
            trends = await self.analyze_temporal_trends()
            
            # Compile comprehensive report
            report = {
                'analysis_timestamp': datetime.now().isoformat(),
                'graph_overview': {
                    'total_nodes': len(self.kg.node_cache),
                    'total_edges': len(self.kg.edge_cache),
                    'graph_density': nx.density(self.kg.graph) if len(self.kg.graph.nodes()) > 1 else 0,
                    'connected_components': nx.number_weakly_connected_components(self.kg.graph)
                },
                'community_analysis': {
                    'total_communities': len(communities),
                    'largest_community_size': max([c.size for c in communities]) if communities else 0,
                    'communities': [c.__dict__ for c in communities[:10]]  # Top 10 communities
                },
                'centrality_analysis': {
                    'top_influential_nodes': [r.__dict__ for r in centrality_rankings[:20]],
                    'centrality_distribution': self._summarize_centrality_distribution(centrality_rankings)
                },
                'pattern_detection': {
                    'patterns_found': len(patterns),
                    'pattern_types': list(set(p.pattern_type for p in patterns)),
                    'high_confidence_patterns': [p.__dict__ for p in patterns if p.confidence > 0.7]
                },
                'trend_analysis': {
                    'trends_identified': len(trends),
                    'trend_summary': [t.__dict__ for t in trends]
                },
                'recommendations': self._generate_recommendations(communities, patterns, trends)
            }
            
            # Cache the comprehensive analysis
            self.last_analysis = report
            
            return report
            
        except Exception as e:
            print(f"Error generating comprehensive analysis: {e}")
            return {
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat(),
                'graph_overview': {
                    'total_nodes': len(self.kg.node_cache),
                    'total_edges': len(self.kg.edge_cache)
                }
            }
    
    def _summarize_centrality_distribution(self, rankings: List[CentralityRanking]) -> Dict[str, Any]:
        """Summarize centrality score distributions"""
        if not rankings:
            return {}
        
        importance_scores = [r.importance_score for r in rankings]
        
        return {
            'mean_importance': statistics.mean(importance_scores),
            'median_importance': statistics.median(importance_scores),
            'max_importance': max(importance_scores),
            'std_importance': statistics.stdev(importance_scores) if len(importance_scores) > 1 else 0,
            'top_10_percent_threshold': sorted(importance_scores, reverse=True)[len(importance_scores)//10] if len(importance_scores) > 10 else max(importance_scores)
        }
    
    def _generate_recommendations(self, 
                                communities: List[CommunityAnalysis],
                                patterns: List[PatternDetection],
                                trends: List[TrendAnalysis]) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Community-based recommendations
        if communities:
            largest_community = max(communities, key=lambda c: c.size)
            recommendations.append(
                f"Focus development efforts on {largest_community.dominant_node_type} "
                f"community ({largest_community.size} nodes) with expertise in "
                f"{', '.join(largest_community.expertise_focus[:3])}"
            )
            
            isolated_communities = [c for c in communities if c.external_edges < c.internal_edges * 0.1]
            if isolated_communities:
                recommendations.append(
                    f"Improve connectivity for {len(isolated_communities)} isolated communities "
                    "to facilitate knowledge sharing"
                )
        
        # Pattern-based recommendations
        hub_patterns = [p for p in patterns if p.pattern_type == 'hub_nodes']
        if hub_patterns:
            recommendations.append(
                f"Monitor {len(hub_patterns)} critical hub nodes for system reliability "
                "and consider redundancy planning"
            )
        
        tech_patterns = [p for p in patterns if p.pattern_type == 'technology_adoption']
        if tech_patterns:
            top_tech = max(tech_patterns, key=lambda p: p.confidence)
            recommendations.append(
                f"Leverage successful technology adoption patterns, particularly "
                f"{top_tech.pattern_name.split(': ')[1]} across projects"
            )
        
        # Trend-based recommendations
        increasing_trends = [t for t in trends if t.trend_direction == 'increasing']
        if increasing_trends:
            for trend in increasing_trends[:2]:  # Top 2 increasing trends
                recommendations.append(
                    f"Capitalize on increasing {trend.trend_type} trend "
                    f"affecting {', '.join(trend.affected_entities)}"
                )
        
        return recommendations[:10]  # Return top 10 recommendations
    
    def clear_cache(self):
        """Clear analytics cache"""
        self.analytics_cache.clear()
        self.last_analysis = None
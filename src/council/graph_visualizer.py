"""
Graph Visualizer

Exports knowledge graph data for visualization with D3.js and other tools.
Provides multiple export formats, filtering options, and layout optimizations
for effective knowledge graph visualization.
"""

import json
import math
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum

import networkx as nx
try:
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class LayoutType(Enum):
    """Available layout algorithms for graph visualization"""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    SPRING = "spring"
    KAMADA_KAWAI = "kamada_kawai"
    SPECTRAL = "spectral"
    TSNE = "tsne"
    PCA = "pca"


class ColorScheme(Enum):
    """Color schemes for node and edge visualization"""
    TYPE_BASED = "type_based"
    IMPORTANCE_BASED = "importance_based"
    COMMUNITY_BASED = "community_based"
    CENTRALITY_BASED = "centrality_based"
    TEMPORAL_BASED = "temporal_based"


@dataclass
class VisualizationConfig:
    """Configuration for graph visualization"""
    layout: LayoutType = LayoutType.FORCE_DIRECTED
    color_scheme: ColorScheme = ColorScheme.TYPE_BASED
    node_size_metric: str = "importance"  # 'importance', 'degree', 'centrality'
    edge_width_metric: str = "weight"     # 'weight', 'confidence'
    show_labels: bool = True
    label_threshold: float = 0.7  # Only show labels for important nodes
    max_nodes: int = 500
    max_edges: int = 1000
    filter_node_types: Optional[List[str]] = None
    filter_edge_types: Optional[List[str]] = None
    min_importance: float = 0.0
    min_weight: float = 0.1
    enable_clustering: bool = True
    enable_physics: bool = True


@dataclass 
class VisualizationNode:
    """Node data structure for visualization"""
    id: str
    name: str
    type: str
    group: str  # For grouping/coloring
    size: float
    color: str
    importance: float
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    attributes: Dict[str, Any] = None
    label: Optional[str] = None
    title: Optional[str] = None  # Tooltip text


@dataclass
class VisualizationEdge:
    """Edge data structure for visualization"""
    id: str
    source: str
    target: str
    type: str
    weight: float
    width: float
    color: str
    confidence: float
    attributes: Dict[str, Any] = None
    title: Optional[str] = None  # Tooltip text


@dataclass
class VisualizationData:
    """Complete visualization dataset"""
    nodes: List[VisualizationNode]
    edges: List[VisualizationEdge]
    metadata: Dict[str, Any]
    statistics: Dict[str, Any]
    layout_info: Dict[str, Any]


class GraphVisualizer:
    """
    Advanced graph visualizer for the Optimus knowledge graph.
    
    Features:
    - Multiple layout algorithms for different visualization needs
    - Dynamic color schemes based on various node/edge properties
    - Filtering and sampling for large graphs
    - Export to D3.js, Cytoscape.js, and other formats
    - Interactive visualization configuration
    - Community highlighting and clustering
    """
    
    def __init__(self, knowledge_graph, analytics=None):
        self.kg = knowledge_graph
        self.analytics = analytics
        
        # Color palettes for different node types
        self.type_colors = {
            'project': '#3498db',      # Blue
            'technology': '#e74c3c',   # Red  
            'decision': '#f39c12',     # Orange
            'persona': '#9b59b6',      # Purple
            'concept': '#1abc9c',      # Teal
            'skill': '#2ecc71',        # Green
            'problem': '#e67e22',      # Dark Orange
            'solution': '#27ae60',     # Dark Green
            'pattern': '#8e44ad',      # Dark Purple
            'insight': '#16a085',      # Dark Teal
            'goal': '#f1c40f',         # Yellow
            'resource': '#95a5a6',     # Gray
            'tool': '#34495e',         # Dark Gray
            'default': '#7f8c8d'       # Medium Gray
        }
        
        # Edge type colors
        self.edge_colors = {
            'uses': '#3498db',
            'depends_on': '#e74c3c',
            'solved_by': '#27ae60',
            'influences': '#9b59b6',
            'relates_to': '#7f8c8d',
            'supports': '#2ecc71',
            'conflicts_with': '#e74c3c',
            'recommends': '#f39c12',
            'default': '#95a5a6'
        }
    
    async def generate_visualization(self, 
                                   config: VisualizationConfig) -> VisualizationData:
        """Generate complete visualization data based on configuration"""
        
        # Filter graph based on configuration
        filtered_nodes, filtered_edges = await self._filter_graph(config)
        
        if not filtered_nodes:
            return VisualizationData(
                nodes=[], edges=[], metadata={}, statistics={}, layout_info={}
            )
        
        # Create subgraph for layout calculation
        subgraph = self._create_subgraph(filtered_nodes, filtered_edges)
        
        # Calculate layout positions
        layout_positions = await self._calculate_layout(subgraph, config.layout)
        
        # Generate visualization nodes
        vis_nodes = await self._generate_vis_nodes(
            filtered_nodes, config, layout_positions
        )
        
        # Generate visualization edges  
        vis_edges = await self._generate_vis_edges(
            filtered_edges, config, filtered_nodes
        )
        
        # Calculate statistics
        statistics = await self._calculate_vis_statistics(vis_nodes, vis_edges)
        
        # Generate metadata
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'config': asdict(config),
            'node_count': len(vis_nodes),
            'edge_count': len(vis_edges),
            'layout_type': config.layout.value,
            'color_scheme': config.color_scheme.value
        }
        
        # Layout information
        layout_info = {
            'type': config.layout.value,
            'dimensions': '2D',
            'algorithm_params': layout_positions.get('params', {})
        }
        
        return VisualizationData(
            nodes=vis_nodes,
            edges=vis_edges,
            metadata=metadata,
            statistics=statistics,
            layout_info=layout_info
        )
    
    async def _filter_graph(self, config: VisualizationConfig) -> Tuple[List, List]:
        """Filter nodes and edges based on configuration"""
        
        # Filter nodes
        filtered_nodes = []
        node_ids_to_include = set()
        
        for node_id, node in self.kg.node_cache.items():
            # Apply filters
            if config.filter_node_types and node.node_type.value not in config.filter_node_types:
                continue
            
            if node.importance < config.min_importance:
                continue
            
            filtered_nodes.append(node)
            node_ids_to_include.add(node_id)
        
        # Sort by importance and limit
        filtered_nodes.sort(key=lambda n: n.importance, reverse=True)
        filtered_nodes = filtered_nodes[:config.max_nodes]
        node_ids_to_include = {str(n.id) for n in filtered_nodes}
        
        # Filter edges
        filtered_edges = []
        
        for edge_id, edge in self.kg.edge_cache.items():
            # Only include edges between filtered nodes
            if (str(edge.source_id) not in node_ids_to_include or 
                str(edge.target_id) not in node_ids_to_include):
                continue
            
            # Apply edge filters
            if config.filter_edge_types and edge.edge_type.value not in config.filter_edge_types:
                continue
            
            if edge.weight < config.min_weight:
                continue
            
            filtered_edges.append(edge)
        
        # Sort by weight and limit
        filtered_edges.sort(key=lambda e: e.weight, reverse=True)
        filtered_edges = filtered_edges[:config.max_edges]
        
        return filtered_nodes, filtered_edges
    
    def _create_subgraph(self, nodes: List, edges: List) -> nx.Graph:
        """Create NetworkX subgraph from filtered nodes and edges"""
        
        subgraph = nx.Graph()  # Undirected for layout algorithms
        
        # Add nodes
        for node in nodes:
            subgraph.add_node(str(node.id), node=node)
        
        # Add edges
        for edge in edges:
            source_id = str(edge.source_id)
            target_id = str(edge.target_id)
            
            if source_id in subgraph.nodes() and target_id in subgraph.nodes():
                subgraph.add_edge(source_id, target_id, weight=edge.weight, edge=edge)
        
        return subgraph
    
    async def _calculate_layout(self, 
                               subgraph: nx.Graph, 
                               layout_type: LayoutType) -> Dict[str, Any]:
        """Calculate node positions using specified layout algorithm"""
        
        if not subgraph.nodes():
            return {'positions': {}, 'params': {}}
        
        try:
            if layout_type == LayoutType.SPRING:
                positions = nx.spring_layout(
                    subgraph, 
                    k=2/math.sqrt(len(subgraph.nodes())),
                    iterations=50,
                    weight='weight'
                )
                params = {'algorithm': 'spring', 'k': 2/math.sqrt(len(subgraph.nodes()))}
                
            elif layout_type == LayoutType.FORCE_DIRECTED:
                positions = nx.spring_layout(
                    subgraph,
                    k=3/math.sqrt(len(subgraph.nodes())),
                    iterations=100,
                    weight='weight'
                )
                params = {'algorithm': 'force_directed', 'iterations': 100}
                
            elif layout_type == LayoutType.CIRCULAR:
                positions = nx.circular_layout(subgraph, scale=2)
                params = {'algorithm': 'circular'}
                
            elif layout_type == LayoutType.KAMADA_KAWAI:
                if len(subgraph.nodes()) < 500:  # KK is expensive for large graphs
                    positions = nx.kamada_kawai_layout(subgraph, weight='weight')
                    params = {'algorithm': 'kamada_kawai'}
                else:
                    # Fallback to spring layout
                    positions = nx.spring_layout(subgraph, iterations=50)
                    params = {'algorithm': 'spring_fallback', 'reason': 'too_many_nodes'}
                
            elif layout_type == LayoutType.SPECTRAL:
                try:
                    positions = nx.spectral_layout(subgraph, weight='weight')
                    params = {'algorithm': 'spectral'}
                except:
                    positions = nx.spring_layout(subgraph, iterations=30)
                    params = {'algorithm': 'spring_fallback', 'reason': 'spectral_failed'}
                    
            elif layout_type == LayoutType.HIERARCHICAL:
                positions = self._hierarchical_layout(subgraph)
                params = {'algorithm': 'hierarchical'}
                
            elif layout_type == LayoutType.TSNE:
                positions = await self._tsne_layout(subgraph)
                params = {'algorithm': 'tsne', 'perplexity': min(30, len(subgraph.nodes())//4)}
                
            elif layout_type == LayoutType.PCA:
                positions = await self._pca_layout(subgraph)
                params = {'algorithm': 'pca'}
                
            else:
                # Default to spring layout
                positions = nx.spring_layout(subgraph, iterations=50)
                params = {'algorithm': 'default_spring'}
            
            # Scale positions to reasonable range for visualization
            positions = self._scale_positions(positions)
            
            return {'positions': positions, 'params': params}
            
        except Exception as e:
            print(f"Error calculating layout: {e}")
            # Fallback to random layout
            positions = {node: (np.random.random(), np.random.random()) 
                        for node in subgraph.nodes()}
            return {'positions': positions, 'params': {'algorithm': 'random_fallback'}}
    
    def _hierarchical_layout(self, graph: nx.Graph) -> Dict[str, Tuple[float, float]]:
        """Create hierarchical layout based on node importance"""
        
        positions = {}
        
        # Get nodes sorted by importance
        nodes_with_importance = []
        for node_id in graph.nodes():
            node = graph.nodes[node_id].get('node')
            importance = node.importance if node else 0.5
            nodes_with_importance.append((node_id, importance))
        
        nodes_with_importance.sort(key=lambda x: x[1], reverse=True)
        
        # Create hierarchical levels
        num_levels = min(5, len(nodes_with_importance))
        level_size = len(nodes_with_importance) // num_levels
        
        for i, (node_id, importance) in enumerate(nodes_with_importance):
            level = i // level_size if level_size > 0 else 0
            level = min(level, num_levels - 1)
            
            # Position within level
            position_in_level = i % level_size if level_size > 0 else i
            level_width = min(level_size, len(nodes_with_importance) - level * level_size)
            
            # Calculate x position (spread across level)
            if level_width > 1:
                x = (position_in_level / (level_width - 1)) * 2 - 1  # Range [-1, 1]
            else:
                x = 0
            
            # Calculate y position (level height)
            y = 1 - (level / (num_levels - 1)) * 2  # Range [1, -1]
            
            positions[node_id] = (x, y)
        
        return positions
    
    async def _tsne_layout(self, graph: nx.Graph) -> Dict[str, Tuple[float, float]]:
        """Create t-SNE layout based on graph structure"""
        
        if not HAS_SKLEARN:
            print("scikit-learn not available, falling back to spring layout")
            return nx.spring_layout(graph)
        
        try:
            # Create adjacency matrix
            adjacency_matrix = nx.to_numpy_array(graph, weight='weight')
            
            if adjacency_matrix.shape[0] < 4:
                # Too few nodes for t-SNE, use spring layout
                return nx.spring_layout(graph)
            
            # Apply t-SNE
            perplexity = min(30, adjacency_matrix.shape[0] // 4)
            tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42)
            embedded_positions = tsne.fit_transform(adjacency_matrix)
            
            # Convert to position dictionary
            positions = {}
            nodes = list(graph.nodes())
            
            for i, node_id in enumerate(nodes):
                positions[node_id] = (
                    float(embedded_positions[i, 0]), 
                    float(embedded_positions[i, 1])
                )
            
            return positions
            
        except Exception as e:
            print(f"t-SNE layout failed: {e}, falling back to spring layout")
            return nx.spring_layout(graph)
    
    async def _pca_layout(self, graph: nx.Graph) -> Dict[str, Tuple[float, float]]:
        """Create PCA layout based on graph structure"""
        
        if not HAS_SKLEARN:
            print("scikit-learn not available, falling back to spring layout")
            return nx.spring_layout(graph)
        
        try:
            # Create feature matrix (adjacency + node features)
            adjacency_matrix = nx.to_numpy_array(graph, weight='weight')
            
            if adjacency_matrix.shape[0] < 2:
                return nx.spring_layout(graph)
            
            # Apply PCA
            pca = PCA(n_components=2, random_state=42)
            embedded_positions = pca.fit_transform(adjacency_matrix)
            
            # Convert to position dictionary
            positions = {}
            nodes = list(graph.nodes())
            
            for i, node_id in enumerate(nodes):
                positions[node_id] = (
                    float(embedded_positions[i, 0]),
                    float(embedded_positions[i, 1])
                )
            
            return positions
            
        except Exception as e:
            print(f"PCA layout failed: {e}, falling back to spring layout")
            return nx.spring_layout(graph)
    
    def _scale_positions(self, positions: Dict[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
        """Scale positions to standard range for consistent visualization"""
        
        if not positions:
            return positions
        
        # Extract x and y coordinates
        x_coords = [pos[0] for pos in positions.values()]
        y_coords = [pos[1] for pos in positions.values()]
        
        # Calculate ranges
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        x_range = x_max - x_min if x_max != x_min else 1
        y_range = y_max - y_min if y_max != y_min else 1
        
        # Scale to [-500, 500] range for reasonable visualization
        scale_factor = 500
        
        scaled_positions = {}
        for node_id, (x, y) in positions.items():
            scaled_x = ((x - x_min) / x_range - 0.5) * scale_factor * 2
            scaled_y = ((y - y_min) / y_range - 0.5) * scale_factor * 2
            scaled_positions[node_id] = (scaled_x, scaled_y)
        
        return scaled_positions
    
    async def _generate_vis_nodes(self, 
                                 nodes: List,
                                 config: VisualizationConfig,
                                 layout_positions: Dict[str, Any]) -> List[VisualizationNode]:
        """Generate visualization nodes with positions and styling"""
        
        vis_nodes = []
        positions = layout_positions.get('positions', {})
        
        # Get community assignments if clustering is enabled
        community_assignments = {}
        if config.enable_clustering and self.analytics:
            try:
                communities = await self.analytics.perform_community_analysis()
                for i, community in enumerate(communities):
                    for member in community.members:
                        community_assignments[member] = i
            except:
                pass
        
        for node in nodes:
            node_id = str(node.id)
            
            # Get position
            x, y = positions.get(node_id, (0, 0))
            
            # Calculate size based on metric
            size = self._calculate_node_size(node, config.node_size_metric)
            
            # Determine color and group
            color, group = self._calculate_node_color(node, config, community_assignments)
            
            # Determine label
            label = node.name if config.show_labels and node.importance >= config.label_threshold else ""
            
            # Create tooltip
            title = self._create_node_tooltip(node)
            
            vis_node = VisualizationNode(
                id=node_id,
                name=node.name,
                type=node.node_type.value,
                group=group,
                size=size,
                color=color,
                importance=node.importance,
                x=x,
                y=y,
                attributes=node.attributes,
                label=label,
                title=title
            )
            
            vis_nodes.append(vis_node)
        
        return vis_nodes
    
    async def _generate_vis_edges(self, 
                                 edges: List,
                                 config: VisualizationConfig,
                                 included_nodes: List) -> List[VisualizationEdge]:
        """Generate visualization edges with styling"""
        
        vis_edges = []
        included_node_ids = {str(node.id) for node in included_nodes}
        
        for edge in edges:
            source_id = str(edge.source_id)
            target_id = str(edge.target_id)
            
            # Only include edges between included nodes
            if source_id not in included_node_ids or target_id not in included_node_ids:
                continue
            
            # Calculate width based on metric
            width = self._calculate_edge_width(edge, config.edge_width_metric)
            
            # Determine color
            color = self._calculate_edge_color(edge)
            
            # Create tooltip
            title = self._create_edge_tooltip(edge)
            
            vis_edge = VisualizationEdge(
                id=str(edge.id),
                source=source_id,
                target=target_id,
                type=edge.edge_type.value,
                weight=edge.weight,
                width=width,
                color=color,
                confidence=edge.confidence,
                attributes=edge.attributes,
                title=title
            )
            
            vis_edges.append(vis_edge)
        
        return vis_edges
    
    def _calculate_node_size(self, node, size_metric: str) -> float:
        """Calculate node size based on specified metric"""
        
        if size_metric == "importance":
            # Scale importance (0-1) to size range (10-50)
            return 10 + node.importance * 40
        
        elif size_metric == "degree":
            # Use node degree from cached graph
            degree = len([e for e in self.kg.edge_cache.values() 
                         if str(e.source_id) == str(node.id) or str(e.target_id) == str(node.id)])
            # Scale degree to reasonable size range
            max_degree = max(10, degree * 2)  # Prevent division by zero
            return 10 + (degree / max_degree) * 40
        
        elif size_metric == "access_count":
            # Scale access count to size range
            max_access = max(1, node.access_count)
            normalized_access = min(node.access_count / max_access, 1.0)
            return 10 + normalized_access * 40
        
        else:
            return 20  # Default size
    
    def _calculate_node_color(self, 
                             node, 
                             config: VisualizationConfig,
                             community_assignments: Dict[str, int]) -> Tuple[str, str]:
        """Calculate node color and group based on color scheme"""
        
        node_id = str(node.id)
        
        if config.color_scheme == ColorScheme.TYPE_BASED:
            color = self.type_colors.get(node.node_type.value, self.type_colors['default'])
            group = node.node_type.value
            
        elif config.color_scheme == ColorScheme.IMPORTANCE_BASED:
            # Color based on importance (red = high, blue = low)
            importance = node.importance
            red = int(255 * importance)
            blue = int(255 * (1 - importance))
            color = f"rgb({red}, 100, {blue})"
            group = f"importance_{int(importance * 10)}"
            
        elif config.color_scheme == ColorScheme.COMMUNITY_BASED:
            community_id = community_assignments.get(node_id, 0)
            # Use predefined color palette for communities
            community_colors = [
                '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
                '#1abc9c', '#e67e22', '#27ae60', '#8e44ad', '#16a085'
            ]
            color = community_colors[community_id % len(community_colors)]
            group = f"community_{community_id}"
            
        elif config.color_scheme == ColorScheme.TEMPORAL_BASED:
            # Color based on creation time (newer = brighter)
            days_since_creation = (datetime.now() - node.created_at).days if node.created_at else 365
            age_factor = max(0, min(1, (365 - days_since_creation) / 365))
            intensity = int(100 + age_factor * 155)
            color = f"rgb({intensity}, {intensity}, {intensity})"
            group = f"age_{int(age_factor * 10)}"
            
        else:
            # Default to type-based coloring
            color = self.type_colors.get(node.node_type.value, self.type_colors['default'])
            group = node.node_type.value
        
        return color, group
    
    def _calculate_edge_width(self, edge, width_metric: str) -> float:
        """Calculate edge width based on specified metric"""
        
        if width_metric == "weight":
            # Scale weight to width range (1-10)
            return 1 + edge.weight * 9
        
        elif width_metric == "confidence":
            # Scale confidence to width range
            return 1 + edge.confidence * 9
        
        else:
            return 3  # Default width
    
    def _calculate_edge_color(self, edge) -> str:
        """Calculate edge color based on edge type"""
        return self.edge_colors.get(edge.edge_type.value, self.edge_colors['default'])
    
    def _create_node_tooltip(self, node) -> str:
        """Create HTML tooltip for node"""
        
        tooltip_parts = [
            f"<strong>{node.name}</strong>",
            f"Type: {node.node_type.value.title()}",
            f"Importance: {node.importance:.2f}",
            f"Access Count: {node.access_count}"
        ]
        
        if node.attributes:
            # Add key attributes
            for key, value in list(node.attributes.items())[:3]:
                if isinstance(value, (str, int, float)):
                    tooltip_parts.append(f"{key.title()}: {value}")
        
        return "<br>".join(tooltip_parts)
    
    def _create_edge_tooltip(self, edge) -> str:
        """Create HTML tooltip for edge"""
        
        tooltip_parts = [
            f"<strong>{edge.edge_type.value.replace('_', ' ').title()}</strong>",
            f"Weight: {edge.weight:.2f}",
            f"Confidence: {edge.confidence:.2f}"
        ]
        
        if edge.attributes:
            # Add key attributes
            for key, value in list(edge.attributes.items())[:2]:
                if isinstance(value, (str, int, float)):
                    tooltip_parts.append(f"{key.title()}: {value}")
        
        return "<br>".join(tooltip_parts)
    
    async def _calculate_vis_statistics(self, 
                                       nodes: List[VisualizationNode],
                                       edges: List[VisualizationEdge]) -> Dict[str, Any]:
        """Calculate visualization statistics"""
        
        if not nodes:
            return {}
        
        # Node statistics
        node_types = {}
        importance_scores = []
        sizes = []
        
        for node in nodes:
            node_types[node.type] = node_types.get(node.type, 0) + 1
            importance_scores.append(node.importance)
            sizes.append(node.size)
        
        # Edge statistics
        edge_types = {}
        weights = []
        
        for edge in edges:
            edge_types[edge.type] = edge_types.get(edge.type, 0) + 1
            weights.append(edge.weight)
        
        statistics = {
            'nodes': {
                'total': len(nodes),
                'types': node_types,
                'avg_importance': np.mean(importance_scores) if importance_scores else 0,
                'max_importance': max(importance_scores) if importance_scores else 0,
                'avg_size': np.mean(sizes) if sizes else 0
            },
            'edges': {
                'total': len(edges),
                'types': edge_types,
                'avg_weight': np.mean(weights) if weights else 0,
                'max_weight': max(weights) if weights else 0
            },
            'connectivity': {
                'density': len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0,
                'avg_degree': (2 * len(edges)) / len(nodes) if nodes else 0
            }
        }
        
        return statistics
    
    async def export_d3_json(self, 
                           config: VisualizationConfig,
                           filename: Optional[str] = None) -> Dict[str, Any]:
        """Export graph data in D3.js compatible JSON format"""
        
        vis_data = await self.generate_visualization(config)
        
        # Convert to D3.js format
        d3_data = {
            'nodes': [asdict(node) for node in vis_data.nodes],
            'links': [  # D3.js uses 'links' instead of 'edges'
                {
                    'id': edge.id,
                    'source': edge.source,
                    'target': edge.target,
                    'type': edge.type,
                    'weight': edge.weight,
                    'width': edge.width,
                    'color': edge.color,
                    'confidence': edge.confidence,
                    'title': edge.title
                }
                for edge in vis_data.edges
            ],
            'metadata': vis_data.metadata,
            'statistics': vis_data.statistics
        }
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(d3_data, f, indent=2, default=str)
        
        return d3_data
    
    async def export_cytoscape_json(self, 
                                  config: VisualizationConfig,
                                  filename: Optional[str] = None) -> Dict[str, Any]:
        """Export graph data in Cytoscape.js compatible JSON format"""
        
        vis_data = await self.generate_visualization(config)
        
        # Convert to Cytoscape.js format
        cytoscape_data = {
            'elements': {
                'nodes': [
                    {
                        'data': {
                            'id': node.id,
                            'name': node.name,
                            'type': node.type,
                            'group': node.group,
                            'importance': node.importance,
                            'attributes': node.attributes
                        },
                        'position': {'x': node.x or 0, 'y': node.y or 0},
                        'style': {
                            'background-color': node.color,
                            'width': node.size,
                            'height': node.size,
                            'label': node.label or node.name
                        }
                    }
                    for node in vis_data.nodes
                ],
                'edges': [
                    {
                        'data': {
                            'id': edge.id,
                            'source': edge.source,
                            'target': edge.target,
                            'type': edge.type,
                            'weight': edge.weight,
                            'confidence': edge.confidence,
                            'attributes': edge.attributes
                        },
                        'style': {
                            'line-color': edge.color,
                            'width': edge.width,
                            'target-arrow-color': edge.color,
                            'target-arrow-shape': 'triangle'
                        }
                    }
                    for edge in vis_data.edges
                ]
            },
            'metadata': vis_data.metadata,
            'statistics': vis_data.statistics
        }
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(cytoscape_data, f, indent=2, default=str)
        
        return cytoscape_data
    
    async def export_gexf(self, 
                         config: VisualizationConfig,
                         filename: str) -> str:
        """Export graph data in GEXF format for Gephi"""
        
        vis_data = await self.generate_visualization(config)
        
        # Create GEXF XML content
        gexf_content = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<gexf xmlns="http://www.gexf.net/1.3" version="1.3">',
            '<meta lastmodifieddate="' + datetime.now().isoformat() + '">',
            '<creator>Optimus Knowledge Graph</creator>',
            '</meta>',
            '<graph mode="static" defaultedgetype="directed">',
            
            # Node attributes
            '<attributes class="node">',
            '<attribute id="0" title="type" type="string"/>',
            '<attribute id="1" title="importance" type="double"/>',
            '<attribute id="2" title="group" type="string"/>',
            '</attributes>',
            
            # Edge attributes  
            '<attributes class="edge">',
            '<attribute id="0" title="type" type="string"/>',
            '<attribute id="1" title="weight" type="double"/>',
            '<attribute id="2" title="confidence" type="double"/>',
            '</attributes>',
            
            # Nodes
            '<nodes>'
        ]
        
        for node in vis_data.nodes:
            gexf_content.extend([
                f'<node id="{node.id}" label="{node.name}">',
                '<attvalues>',
                f'<attvalue for="0" value="{node.type}"/>',
                f'<attvalue for="1" value="{node.importance}"/>',
                f'<attvalue for="2" value="{node.group}"/>',
                '</attvalues>',
                f'<viz:color r="{int(node.color[1:3], 16)}" g="{int(node.color[3:5], 16)}" b="{int(node.color[5:7], 16)}"/>',
                f'<viz:size value="{node.size}"/>',
                f'<viz:position x="{node.x or 0}" y="{node.y or 0}" z="0"/>',
                '</node>'
            ])
        
        gexf_content.extend([
            '</nodes>',
            
            # Edges
            '<edges>'
        ])
        
        for edge in vis_data.edges:
            gexf_content.extend([
                f'<edge id="{edge.id}" source="{edge.source}" target="{edge.target}">',
                '<attvalues>',
                f'<attvalue for="0" value="{edge.type}"/>',
                f'<attvalue for="1" value="{edge.weight}"/>',
                f'<attvalue for="2" value="{edge.confidence}"/>',
                '</attvalues>',
                f'<viz:thickness value="{edge.width}"/>',
                '</edge>'
            ])
        
        gexf_content.extend([
            '</edges>',
            '</graph>',
            '</gexf>'
        ])
        
        gexf_xml = '\n'.join(gexf_content)
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(gexf_xml)
        
        return gexf_xml
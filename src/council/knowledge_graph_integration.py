"""
Knowledge Graph Integration

Integration layer that provides backward compatibility for the knowledge graph
while using the optimized implementation underneath.
"""

from .knowledge_graph import KnowledgeGraph as OriginalKnowledgeGraph, Node as OriginalNode, Edge as OriginalEdge
from .knowledge_graph import NodeType, EdgeType  # Import existing enums for compatibility
from ..database.knowledge_graph_optimized import (
    OptimizedKnowledgeGraph, 
    Node as OptimizedNode, 
    Edge as OptimizedEdge
)
from ..database.config import get_database_manager
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import networkx as nx
import asyncio


class KnowledgeGraphAdapter:
    """
    Adapter class that provides backward compatibility for the existing
    KnowledgeGraph interface while using the optimized implementation.
    """
    
    def __init__(self, db_path: str = "optimus_knowledge.db"):
        """Initialize with backward compatibility"""
        self.db_path = db_path
        self.db_manager = get_database_manager()
        self.optimized_graph = OptimizedKnowledgeGraph(self.db_manager)
        
        # Maintain compatibility with existing interface
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, OriginalNode] = {}
        self.edges: Dict[str, OriginalEdge] = {}
        
        # Initialize in async context if needed
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the system is initialized"""
        if not self._initialized:
            await self.db_manager.initialize()
            self._initialized = True
    
    def _convert_to_original_node(self, optimized_node: OptimizedNode) -> OriginalNode:
        """Convert optimized node to original format"""
        return OriginalNode(
            id=optimized_node.id,
            name=optimized_node.name,
            node_type=optimized_node.node_type,
            attributes=optimized_node.attributes,
            created_at=optimized_node.created_at,
            updated_at=optimized_node.updated_at,
            importance=optimized_node.importance,
            activation_level=optimized_node.activation_level,
            personas_relevance=optimized_node.personas_relevance
        )
    
    def _convert_to_original_edge(self, optimized_edge: OptimizedEdge) -> OriginalEdge:
        """Convert optimized edge to original format"""
        return OriginalEdge(
            id=optimized_edge.id,
            source_id=optimized_edge.source_id,
            target_id=optimized_edge.target_id,
            edge_type=optimized_edge.edge_type,
            weight=optimized_edge.weight,
            attributes=optimized_edge.attributes,
            created_at=optimized_edge.created_at,
            confidence=optimized_edge.confidence
        )
    
    async def add_node(self,
                      name: str,
                      node_type: NodeType,
                      attributes: Optional[Dict[str, Any]] = None,
                      importance: float = 0.5) -> OriginalNode:
        """Add node using optimized system"""
        await self._ensure_initialized()
        
        optimized_node = await self.optimized_graph.add_node(
            name=name,
            node_type=node_type,
            attributes=attributes,
            importance=importance
        )
        
        # Convert to original format
        node = self._convert_to_original_node(optimized_node)
        
        # Update compatibility structures
        self.nodes[node.id] = node
        self.graph.add_node(node.id, node=node)
        
        return node
    
    async def add_edge(self,
                      source_id: str,
                      target_id: str,
                      edge_type: EdgeType,
                      weight: float = 1.0,
                      confidence: float = 0.5,
                      attributes: Optional[Dict[str, Any]] = None) -> OriginalEdge:
        """Add edge using optimized system"""
        await self._ensure_initialized()
        
        optimized_edge = await self.optimized_graph.add_edge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            confidence=confidence,
            attributes=attributes
        )
        
        # Convert to original format
        edge = self._convert_to_original_edge(optimized_edge)
        
        # Update compatibility structures
        self.edges[edge.id] = edge
        self.graph.add_edge(source_id, target_id, edge_id=edge.id, edge=edge, weight=weight)
        
        return edge
    
    async def find_related(self,
                          node_id: str,
                          max_depth: int = 2,
                          edge_types: Optional[List[EdgeType]] = None) -> Dict[str, Any]:
        """Find related nodes using optimized system"""
        await self._ensure_initialized()
        
        related_data = await self.optimized_graph.find_related_optimized(
            node_id=node_id,
            max_depth=max_depth,
            edge_types=edge_types
        )
        
        # Convert to original format
        related_nodes = [
            self._convert_to_original_node(node) 
            for node in related_data.get('nodes', [])
        ]
        related_edges = [
            self._convert_to_original_edge(edge) 
            for edge in related_data.get('edges', [])
        ]
        
        # Update compatibility structures
        for node in related_nodes:
            self.nodes[node.id] = node
            self.graph.add_node(node.id, node=node)
        
        for edge in related_edges:
            self.edges[edge.id] = edge
            if edge.source_id in self.nodes and edge.target_id in self.nodes:
                self.graph.add_edge(
                    edge.source_id, edge.target_id, 
                    edge_id=edge.id, edge=edge, weight=edge.weight
                )
        
        return {
            'nodes': related_nodes,
            'edges': related_edges
        }
    
    async def find_path(self,
                       source_id: str,
                       target_id: str,
                       edge_types: Optional[List[EdgeType]] = None) -> List[OriginalNode]:
        """Find path using optimized system"""
        await self._ensure_initialized()
        
        # Use the optimized graph's NetworkX graph for path finding
        try:
            # Get subgraph if edge types are specified
            if edge_types:
                subgraph = await self.optimized_graph.get_subgraph_optimized(
                    edge_types=edge_types
                )
            else:
                subgraph = self.optimized_graph.graph
            
            # Find shortest path
            path_ids = nx.shortest_path(subgraph, source_id, target_id)
            
            # Convert to original nodes
            path = []
            for node_id in path_ids:
                if node_id in self.optimized_graph.nodes:
                    optimized_node = self.optimized_graph.nodes[node_id]
                    original_node = self._convert_to_original_node(optimized_node)
                    path.append(original_node)
                    
                    # Update compatibility structure
                    self.nodes[node_id] = original_node
                    self.graph.add_node(node_id, node=original_node)
            
            return path
            
        except nx.NetworkXNoPath:
            return []
    
    async def spreading_activation(self,
                                 seed_nodes: List[str],
                                 iterations: int = 3,
                                 decay: float = 0.5) -> Dict[str, float]:
        """Spreading activation using optimized system"""
        await self._ensure_initialized()
        
        return await self.optimized_graph.spreading_activation_optimized(
            seed_nodes=seed_nodes,
            iterations=iterations,
            decay=decay
        )
    
    async def calculate_centrality(self, centrality_type: str = 'betweenness') -> Dict[str, float]:
        """Calculate centrality using optimized system"""
        await self._ensure_initialized()
        
        return await self.optimized_graph.calculate_centrality_optimized(centrality_type)
    
    async def get_subgraph(self,
                          node_types: Optional[List[NodeType]] = None,
                          edge_types: Optional[List[EdgeType]] = None,
                          min_importance: float = 0.0) -> nx.DiGraph:
        """Get subgraph using optimized system"""
        await self._ensure_initialized()
        
        return await self.optimized_graph.get_subgraph_optimized(
            node_types=node_types,
            edge_types=edge_types,
            min_importance=min_importance
        )
    
    async def find_communities(self) -> List[Set[str]]:
        """Find communities using optimized system"""
        await self._ensure_initialized()
        
        # Use NetworkX on the optimized graph
        import networkx.algorithms.community as nx_comm
        undirected = self.optimized_graph.graph.to_undirected()
        communities = nx_comm.greedy_modularity_communities(undirected)
        
        return [set(community) for community in communities]
    
    async def infer_relationships(self):
        """Infer relationships using optimized system"""
        await self._ensure_initialized()
        
        # For now, return empty list - this can be enhanced with ML-based inference
        return []
    
    def visualize(self, output_file: str = "knowledge_graph.png"):
        """Create visualization using optimized system"""
        # Use the optimized graph's visualization if available
        if hasattr(self.optimized_graph, 'visualize'):
            self.optimized_graph.visualize(output_file)
        else:
            # Fallback to basic NetworkX visualization
            import matplotlib.pyplot as plt
            
            pos = nx.spring_layout(self.graph, k=2, iterations=50)
            
            plt.figure(figsize=(15, 10))
            nx.draw(self.graph, pos, 
                   with_labels=True,
                   labels={n: self.nodes[n].name[:20] if n in self.nodes else n 
                          for n in self.graph.nodes()},
                   node_size=1000,
                   font_size=8,
                   font_weight='bold',
                   arrows=True,
                   edge_color='gray',
                   alpha=0.7)
            
            plt.title("Optimus Knowledge Graph")
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()


# Create a global instance that can be used as a drop-in replacement
_global_knowledge_graph = None


def get_optimized_knowledge_graph() -> KnowledgeGraphAdapter:
    """Get the global optimized knowledge graph instance"""
    global _global_knowledge_graph
    if _global_knowledge_graph is None:
        _global_knowledge_graph = KnowledgeGraphAdapter()
    return _global_knowledge_graph


# Backward compatibility: provide the same interface as the original
class KnowledgeGraph(KnowledgeGraphAdapter):
    """
    Drop-in replacement for the original KnowledgeGraph class.
    Uses the optimized implementation while maintaining full compatibility.
    """
    pass
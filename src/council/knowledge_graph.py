"""
Knowledge Graph System

A graph-based knowledge representation system that models relationships
between concepts, entities, and experiences using nodes and edges.
"""

import json
import sqlite3
import networkx as nx
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from collections import defaultdict
import hashlib


class NodeType(Enum):
    """Types of nodes in the knowledge graph"""
    CONCEPT = "concept"          # Abstract concepts
    PERSON = "person"            # People and relationships
    PROJECT = "project"          # Projects and work
    SKILL = "skill"              # Skills and capabilities
    GOAL = "goal"                # Goals and objectives
    EXPERIENCE = "experience"    # Life experiences
    EMOTION = "emotion"          # Emotional states
    VALUE = "value"              # Personal values
    RESOURCE = "resource"        # Resources (time, money, etc.)
    LOCATION = "location"        # Places and spaces
    ACTIVITY = "activity"        # Activities and hobbies
    HEALTH = "health"           # Health-related nodes
    LEARNING = "learning"       # Knowledge and education
    DECISION = "decision"       # Past decisions made


class EdgeType(Enum):
    """Types of relationships between nodes"""
    RELATES_TO = "relates_to"           # General relationship
    CAUSES = "causes"                   # Causal relationship
    REQUIRES = "requires"               # Dependency
    CONFLICTS_WITH = "conflicts_with"   # Conflict or opposition
    SUPPORTS = "supports"               # Supportive relationship
    PART_OF = "part_of"                # Hierarchical relationship
    LEADS_TO = "leads_to"              # Sequential relationship
    SIMILAR_TO = "similar_to"          # Similarity
    OPPOSITE_OF = "opposite_of"        # Opposition
    INFLUENCES = "influences"          # Influence relationship
    BELONGS_TO = "belongs_to"          # Ownership/membership
    LOCATED_AT = "located_at"          # Spatial relationship
    OCCURS_DURING = "occurs_during"    # Temporal relationship
    LEARNED_FROM = "learned_from"      # Learning relationship
    EMOTIONAL_LINK = "emotional_link"  # Emotional connection


@dataclass
class Node:
    """A node in the knowledge graph"""
    id: str
    name: str
    node_type: NodeType
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    importance: float = 0.5  # 0.0 to 1.0
    activation_level: float = 0.0  # Current activation in spreading activation
    personas_relevance: Dict[str, float] = field(default_factory=dict)  # Relevance to each persona
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'node_type': self.node_type.value,
            'attributes': self.attributes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'importance': self.importance,
            'activation_level': self.activation_level,
            'personas_relevance': self.personas_relevance
        }


@dataclass
class Edge:
    """An edge in the knowledge graph"""
    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0  # Strength of relationship
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    confidence: float = 0.5  # Confidence in this relationship
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'edge_type': self.edge_type.value,
            'weight': self.weight,
            'attributes': self.attributes,
            'created_at': self.created_at.isoformat(),
            'confidence': self.confidence
        }


class KnowledgeGraph:
    """
    Graph-based knowledge representation system for understanding
    relationships between all aspects of life and work.
    """
    
    def __init__(self, db_path: str = "optimus_knowledge.db"):
        self.db_path = db_path
        self.graph = nx.DiGraph()  # Directed graph
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self._init_database()
        self._load_graph()
    
    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Nodes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                node_type TEXT NOT NULL,
                attributes TEXT,
                created_at TEXT,
                updated_at TEXT,
                importance REAL,
                personas_relevance TEXT
            )
        ''')
        
        # Edges table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL,
                attributes TEXT,
                created_at TEXT,
                confidence REAL,
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            )
        ''')
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_node_type ON nodes(node_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edge_source ON edges(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edge_target ON edges(target_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edge_type ON edges(edge_type)')
        
        conn.commit()
        conn.close()
    
    def _load_graph(self):
        """Load graph from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load nodes
        cursor.execute('SELECT * FROM nodes')
        for row in cursor.fetchall():
            node = Node(
                id=row[0],
                name=row[1],
                node_type=NodeType(row[2]),
                attributes=json.loads(row[3]) if row[3] else {},
                created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                updated_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                importance=row[6] if row[6] else 0.5,
                personas_relevance=json.loads(row[7]) if row[7] else {}
            )
            self.nodes[node.id] = node
            self.graph.add_node(node.id, node=node)
        
        # Load edges
        cursor.execute('SELECT * FROM edges')
        for row in cursor.fetchall():
            edge = Edge(
                id=row[0],
                source_id=row[1],
                target_id=row[2],
                edge_type=EdgeType(row[3]),
                weight=row[4] if row[4] else 1.0,
                attributes=json.loads(row[5]) if row[5] else {},
                created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                confidence=row[7] if row[7] else 0.5
            )
            self.edges[edge.id] = edge
            self.graph.add_edge(edge.source_id, edge.target_id, 
                              edge_id=edge.id, edge=edge, weight=edge.weight)
        
        conn.close()
    
    async def add_node(self,
                      name: str,
                      node_type: NodeType,
                      attributes: Optional[Dict[str, Any]] = None,
                      importance: float = 0.5) -> Node:
        """Add a node to the knowledge graph"""
        
        # Generate node ID
        node_id = hashlib.md5(f"{name}{node_type.value}".encode()).hexdigest()[:16]
        
        # Check if node already exists
        if node_id in self.nodes:
            return self.nodes[node_id]
        
        # Create node
        node = Node(
            id=node_id,
            name=name,
            node_type=node_type,
            attributes=attributes or {},
            importance=importance
        )
        
        # Add to graph
        self.nodes[node_id] = node
        self.graph.add_node(node_id, node=node)
        
        # Persist to database
        await self._persist_node(node)
        
        return node
    
    async def add_edge(self,
                      source_id: str,
                      target_id: str,
                      edge_type: EdgeType,
                      weight: float = 1.0,
                      confidence: float = 0.5,
                      attributes: Optional[Dict[str, Any]] = None) -> Edge:
        """Add an edge between two nodes"""
        
        # Verify nodes exist
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError(f"Both nodes must exist before creating edge")
        
        # Generate edge ID
        edge_id = hashlib.md5(
            f"{source_id}{target_id}{edge_type.value}".encode()
        ).hexdigest()[:16]
        
        # Check if edge already exists
        if edge_id in self.edges:
            # Update weight and confidence
            existing_edge = self.edges[edge_id]
            existing_edge.weight = (existing_edge.weight + weight) / 2
            existing_edge.confidence = max(existing_edge.confidence, confidence)
            await self._persist_edge(existing_edge)
            return existing_edge
        
        # Create edge
        edge = Edge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            confidence=confidence,
            attributes=attributes or {}
        )
        
        # Add to graph
        self.edges[edge_id] = edge
        self.graph.add_edge(source_id, target_id, 
                           edge_id=edge_id, edge=edge, weight=weight)
        
        # Persist to database
        await self._persist_edge(edge)
        
        return edge
    
    async def find_related(self,
                          node_id: str,
                          max_depth: int = 2,
                          edge_types: Optional[List[EdgeType]] = None) -> Dict[str, Any]:
        """Find all nodes related to a given node within max_depth"""
        
        if node_id not in self.nodes:
            return {}
        
        related = {'nodes': [], 'edges': []}
        visited = set()
        
        # BFS to find related nodes
        queue = [(node_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            related['nodes'].append(self.nodes[current_id])
            
            # Get neighbors
            for neighbor_id in self.graph.neighbors(current_id):
                edge_data = self.graph[current_id][neighbor_id]
                edge = edge_data['edge']
                
                # Filter by edge type if specified
                if edge_types and edge.edge_type not in edge_types:
                    continue
                
                related['edges'].append(edge)
                
                if neighbor_id not in visited:
                    queue.append((neighbor_id, depth + 1))
        
        return related
    
    async def find_path(self,
                       source_id: str,
                       target_id: str,
                       edge_types: Optional[List[EdgeType]] = None) -> List[Node]:
        """Find shortest path between two nodes"""
        
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
        
        try:
            # Find shortest path
            path_ids = nx.shortest_path(self.graph, source_id, target_id)
            
            # Convert to nodes
            path = [self.nodes[node_id] for node_id in path_ids]
            
            return path
        except nx.NetworkXNoPath:
            return []
    
    async def spreading_activation(self,
                                 seed_nodes: List[str],
                                 iterations: int = 3,
                                 decay: float = 0.5) -> Dict[str, float]:
        """
        Simulate spreading activation from seed nodes.
        This helps find conceptually related nodes.
        """
        
        # Initialize activation levels
        for node_id in self.nodes:
            self.nodes[node_id].activation_level = 0.0
        
        # Set initial activation for seed nodes
        for node_id in seed_nodes:
            if node_id in self.nodes:
                self.nodes[node_id].activation_level = 1.0
        
        # Spread activation
        for _ in range(iterations):
            new_activations = {}
            
            for node_id, node in self.nodes.items():
                if node.activation_level > 0:
                    # Spread to neighbors
                    for neighbor_id in self.graph.neighbors(node_id):
                        edge_data = self.graph[node_id][neighbor_id]
                        edge = edge_data['edge']
                        
                        # Calculate spread amount
                        spread = node.activation_level * edge.weight * decay
                        
                        if neighbor_id not in new_activations:
                            new_activations[neighbor_id] = 0
                        
                        new_activations[neighbor_id] += spread
            
            # Apply new activations
            for node_id, activation in new_activations.items():
                self.nodes[node_id].activation_level = min(1.0, activation)
        
        # Return activated nodes sorted by activation level
        activated = {
            node_id: node.activation_level 
            for node_id, node in self.nodes.items()
            if node.activation_level > 0.1
        }
        
        return dict(sorted(activated.items(), key=lambda x: x[1], reverse=True))
    
    async def infer_relationships(self):
        """
        Infer new relationships based on existing graph structure.
        Uses transitivity and pattern matching.
        """
        
        new_edges = []
        
        # Transitive relationships
        for node_id in self.nodes:
            neighbors = list(self.graph.neighbors(node_id))
            
            for n1 in neighbors:
                for n2 in neighbors:
                    if n1 != n2 and not self.graph.has_edge(n1, n2):
                        # Check if they should be related
                        edge1 = self.graph[node_id][n1]['edge']
                        edge2 = self.graph[node_id][n2]['edge']
                        
                        # If both have same relationship type to common node
                        if edge1.edge_type == edge2.edge_type:
                            # They might be similar
                            new_edge = await self.add_edge(
                                n1, n2,
                                EdgeType.SIMILAR_TO,
                                weight=0.5,
                                confidence=0.3,
                                attributes={'inferred': True, 'basis': node_id}
                            )
                            new_edges.append(new_edge)
        
        return new_edges
    
    async def get_subgraph(self,
                          node_types: Optional[List[NodeType]] = None,
                          edge_types: Optional[List[EdgeType]] = None,
                          min_importance: float = 0.0) -> nx.DiGraph:
        """Get a subgraph filtered by node/edge types and importance"""
        
        # Filter nodes
        filtered_nodes = []
        for node_id, node in self.nodes.items():
            if node_types and node.node_type not in node_types:
                continue
            if node.importance < min_importance:
                continue
            filtered_nodes.append(node_id)
        
        # Create subgraph
        subgraph = self.graph.subgraph(filtered_nodes).copy()
        
        # Filter edges if specified
        if edge_types:
            edges_to_remove = []
            for u, v, data in subgraph.edges(data=True):
                if data['edge'].edge_type not in edge_types:
                    edges_to_remove.append((u, v))
            subgraph.remove_edges_from(edges_to_remove)
        
        return subgraph
    
    async def calculate_centrality(self,
                                 centrality_type: str = 'betweenness') -> Dict[str, float]:
        """Calculate node centrality to find important nodes"""
        
        if centrality_type == 'betweenness':
            centrality = nx.betweenness_centrality(self.graph)
        elif centrality_type == 'closeness':
            centrality = nx.closeness_centrality(self.graph)
        elif centrality_type == 'degree':
            centrality = nx.degree_centrality(self.graph)
        elif centrality_type == 'eigenvector':
            try:
                centrality = nx.eigenvector_centrality(self.graph, max_iter=100)
            except:
                centrality = nx.degree_centrality(self.graph)
        else:
            centrality = nx.degree_centrality(self.graph)
        
        # Update node importance based on centrality
        for node_id, score in centrality.items():
            if node_id in self.nodes:
                # Blend with existing importance
                self.nodes[node_id].importance = (
                    self.nodes[node_id].importance * 0.7 + score * 0.3
                )
        
        return centrality
    
    async def find_communities(self) -> List[Set[str]]:
        """Find communities/clusters in the graph"""
        
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()
        
        # Find communities
        import networkx.algorithms.community as nx_comm
        communities = nx_comm.greedy_modularity_communities(undirected)
        
        return [set(community) for community in communities]
    
    async def _persist_node(self, node: Node):
        """Save node to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO nodes
            (id, name, node_type, attributes, created_at, updated_at, importance, personas_relevance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            node.id,
            node.name,
            node.node_type.value,
            json.dumps(node.attributes),
            node.created_at.isoformat(),
            node.updated_at.isoformat(),
            node.importance,
            json.dumps(node.personas_relevance)
        ))
        
        conn.commit()
        conn.close()
    
    async def _persist_edge(self, edge: Edge):
        """Save edge to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO edges
            (id, source_id, target_id, edge_type, weight, attributes, created_at, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            edge.id,
            edge.source_id,
            edge.target_id,
            edge.edge_type.value,
            edge.weight,
            json.dumps(edge.attributes),
            edge.created_at.isoformat(),
            edge.confidence
        ))
        
        conn.commit()
        conn.close()
    
    def visualize(self, output_file: str = "knowledge_graph.png"):
        """Create a visual representation of the graph"""
        import matplotlib.pyplot as plt
        
        # Create layout
        pos = nx.spring_layout(self.graph, k=2, iterations=50)
        
        # Color nodes by type
        node_colors = {
            NodeType.CONCEPT: 'lightblue',
            NodeType.PERSON: 'lightgreen',
            NodeType.PROJECT: 'yellow',
            NodeType.SKILL: 'orange',
            NodeType.GOAL: 'red',
            NodeType.EXPERIENCE: 'purple',
            NodeType.EMOTION: 'pink',
            NodeType.VALUE: 'gold',
            NodeType.RESOURCE: 'brown',
            NodeType.LOCATION: 'gray',
            NodeType.ACTIVITY: 'cyan',
            NodeType.HEALTH: 'lime',
            NodeType.LEARNING: 'navy',
            NodeType.DECISION: 'maroon'
        }
        
        colors = [node_colors.get(self.nodes[n].node_type, 'white') 
                 for n in self.graph.nodes()]
        
        # Draw
        plt.figure(figsize=(15, 10))
        nx.draw(self.graph, pos, 
               node_color=colors,
               with_labels=True,
               labels={n: self.nodes[n].name[:20] for n in self.graph.nodes()},
               node_size=1000,
               font_size=8,
               font_weight='bold',
               arrows=True,
               edge_color='gray',
               alpha=0.7)
        
        plt.title("Optimus Knowledge Graph")
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
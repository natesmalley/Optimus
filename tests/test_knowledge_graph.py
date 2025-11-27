"""
Comprehensive Test Suite for Optimus Knowledge Graph System

Tests all components of the knowledge graph implementation including:
- Core graph operations
- PostgreSQL model persistence
- Analytics and pattern detection
- Visualization export
- Memory system integration
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Knowledge graph components
try:
    from src.council.optimus_knowledge_graph import OptimusKnowledgeGraph
    from src.council.graph_analytics import GraphAnalytics
    from src.council.graph_visualizer import GraphVisualizer, VisualizationConfig, LayoutType, ColorScheme
    from src.council.knowledge_memory_integration import KnowledgeMemoryIntegrator
except ImportError as e:
    pytest.skip(f"Knowledge graph dependencies not available: {e}", allow_module_level=True)

# Models
from src.models.knowledge_graph import (
    GraphNode, GraphEdge, NodeTypeEnum, EdgeTypeEnum
)

# Test utilities
from src.database.config import get_database_manager


@pytest.fixture
async def knowledge_graph():
    """Create a test knowledge graph instance"""
    db_manager = get_database_manager()
    kg = OptimusKnowledgeGraph(db_manager)
    await kg.initialize()
    return kg


@pytest.fixture
async def analytics(knowledge_graph):
    """Create analytics instance with test data"""
    analytics = GraphAnalytics(knowledge_graph)
    
    # Add test data for analytics
    await knowledge_graph.add_project_node(
        "test-project-1",
        "/path/to/project1",
        ["python", "fastapi", "postgresql"],
        "active"
    )
    
    await knowledge_graph.add_project_node(
        "test-project-2", 
        "/path/to/project2",
        ["python", "react", "postgresql"],
        "active"
    )
    
    return analytics


@pytest.fixture
async def visualizer(knowledge_graph, analytics):
    """Create visualizer instance with test data"""
    return GraphVisualizer(knowledge_graph, analytics)


@pytest.fixture
async def integrator():
    """Create integration layer instance"""
    integrator = KnowledgeMemoryIntegrator()
    await integrator.initialize()
    return integrator


class TestKnowledgeGraphCore:
    """Test core knowledge graph functionality"""
    
    async def test_node_creation(self, knowledge_graph):
        """Test creating nodes with various types"""
        
        # Create a project node
        project_node = await knowledge_graph.add_node(
            name="Test Project",
            node_type=NodeTypeEnum.PROJECT,
            attributes={"path": "/test", "status": "active"},
            importance=0.8
        )
        
        assert project_node.name == "Test Project"
        assert project_node.node_type == NodeTypeEnum.PROJECT
        assert project_node.importance == 0.8
        assert project_node.attributes["path"] == "/test"
        
        # Create a technology node
        tech_node = await knowledge_graph.add_node(
            name="Python",
            node_type=NodeTypeEnum.TECHNOLOGY,
            importance=0.9
        )
        
        assert tech_node.name == "Python"
        assert tech_node.node_type == NodeTypeEnum.TECHNOLOGY
        assert tech_node.importance == 0.9
    
    async def test_duplicate_node_handling(self, knowledge_graph):
        """Test that duplicate nodes are properly handled"""
        
        # Create first node
        node1 = await knowledge_graph.add_node(
            name="Duplicate Test",
            node_type=NodeTypeEnum.CONCEPT,
            importance=0.5
        )
        
        # Create second node with same name and type
        node2 = await knowledge_graph.add_node(
            name="Duplicate Test",
            node_type=NodeTypeEnum.CONCEPT,
            importance=0.7
        )
        
        # Should return the same node with updated importance
        assert node1.id == node2.id
        assert node2.importance >= node1.importance  # Should use higher importance
        assert node2.access_count > node1.access_count  # Should increment access
    
    async def test_edge_creation(self, knowledge_graph):
        """Test creating edges between nodes"""
        
        # Create source and target nodes
        source = await knowledge_graph.add_node(
            name="Source Node",
            node_type=NodeTypeEnum.PROJECT
        )
        
        target = await knowledge_graph.add_node(
            name="Target Node", 
            node_type=NodeTypeEnum.TECHNOLOGY
        )
        
        # Create edge
        edge = await knowledge_graph.add_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type=EdgeTypeEnum.USES,
            weight=0.8,
            confidence=0.9
        )
        
        assert edge.source_id == source.id
        assert edge.target_id == target.id
        assert edge.edge_type == EdgeTypeEnum.USES
        assert edge.weight == 0.8
        assert edge.confidence == 0.9
    
    async def test_edge_reinforcement(self, knowledge_graph):
        """Test edge reinforcement when adding duplicate edges"""
        
        # Create nodes
        source = await knowledge_graph.add_node("Source", NodeTypeEnum.CONCEPT)
        target = await knowledge_graph.add_node("Target", NodeTypeEnum.CONCEPT)
        
        # Create first edge
        edge1 = await knowledge_graph.add_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type=EdgeTypeEnum.RELATES_TO,
            weight=0.5,
            confidence=0.6
        )
        
        # Create duplicate edge with different values
        edge2 = await knowledge_graph.add_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type=EdgeTypeEnum.RELATES_TO,
            weight=0.8,
            confidence=0.7
        )
        
        # Should return same edge with reinforced values
        assert edge1.id == edge2.id
        assert edge2.reinforcement_count > edge1.reinforcement_count
        assert edge2.confidence >= edge1.confidence
    
    async def test_project_node_creation(self, knowledge_graph):
        """Test creating project nodes with technology relationships"""
        
        project = await knowledge_graph.add_project_node(
            project_name="Test API",
            project_path="/projects/test-api",
            technologies=["python", "fastapi", "postgresql", "redis"],
            status="active",
            attributes={"team": "backend", "priority": "high"}
        )
        
        assert project.name == "Test API"
        assert project.node_type == NodeTypeEnum.PROJECT
        assert project.attributes["path"] == "/projects/test-api"
        assert project.attributes["status"] == "active"
        assert "python" in project.attributes["technologies"]
        
        # Check that technology nodes were created and connected
        # Note: This would require querying the knowledge graph for edges
        
    async def test_decision_node_creation(self, knowledge_graph):
        """Test creating decision nodes with persona connections"""
        
        decision = await knowledge_graph.add_decision_node(
            decision_title="Choose Database Technology",
            context={"project": "web-app", "requirements": "high-performance"},
            outcome={"choice": "postgresql", "reasoning": "ACID compliance"},
            personas_involved=["analyst", "pragmatist", "guardian"],
            confidence=0.85
        )
        
        assert decision.name == "Choose Database Technology"
        assert decision.node_type == NodeTypeEnum.DECISION
        assert decision.importance == 0.85
        assert decision.attributes["context"]["project"] == "web-app"
        assert "analyst" in decision.attributes["personas_involved"]
    
    async def test_problem_solution_pair(self, knowledge_graph):
        """Test creating problem-solution node pairs"""
        
        problem, solution = await knowledge_graph.add_problem_solution_pair(
            problem_description="Slow database queries",
            solution_description="Add database indexes",
            success_rate=0.9,
            context={"technology": "postgresql", "impact": "high"}
        )
        
        assert problem.node_type == NodeTypeEnum.PROBLEM
        assert solution.node_type == NodeTypeEnum.SOLUTION
        assert solution.importance == 0.9  # Success rate becomes importance
        assert problem.attributes["technology"] == "postgresql"
        
        # Check that solution relationship was created
        # This would require querying edges in a real implementation


class TestGraphAnalytics:
    """Test graph analytics functionality"""
    
    async def test_community_detection(self, analytics):
        """Test community detection algorithms"""
        
        communities = await analytics.perform_community_analysis()
        
        # Should find at least one community
        assert len(communities) >= 1
        
        # Each community should have basic properties
        for community in communities:
            assert community.size > 0
            assert community.community_id >= 0
            assert isinstance(community.members, list)
            assert 0 <= community.density <= 1
            assert 0 <= community.cohesion_score <= 1
    
    async def test_centrality_calculations(self, analytics):
        """Test centrality metric calculations"""
        
        rankings = await analytics.calculate_centrality_rankings()
        
        # Should have rankings for existing nodes
        assert len(rankings) > 0
        
        # Rankings should be ordered by importance
        for i in range(1, len(rankings)):
            assert rankings[i-1].importance_score >= rankings[i].importance_score
        
        # Each ranking should have valid centrality scores
        for ranking in rankings:
            assert 0 <= ranking.betweenness_centrality <= 1
            assert 0 <= ranking.closeness_centrality <= 1
            assert 0 <= ranking.degree_centrality <= 1
            assert ranking.influence_rank > 0
    
    async def test_pattern_detection(self, analytics):
        """Test pattern detection algorithms"""
        
        patterns = await analytics.detect_patterns()
        
        # Should detect some patterns in test data
        assert isinstance(patterns, list)
        
        # Each pattern should have required properties
        for pattern in patterns:
            assert pattern.pattern_type in [
                'hub_nodes', 'bridge_nodes', 'isolated_clusters',
                'technology_adoption', 'decision_chains'
            ]
            assert 0 <= pattern.confidence <= 1
            assert isinstance(pattern.supporting_evidence, list)
            assert isinstance(pattern.recommendations, list)
    
    async def test_trend_analysis(self, analytics):
        """Test temporal trend analysis"""
        
        trends = await analytics.analyze_temporal_trends(time_window_days=30)
        
        # Should return trend analysis
        assert isinstance(trends, list)
        
        # Each trend should have valid properties
        for trend in trends:
            assert trend.trend_direction in ['increasing', 'decreasing', 'stable', 'cyclic']
            assert 0 <= trend.strength <= 1
            assert isinstance(trend.affected_entities, list)
            assert isinstance(trend.predictions, list)
    
    async def test_comprehensive_analysis(self, analytics):
        """Test comprehensive analytics report"""
        
        report = await analytics.get_comprehensive_analysis()
        
        # Should contain all major sections
        assert 'analysis_timestamp' in report
        assert 'graph_overview' in report
        assert 'community_analysis' in report
        assert 'centrality_analysis' in report
        assert 'pattern_detection' in report
        assert 'trend_analysis' in report
        assert 'recommendations' in report
        
        # Graph overview should have basic stats
        overview = report['graph_overview']
        assert overview['total_nodes'] >= 0
        assert overview['total_edges'] >= 0
        assert 0 <= overview['graph_density'] <= 1


class TestGraphVisualization:
    """Test graph visualization functionality"""
    
    async def test_basic_visualization_generation(self, visualizer):
        """Test basic visualization data generation"""
        
        config = VisualizationConfig(
            layout=LayoutType.SPRING,
            color_scheme=ColorScheme.TYPE_BASED,
            max_nodes=100,
            max_edges=200
        )
        
        vis_data = await visualizer.generate_visualization(config)
        
        assert vis_data.nodes is not None
        assert vis_data.edges is not None
        assert vis_data.metadata is not None
        assert vis_data.statistics is not None
        
        # Check metadata
        assert vis_data.metadata['layout_type'] == 'spring'
        assert vis_data.metadata['color_scheme'] == 'type_based'
        assert vis_data.metadata['node_count'] == len(vis_data.nodes)
        assert vis_data.metadata['edge_count'] == len(vis_data.edges)
    
    async def test_different_layouts(self, visualizer):
        """Test different layout algorithms"""
        
        layouts_to_test = [
            LayoutType.SPRING,
            LayoutType.CIRCULAR,
            LayoutType.HIERARCHICAL,
            LayoutType.FORCE_DIRECTED
        ]
        
        for layout in layouts_to_test:
            config = VisualizationConfig(
                layout=layout,
                max_nodes=50
            )
            
            vis_data = await visualizer.generate_visualization(config)
            
            # Should generate valid visualization data
            assert len(vis_data.nodes) <= 50
            assert vis_data.layout_info['type'] == layout.value
            
            # Nodes should have positions
            for node in vis_data.nodes:
                assert node.x is not None
                assert node.y is not None
    
    async def test_color_schemes(self, visualizer):
        """Test different color schemes"""
        
        schemes_to_test = [
            ColorScheme.TYPE_BASED,
            ColorScheme.IMPORTANCE_BASED,
            ColorScheme.COMMUNITY_BASED
        ]
        
        for scheme in schemes_to_test:
            config = VisualizationConfig(
                color_scheme=scheme,
                max_nodes=30
            )
            
            vis_data = await visualizer.generate_visualization(config)
            
            # Nodes should have colors assigned
            for node in vis_data.nodes:
                assert node.color is not None
                assert node.group is not None
    
    async def test_filtering(self, visualizer):
        """Test node and edge filtering"""
        
        config = VisualizationConfig(
            filter_node_types=['project', 'technology'],
            filter_edge_types=['uses'],
            min_importance=0.5,
            min_weight=0.3,
            max_nodes=20
        )
        
        vis_data = await visualizer.generate_visualization(config)
        
        # Should only include specified node types
        for node in vis_data.nodes:
            assert node.type in ['project', 'technology']
            assert node.importance >= 0.5
        
        # Should only include specified edge types
        for edge in vis_data.edges:
            assert edge.type in ['uses']
            assert edge.weight >= 0.3
    
    async def test_d3_export(self, visualizer):
        """Test D3.js format export"""
        
        config = VisualizationConfig(max_nodes=20, max_edges=30)
        d3_data = await visualizer.export_d3_json(config)
        
        # Should have D3.js structure
        assert 'nodes' in d3_data
        assert 'links' in d3_data  # D3 uses 'links' not 'edges'
        assert 'metadata' in d3_data
        assert 'statistics' in d3_data
        
        # Nodes should have required D3 properties
        for node in d3_data['nodes']:
            assert 'id' in node
            assert 'name' in node
            assert 'type' in node
            assert 'x' in node
            assert 'y' in node
        
        # Links should have required D3 properties
        for link in d3_data['links']:
            assert 'source' in link
            assert 'target' in link
            assert 'weight' in link
    
    async def test_cytoscape_export(self, visualizer):
        """Test Cytoscape.js format export"""
        
        config = VisualizationConfig(max_nodes=15, max_edges=20)
        cytoscape_data = await visualizer.export_cytoscape_json(config)
        
        # Should have Cytoscape.js structure
        assert 'elements' in cytoscape_data
        assert 'nodes' in cytoscape_data['elements']
        assert 'edges' in cytoscape_data['elements']
        
        # Nodes should have Cytoscape format
        for node in cytoscape_data['elements']['nodes']:
            assert 'data' in node
            assert 'position' in node
            assert 'style' in node
            assert 'id' in node['data']
    
    async def test_statistics_calculation(self, visualizer):
        """Test visualization statistics"""
        
        config = VisualizationConfig()
        vis_data = await visualizer.generate_visualization(config)
        
        stats = vis_data.statistics
        
        # Should have node statistics
        assert 'nodes' in stats
        assert 'total' in stats['nodes']
        assert 'types' in stats['nodes']
        assert 'avg_importance' in stats['nodes']
        
        # Should have edge statistics
        assert 'edges' in stats
        assert 'total' in stats['edges']
        assert 'types' in stats['edges']
        
        # Should have connectivity statistics
        assert 'connectivity' in stats
        assert 'density' in stats['connectivity']


class TestMemoryIntegration:
    """Test knowledge graph integration with memory system"""
    
    async def test_context_enhancement(self, integrator):
        """Test query context enhancement"""
        
        query = "Should we use React or Vue for our new frontend project?"
        context = {"project_type": "web_app", "team_size": 5}
        
        enhanced = await integrator.enhance_query_context(query, context)
        
        assert enhanced.original_context == context
        assert isinstance(enhanced.related_projects, list)
        assert isinstance(enhanced.technology_recommendations, list)
        assert isinstance(enhanced.expertise_mapping, dict)
        assert 0 <= enhanced.confidence_score <= 1
    
    async def test_project_knowledge_update(self, integrator):
        """Test updating project knowledge"""
        
        project_data = {
            "technologies": ["python", "django", "postgresql"],
            "path": "/projects/test-django",
            "status": "active",
            "team": "backend",
            "complexity": "medium"
        }
        
        # Should not raise exception
        await integrator.update_project_knowledge("Test Django Project", project_data)
    
    async def test_technology_insights(self, integrator):
        """Test technology-specific insights"""
        
        insights = await integrator.get_technology_insights("python")
        
        assert 'technology' in insights
        assert insights['technology'] == "python"
        assert 'related_projects' in insights
        assert 'usage_patterns' in insights
        assert 'recommendations' in insights
    
    async def test_deliberation_insights(self, integrator):
        """Test comprehensive deliberation insights"""
        
        query = "How should we architect our microservices?"
        context = {"system_scale": "medium", "team_experience": "intermediate"}
        
        insights = await integrator.get_deliberation_insights(query, context)
        
        assert 'enhanced_context' in insights
        assert 'project_insights' in insights
        assert 'analytics_summary' in insights
        assert 'recommendations' in insights


class TestPerformance:
    """Test knowledge graph performance with larger datasets"""
    
    @pytest.mark.slow
    async def test_large_graph_creation(self, knowledge_graph):
        """Test creating a large graph with many nodes and edges"""
        
        # Create 100 nodes of different types
        nodes = []
        for i in range(100):
            node_type = [NodeTypeEnum.PROJECT, NodeTypeEnum.TECHNOLOGY, NodeTypeEnum.CONCEPT][i % 3]
            node = await knowledge_graph.add_node(
                name=f"Node_{i}",
                node_type=node_type,
                importance=0.1 + (i % 10) * 0.1
            )
            nodes.append(node)
        
        assert len(knowledge_graph.node_cache) >= 100
        
        # Create 500 edges randomly connecting nodes
        edges = []
        for i in range(500):
            source = nodes[i % len(nodes)]
            target = nodes[(i + 1) % len(nodes)]
            
            if source.id != target.id:
                edge = await knowledge_graph.add_edge(
                    source_id=source.id,
                    target_id=target.id,
                    edge_type=EdgeTypeEnum.RELATES_TO,
                    weight=0.1 + (i % 10) * 0.1
                )
                edges.append(edge)
        
        assert len(knowledge_graph.edge_cache) >= 400  # Some duplicates expected
    
    @pytest.mark.slow
    async def test_analytics_performance(self, analytics):
        """Test analytics performance on larger graphs"""
        
        # Add more test data first
        for i in range(50):
            await analytics.kg.add_node(
                name=f"PerfTest_{i}",
                node_type=NodeTypeEnum.CONCEPT,
                importance=0.5
            )
        
        # Test community detection
        start_time = datetime.now()
        communities = await analytics.perform_community_analysis()
        community_time = (datetime.now() - start_time).total_seconds()
        
        assert community_time < 10.0  # Should complete in under 10 seconds
        assert len(communities) >= 1
        
        # Test centrality calculation
        start_time = datetime.now()
        rankings = await analytics.calculate_centrality_rankings()
        centrality_time = (datetime.now() - start_time).total_seconds()
        
        assert centrality_time < 15.0  # Should complete in under 15 seconds
        assert len(rankings) > 0
    
    @pytest.mark.slow
    async def test_visualization_performance(self, visualizer):
        """Test visualization performance with larger graphs"""
        
        config = VisualizationConfig(
            max_nodes=200,
            max_edges=500,
            layout=LayoutType.SPRING
        )
        
        start_time = datetime.now()
        vis_data = await visualizer.generate_visualization(config)
        viz_time = (datetime.now() - start_time).total_seconds()
        
        assert viz_time < 20.0  # Should complete in under 20 seconds
        assert len(vis_data.nodes) <= 200
        assert len(vis_data.edges) <= 500


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    async def test_invalid_node_operations(self, knowledge_graph):
        """Test handling of invalid node operations"""
        
        # Test invalid node type (this should be prevented by enum)
        with pytest.raises((ValueError, TypeError)):
            await knowledge_graph.add_node(
                name="Invalid Node",
                node_type="invalid_type",  # Should be NodeTypeEnum
                importance=0.5
            )
    
    async def test_invalid_edge_operations(self, knowledge_graph):
        """Test handling of invalid edge operations"""
        
        # Create a valid node first
        valid_node = await knowledge_graph.add_node(
            name="Valid Node",
            node_type=NodeTypeEnum.CONCEPT
        )
        
        # Test edge with non-existent target
        with pytest.raises((ValueError, Exception)):
            await knowledge_graph.add_edge(
                source_id=valid_node.id,
                target_id=uuid.uuid4(),  # Non-existent node
                edge_type=EdgeTypeEnum.RELATES_TO
            )
    
    async def test_empty_graph_analytics(self):
        """Test analytics on empty graph"""
        
        empty_kg = OptimusKnowledgeGraph()
        empty_analytics = GraphAnalytics(empty_kg)
        
        # Should handle empty graph gracefully
        communities = await empty_analytics.perform_community_analysis()
        assert len(communities) == 0
        
        rankings = await empty_analytics.calculate_centrality_rankings()
        assert len(rankings) == 0
        
        patterns = await empty_analytics.detect_patterns()
        assert len(patterns) == 0
    
    async def test_visualization_with_no_data(self):
        """Test visualization with no data"""
        
        empty_kg = OptimusKnowledgeGraph()
        empty_visualizer = GraphVisualizer(empty_kg)
        
        config = VisualizationConfig()
        vis_data = await empty_visualizer.generate_visualization(config)
        
        # Should return empty but valid data structure
        assert len(vis_data.nodes) == 0
        assert len(vis_data.edges) == 0
        assert vis_data.metadata is not None
        assert vis_data.statistics is not None


@pytest.mark.asyncio
async def test_full_integration_workflow():
    """Test complete workflow integration"""
    
    # Initialize system
    integrator = KnowledgeMemoryIntegrator()
    await integrator.initialize()
    
    # Add project knowledge
    await integrator.update_project_knowledge(
        "Integration Test Project",
        {
            "technologies": ["python", "fastapi", "react"],
            "path": "/test/integration",
            "status": "active"
        }
    )
    
    # Get deliberation insights
    insights = await integrator.get_deliberation_insights(
        "Should we add Redis caching to our FastAPI project?",
        {"project": "Integration Test Project", "performance_requirements": "high"}
    )
    
    # Should provide comprehensive insights
    assert 'enhanced_context' in insights
    assert 'project_insights' in insights
    assert 'recommendations' in insights
    
    # Test visualization integration
    config = VisualizationConfig(max_nodes=50)
    vis_data = await integrator.kg.analytics.kg.visualizer.generate_visualization(config)
    
    # Should include our test project
    project_nodes = [n for n in vis_data.nodes if n.type == 'project']
    assert len(project_nodes) > 0


if __name__ == "__main__":
    """Run tests directly"""
    pytest.main([__file__, "-v", "--tb=short"])
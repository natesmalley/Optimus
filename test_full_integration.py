#!/usr/bin/env python3
"""
Full integration test demonstrating tool integration with mock systems.
This test shows the complete workflow without requiring external dependencies.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from council.tool_integration import (
    PersonaToolIntegration, 
    ToolPermission, 
    ToolCategory, 
    ToolCapabilityLevel,
    create_tool_enabled_persona
)

# Mock systems for testing
class MockMemorySystem:
    def __init__(self):
        self.memories = {}
    
    async def store_memory(self, persona_id: str, content: str, context: Dict[str, Any], **kwargs):
        if persona_id not in self.memories:
            self.memories[persona_id] = []
        self.memories[persona_id].append({
            'content': content,
            'context': context,
            'kwargs': kwargs
        })
        return True
    
    async def recall(self, persona_id: str, query: str, context: Dict[str, Any], limit: int = 10):
        return self.memories.get(persona_id, [])[:limit]

class MockKnowledgeGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.node_counter = 0
        self.edge_counter = 0
    
    async def add_node(self, name: str, node_type: Any, **kwargs):
        node_id = f"node_{self.node_counter}"
        self.node_counter += 1
        
        node = type('MockNode', (), {
            'id': node_id,
            'name': name,
            'node_type': node_type,
            'attributes': kwargs.get('attributes', {}),
            'to_dict': lambda: {
                'id': node_id,
                'name': name,
                'node_type': str(node_type),
                'attributes': kwargs.get('attributes', {})
            }
        })()
        
        self.nodes[node_id] = node
        return node
    
    async def add_edge(self, source_id: str, target_id: str, edge_type: Any, **kwargs):
        edge_id = f"edge_{self.edge_counter}"
        self.edge_counter += 1
        
        edge = type('MockEdge', (), {
            'id': edge_id,
            'source_id': source_id,
            'target_id': target_id,
            'edge_type': edge_type,
            'to_dict': lambda: {
                'id': edge_id,
                'source_id': source_id,
                'target_id': target_id,
                'edge_type': str(edge_type)
            }
        })()
        
        self.edges[edge_id] = edge
        return edge
    
    async def find_related(self, node_id: str, **kwargs):
        return {'nodes': list(self.nodes.values())[:3], 'edges': list(self.edges.values())[:3]}

class MockBlackboard:
    def __init__(self):
        self.entries = {}
    
    async def post(self, topic: str, entry: Any):
        if topic not in self.entries:
            self.entries[topic] = []
        self.entries[topic].append(entry)
        return True

async def test_complete_integration():
    """Test the complete tool integration system"""
    print("🧪 Starting complete integration test...")
    
    # Setup mock systems
    memory_system = MockMemorySystem()
    knowledge_graph = MockKnowledgeGraph()
    blackboard = MockBlackboard()
    
    # Initialize tool integration
    tool_integration = PersonaToolIntegration(
        memory_system=memory_system,
        knowledge_graph=knowledge_graph,
        blackboard=blackboard,
        mcp_config_path=None  # Use mock MCP
    )
    
    await tool_integration.initialize()
    print("✅ Tool integration system initialized")
    
    # Create enhanced personas
    strategist = create_tool_enabled_persona(
        persona_id="strategist",
        persona_name="Strategic Advisor",
        expertise_domains=["strategy", "analysis"],
        tool_integration=tool_integration
    )
    
    analyst = create_tool_enabled_persona(
        persona_id="analyst", 
        persona_name="Data Analyst",
        expertise_domains=["analysis", "data_science"],
        tool_integration=tool_integration
    )
    
    # Add specialized permissions
    strategist.add_tool_permission(ToolPermission(
        "web_search",
        ToolCategory.WEB_SEARCH,
        ToolCapabilityLevel.READ_ONLY,
        rate_limit_per_minute=30
    ))
    
    analyst.add_tool_permission(ToolPermission(
        "database_query",
        ToolCategory.DATABASE,
        ToolCapabilityLevel.FULL_ACCESS,
        rate_limit_per_minute=50
    ))
    
    print("✅ Created 2 enhanced personas with permissions")
    
    # Test 1: Basic tool execution
    print("\n📋 Test 1: Basic tool execution")
    result = await strategist.execute_tool(
        "knowledge_query",
        {"query": "AI development"},
        store_result=True
    )
    
    print(f"  Tool execution: {'✅' if result.success else '❌'}")
    print(f"  Execution time: {result.execution_time:.3f}s")
    
    # Test 2: Parallel tool execution
    print("\n📋 Test 2: Parallel tool execution")
    tool_requests = [
        ("knowledge_query", {"query": "machine learning"}),
        ("knowledge_query", {"query": "data analysis"}),
        ("knowledge_query", {"query": "software architecture"})
    ]
    
    results = await analyst.execute_tools_parallel(tool_requests, max_concurrent=2)
    successful = sum(1 for r in results if r.success)
    
    print(f"  Parallel execution: {successful}/{len(results)} successful")
    print(f"  Total time: {sum(r.execution_time for r in results):.3f}s")
    
    # Test 3: Agent delegation
    print("\n📋 Test 3: CoralCollective agent delegation")
    delegation_result = await strategist.delegate_to_agent(
        agent_type="backend_development",
        task_description="Create user authentication system",
        context={"framework": "FastAPI", "security": "JWT"}
    )
    
    print(f"  Agent delegation: {'✅' if delegation_result.success else '❌'}")
    if delegation_result.success:
        result_data = delegation_result.result
        print(f"  Assigned to: {result_data['agent_name']}")
        print(f"  Delegation ID: {result_data['delegation_id']}")
    
    # Test 4: Memory integration
    print("\n📋 Test 4: Memory integration")
    memories = await memory_system.recall(
        persona_id="strategist",
        query="tool usage",
        context={},
        limit=5
    )
    
    print(f"  Stored memories: {len(memories)}")
    if memories:
        print(f"  Latest memory: {memories[0]['content'][:50]}...")
    
    # Test 5: Knowledge graph updates
    print("\n📋 Test 5: Knowledge graph integration") 
    node_count_before = len(knowledge_graph.nodes)
    edge_count_before = len(knowledge_graph.edges)
    
    # Execute a tool that should update the knowledge graph
    await analyst.execute_tool(
        "knowledge_add_node",
        {
            "name": "Test Analysis Node",
            "node_type": "CONCEPT",
            "attributes": {"type": "test"}
        }
    )
    
    print(f"  Nodes created: {len(knowledge_graph.nodes) - node_count_before}")
    print(f"  Edges created: {len(knowledge_graph.edges) - edge_count_before}")
    
    # Test 6: Tool metrics
    print("\n📋 Test 6: Tool usage metrics")
    strategist_metrics = strategist.get_tool_metrics()
    analyst_metrics = analyst.get_tool_metrics()
    
    total_calls = (
        sum(m.total_calls for m in strategist_metrics.values()) +
        sum(m.total_calls for m in analyst_metrics.values())
    )
    
    print(f"  Strategist tools used: {len(strategist_metrics)}")
    print(f"  Analyst tools used: {len(analyst_metrics)}")
    print(f"  Total tool calls: {total_calls}")
    
    # Test 7: System analytics
    print("\n📋 Test 7: System analytics")
    analytics = await tool_integration.get_tool_usage_analytics()
    
    print(f"  Cached results: {analytics['total_cached_results']}")
    print(f"  Active interfaces: {analytics['active_agent_interfaces']}")
    print(f"  MCP status: {'✅' if analytics['mcp_client_status'] else '❌'}")
    
    # Test 8: Rate limiting
    print("\n📋 Test 8: Rate limiting")
    # Try to exceed rate limit
    rate_limit_results = []
    for i in range(5):  # Try 5 rapid calls
        result = await strategist.execute_tool("knowledge_query", {"query": f"test_{i}"})
        rate_limit_results.append(result.success)
    
    successful_rapid_calls = sum(rate_limit_results)
    print(f"  Rapid calls handled: {successful_rapid_calls}/5")
    
    # Cleanup
    await tool_integration.cleanup()
    print("\n✅ Integration test completed successfully!")
    
    return True

async def main():
    """Run the complete integration test"""
    try:
        success = await test_complete_integration()
        if success:
            print("\n🎉 All integration tests passed!")
            return 0
        else:
            print("\n❌ Some integration tests failed!")
            return 1
    except Exception as e:
        print(f"\n💥 Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
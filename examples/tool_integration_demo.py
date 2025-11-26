#!/usr/bin/env python3
"""
Comprehensive Tool Integration Demo for Optimus Council of Minds

This script demonstrates the full capabilities of the tool integration system:
1. Setting up personas with tool capabilities
2. Parallel tool execution
3. Memory and knowledge graph integration
4. CoralCollective agent delegation
5. Blackboard sharing and collaboration

Run with: python examples/tool_integration_demo.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from council.memory import MemorySystem
from council.knowledge_graph import KnowledgeGraph, NodeType, EdgeType
from council.blackboard import Blackboard
from council.tool_integration import (
    PersonaToolIntegration, 
    ToolPermission, 
    ToolCategory, 
    ToolCapabilityLevel,
    create_tool_enabled_persona
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ToolIntegrationDemo:
    """Comprehensive demonstration of tool integration capabilities"""
    
    def __init__(self):
        self.memory_system = None
        self.knowledge_graph = None
        self.blackboard = None
        self.tool_integration = None
        self.personas = {}
    
    async def setup(self):
        """Initialize all systems"""
        logger.info("Setting up tool integration demo...")
        
        # Initialize core systems
        self.memory_system = MemorySystem("demo_memory.db")
        self.knowledge_graph = KnowledgeGraph("demo_knowledge.db")
        self.blackboard = Blackboard()
        
        # Initialize tool integration
        self.tool_integration = PersonaToolIntegration(
            memory_system=self.memory_system,
            knowledge_graph=self.knowledge_graph,
            blackboard=self.blackboard,
            mcp_config_path=".coral/mcp/configs/mcp_config.yaml"  # If available
        )
        
        await self.tool_integration.initialize()
        
        # Create enhanced personas
        await self.create_personas()
        
        logger.info("Setup complete!")
    
    async def create_personas(self):
        """Create personas with tool capabilities"""
        
        # Create Strategist with enhanced permissions
        strategist = create_tool_enabled_persona(
            persona_id="strategist",
            persona_name="Strategic Advisor",
            expertise_domains=["strategy", "planning", "analysis", "market_research"],
            tool_integration=self.tool_integration
        )
        
        # Add specialized permissions for strategist
        strategist.add_tool_permission(ToolPermission(
            "web_search", 
            ToolCategory.WEB_SEARCH, 
            ToolCapabilityLevel.READ_ONLY,
            rate_limit_per_minute=50
        ))
        strategist.add_tool_permission(ToolPermission(
            "database_query", 
            ToolCategory.DATABASE, 
            ToolCapabilityLevel.READ_ONLY,
            rate_limit_per_minute=30
        ))
        
        # Create Analyst with data access
        analyst = create_tool_enabled_persona(
            persona_id="analyst",
            persona_name="Data Analyst",
            expertise_domains=["analysis", "data_science", "metrics", "research"],
            tool_integration=self.tool_integration
        )
        
        # Add data-focused permissions
        analyst.add_tool_permission(ToolPermission(
            "code_execute", 
            ToolCategory.CODE_EXECUTION, 
            ToolCapabilityLevel.LIMITED_WRITE,
            rate_limit_per_minute=20
        ))
        analyst.add_tool_permission(ToolPermission(
            "database_query", 
            ToolCategory.DATABASE, 
            ToolCapabilityLevel.FULL_ACCESS,
            rate_limit_per_minute=100
        ))
        
        # Create Pragmatist with implementation focus
        pragmatist = create_tool_enabled_persona(
            persona_id="pragmatist", 
            persona_name="Implementation Specialist",
            expertise_domains=["development", "implementation", "project_management"],
            tool_integration=self.tool_integration
        )
        
        # Add development permissions
        pragmatist.add_tool_permission(ToolPermission(
            "filesystem_write", 
            ToolCategory.FILE_SYSTEM, 
            ToolCapabilityLevel.FULL_ACCESS,
            rate_limit_per_minute=40
        ))
        pragmatist.add_tool_permission(ToolPermission(
            "git_create_pr", 
            ToolCategory.VERSION_CONTROL, 
            ToolCapabilityLevel.FULL_ACCESS,
            rate_limit_per_minute=10
        ))
        
        # Connect to blackboard
        self.blackboard = Blackboard()
        strategist.connect_blackboard(self.blackboard)
        analyst.connect_blackboard(self.blackboard)
        pragmatist.connect_blackboard(self.blackboard)
        
        self.personas = {
            "strategist": strategist,
            "analyst": analyst,
            "pragmatist": pragmatist
        }
        
        logger.info("Created 3 enhanced personas with tool capabilities")
    
    async def demo_basic_tool_usage(self):
        """Demonstrate basic tool usage"""
        logger.info("\n=== Demo: Basic Tool Usage ===")
        
        strategist = self.personas["strategist"]
        
        # Test filesystem read
        result = await strategist.execute_tool(
            "filesystem_read",
            {"path": "README.md"},
            store_result=True,
            share_on_blackboard=True
        )
        
        print(f"✓ Filesystem read: {result.success}")
        if result.success and result.result:
            print(f"  Read {len(result.result)} characters from README.md")
        
        # Test web search (if available)
        result = await strategist.execute_tool(
            "web_search",
            {"query": "AI development best practices", "max_results": 3},
            store_result=True
        )
        
        print(f"✓ Web search: {result.success}")
        if result.success:
            search_results = result.result.get("results", [])
            print(f"  Found {len(search_results)} results")
        
        # Test knowledge graph query
        result = await strategist.execute_tool(
            "knowledge_query",
            {"query": "AI development"},
            store_result=True
        )
        
        print(f"✓ Knowledge query: {result.success}")
        if result.success:
            print(f"  Found {len(result.result.get('results', []))} knowledge items")
    
    async def demo_parallel_execution(self):
        """Demonstrate parallel tool execution"""
        logger.info("\n=== Demo: Parallel Tool Execution ===")
        
        analyst = self.personas["analyst"]
        
        # Execute multiple tools in parallel
        tool_requests = [
            ("filesystem_read", {"path": "pyproject.toml"}),
            ("filesystem_list", {"path": "src"}),
            ("knowledge_query", {"query": "development tools"}),
            ("web_search", {"query": "Python best practices", "max_results": 2})
        ]
        
        print(f"Executing {len(tool_requests)} tools in parallel...")
        
        results = await analyst.execute_tools_parallel(
            tool_requests=tool_requests,
            max_concurrent=3
        )
        
        success_count = sum(1 for r in results if r.success)
        total_time = sum(r.execution_time for r in results)
        
        print(f"✓ Parallel execution complete:")
        print(f"  {success_count}/{len(results)} tools succeeded")
        print(f"  Total execution time: {total_time:.2f}s")
        print(f"  Average per tool: {total_time/len(results):.2f}s")
        
        # Show individual results
        for result in results:
            status = "✓" if result.success else "✗"
            print(f"  {status} {result.tool_name}: {result.execution_time:.2f}s")
    
    async def demo_agent_delegation(self):
        """Demonstrate CoralCollective agent delegation"""
        logger.info("\n=== Demo: CoralCollective Agent Delegation ===")
        
        pragmatist = self.personas["pragmatist"]
        
        # Delegate backend development task
        backend_task = await pragmatist.delegate_to_agent(
            agent_type="backend_development",
            task_description="Create a REST API for user authentication with JWT tokens",
            context={
                "framework": "FastAPI",
                "database": "PostgreSQL", 
                "requirements": ["secure", "scalable", "well_documented"]
            }
        )
        
        print(f"✓ Backend delegation: {backend_task.success}")
        if backend_task.success:
            result = backend_task.result
            print(f"  Delegation ID: {result['delegation_id']}")
            print(f"  Assigned to: {result['agent_name']}")
            print(f"  Status: {result['status']}")
        
        # Delegate AI/ML task
        ai_task = await pragmatist.delegate_to_agent(
            agent_type="ai_ml",
            task_description="Implement sentiment analysis for user feedback",
            context={
                "model_type": "transformer",
                "data_source": "user_reviews",
                "accuracy_target": "85%"
            }
        )
        
        print(f"✓ AI/ML delegation: {ai_task.success}")
        if ai_task.success:
            result = ai_task.result
            print(f"  Assigned to: {result['agent_name']}")
    
    async def demo_collaborative_research(self):
        """Demonstrate collaborative research using multiple personas"""
        logger.info("\n=== Demo: Collaborative Research ===")
        
        research_topic = "microservices architecture patterns"
        
        # Each persona contributes their expertise
        strategist_research = await self.personas["strategist"].research_topic(research_topic)
        analyst_data = await self.personas["analyst"].research_topic(research_topic) 
        
        print(f"✓ Collaborative research on: {research_topic}")
        print(f"  Strategist found {len(strategist_research.get('web_results', []))} web results")
        print(f"  Analyst found {len(analyst_data.get('knowledge_results', []))} knowledge items")
        
        # Share findings on blackboard
        await self.blackboard.post("research_collaboration", {
            "topic": research_topic,
            "strategist_findings": strategist_research,
            "analyst_findings": analyst_data,
            "collaboration_timestamp": "2024-01-15T10:30:00Z"
        })
        
        print("✓ Research findings shared on blackboard")
    
    async def demo_memory_integration(self):
        """Demonstrate memory system integration"""
        logger.info("\n=== Demo: Memory System Integration ===")
        
        analyst = self.personas["analyst"]
        
        # Recall past tool usage
        memories = await self.memory_system.recall(
            persona_id="analyst",
            query="tool usage filesystem",
            context={"category": "tool_usage"},
            limit=5
        )
        
        print(f"✓ Retrieved {len(memories)} relevant memories")
        for memory in memories:
            print(f"  - {memory.content[:80]}...")
        
        # Store new insight
        await self.memory_system.store_memory(
            persona_id="analyst",
            content="Tool integration demo completed successfully. All systems working well.",
            context={"event": "demo", "success": True},
            importance=0.8,
            emotional_valence=0.5,
            tags={"demo", "success", "tool_integration"}
        )
        
        print("✓ Stored demo completion memory")
    
    async def demo_knowledge_graph_updates(self):
        """Demonstrate knowledge graph integration"""
        logger.info("\n=== Demo: Knowledge Graph Updates ===")
        
        # Add tool integration concept
        integration_node = await self.knowledge_graph.add_node(
            name="Tool Integration System",
            node_type=NodeType.CONCEPT,
            attributes={
                "type": "system",
                "capabilities": ["parallel_execution", "agent_delegation", "memory_storage"]
            },
            importance=0.9
        )
        
        # Add persona nodes and relationships
        for persona_name, persona in self.personas.items():
            persona_node = await self.knowledge_graph.add_node(
                name=persona.name,
                node_type=NodeType.PERSON,
                attributes={"type": "persona", "expertise": persona.expertise_domains}
            )
            
            # Connect persona to tool integration
            await self.knowledge_graph.add_edge(
                source_id=persona_node.id,
                target_id=integration_node.id,
                edge_type=EdgeType.INFLUENCES,
                weight=1.0,
                confidence=0.9
            )
        
        print("✓ Updated knowledge graph with tool integration concepts")
        
        # Find related concepts
        related = await self.knowledge_graph.find_related(
            integration_node.id,
            max_depth=2
        )
        
        print(f"✓ Found {len(related.get('nodes', []))} related concepts")
    
    async def show_analytics(self):
        """Show comprehensive analytics"""
        logger.info("\n=== Analytics Summary ===")
        
        # Tool usage analytics
        analytics = await self.tool_integration.get_tool_usage_analytics()
        
        print("Tool Integration Analytics:")
        print(f"  Cached results: {analytics['total_cached_results']}")
        print(f"  Active interfaces: {analytics['active_agent_interfaces']}")
        print(f"  Available CoralCollective agents: {analytics['coral_agents_available']}")
        print(f"  MCP client status: {'✓' if analytics['mcp_client_status'] else '✗'}")
        
        if 'mcp_servers' in analytics:
            print(f"  Available MCP servers: {', '.join(analytics['mcp_servers'])}")
        
        # Persona metrics
        print("\nPersona Tool Usage:")
        for name, persona in self.personas.items():
            metrics = persona.get_tool_metrics()
            total_calls = sum(m.total_calls for m in metrics.values())
            success_rate = sum(m.successful_calls for m in metrics.values()) / max(total_calls, 1)
            
            print(f"  {name}:")
            print(f"    Total tool calls: {total_calls}")
            print(f"    Success rate: {success_rate:.1%}")
            print(f"    Tools used: {len(metrics)}")
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up demo resources...")
        
        if self.tool_integration:
            await self.tool_integration.cleanup()
        
        logger.info("Demo cleanup complete")
    
    async def run_full_demo(self):
        """Run the complete demonstration"""
        try:
            await self.setup()
            
            print("\n" + "="*60)
            print("    OPTIMUS TOOL INTEGRATION DEMO")
            print("="*60)
            
            await self.demo_basic_tool_usage()
            await self.demo_parallel_execution()
            await self.demo_agent_delegation()
            await self.demo_collaborative_research()
            await self.demo_memory_integration()
            await self.demo_knowledge_graph_updates()
            await self.show_analytics()
            
            print("\n" + "="*60)
            print("    DEMO COMPLETED SUCCESSFULLY")
            print("="*60)
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.cleanup()


async def main():
    """Main demo entry point"""
    demo = ToolIntegrationDemo()
    await demo.run_full_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()
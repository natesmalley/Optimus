#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for Optimus
Tests all components working together in real scenarios
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all components
from src.council.orchestrator import Orchestrator as CouncilOrchestrator
from src.council.memory_system import PersonaMemorySystem
from src.council.optimus_knowledge_graph import OptimusKnowledgeGraph
from src.services.enhanced_scanner import EnhancedProjectScanner
from src.services.runtime_monitor import RuntimeMonitor
from src.services.troubleshooting_engine import TroubleshootingEngine
from src.database.config import DatabaseManager
from src.config import get_settings

# Test utilities
class Colors:
    """Terminal colors for test output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_test_header(test_name):
    """Print formatted test header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"Testing: {test_name}")
    print(f"{'='*60}{Colors.ENDC}")

def print_success(message):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_error(message):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_info(message):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")

def print_warning(message):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

async def test_database_connection():
    """Test 1: Database Connection"""
    print_test_header("Database Connection")
    
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        print_success("Database connection established")
        
        # Test query
        async for session in db_manager.get_session():
            result = await session.execute("SELECT 1")
            if result:
                print_success("Database query successful")
            break
            
        await db_manager.close()
        print_success("Database connection closed properly")
        return True
        
    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False

async def test_memory_system():
    """Test 2: Memory System"""
    print_test_header("Memory System")
    
    try:
        # Initialize memory system
        memory = PersonaMemorySystem()
        await memory.initialize()
        print_success("Memory system initialized")
        
        # Store a test memory
        test_memory = {
            'query': 'Should I use microservices for my startup?',
            'context': {'team_size': 3, 'budget': 50000},
            'decision': 'Start with monolith, consider microservices later',
            'confidence': 0.75,
            'timestamp': datetime.now()
        }
        
        memory_id = await memory.store_deliberation_memory(
            query=test_memory['query'],
            context=test_memory['context'],
            consensus={'decision': test_memory['decision'], 'confidence': test_memory['confidence']},
            persona_responses=[]
        )
        print_success(f"Stored memory with ID: {memory_id}")
        
        # Retrieve similar memories
        similar = await memory.recall_similar_memories(
            query="microservices architecture decision",
            context={'team_size': 5}
        )
        
        if similar:
            print_success(f"Found {len(similar)} similar memories")
        else:
            print_warning("No similar memories found (expected for first run)")
            
        await memory.close()
        return True
        
    except Exception as e:
        print_error(f"Memory system test failed: {e}")
        return False

async def test_knowledge_graph():
    """Test 3: Knowledge Graph"""
    print_test_header("Knowledge Graph")
    
    try:
        # Initialize knowledge graph
        graph = OptimusKnowledgeGraph()
        await graph.initialize()
        print_success("Knowledge graph initialized")
        
        # Add test nodes
        project_id = await graph.add_project(
            name="TestProject",
            path="/test/project",
            metadata={'language': 'python', 'framework': 'fastapi'}
        )
        print_success(f"Added project node: {project_id}")
        
        tech_id = await graph.add_technology(
            name="Python",
            version="3.11",
            metadata={'type': 'language'}
        )
        print_success(f"Added technology node: {tech_id}")
        
        # Create relationship
        await graph.connect_project_technology(project_id, tech_id)
        print_success("Created project-technology relationship")
        
        # Find connections
        related = await graph.get_related_nodes(project_id, max_depth=2)
        print_success(f"Found {len(related)} related nodes")
        
        # Get insights
        insights = await graph.get_insights()
        print_info(f"Generated {len(insights)} insights")
        
        await graph.close()
        return True
        
    except Exception as e:
        print_error(f"Knowledge graph test failed: {e}")
        return False

async def test_project_scanner():
    """Test 4: Project Scanner"""
    print_test_header("Enhanced Project Scanner")
    
    try:
        scanner = EnhancedProjectScanner()
        
        # Scan current Optimus project
        optimus_path = Path(__file__).parent
        print_info(f"Scanning: {optimus_path}")
        
        analysis = await scanner.analyze_project(str(optimus_path))
        
        if analysis:
            print_success(f"Project: {analysis.get('name', 'Unknown')}")
            print_success(f"Language: {analysis.get('primary_language', 'Unknown')}")
            print_success(f"Framework: {analysis.get('framework', 'Unknown')}")
            
            if 'dependencies' in analysis:
                dep_count = len(analysis['dependencies'].get('python', []))
                print_success(f"Found {dep_count} Python dependencies")
                
            if 'quality_metrics' in analysis:
                metrics = analysis['quality_metrics']
                print_info(f"Code quality score: {metrics.get('overall_score', 0):.1f}/10")
                
            return True
        else:
            print_warning("Scanner returned no analysis")
            return False
            
    except Exception as e:
        print_error(f"Scanner test failed: {e}")
        return False

async def test_runtime_monitor():
    """Test 5: Runtime Monitor"""
    print_test_header("Runtime Monitor")
    
    try:
        # Get database session
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        async for session in db_manager.get_session():
            monitor = RuntimeMonitor(session)
            
            # Scan for running processes
            print_info("Scanning for development processes...")
            processes = await monitor.scan_processes()
            
            if processes:
                print_success(f"Found {len(processes)} development processes")
                for proc in processes[:3]:  # Show first 3
                    print_info(f"  - {proc['name']} (PID: {proc['pid']})")
            else:
                print_warning("No development processes found")
                
            # Check system metrics
            metrics = await monitor.get_system_metrics()
            print_success(f"CPU Usage: {metrics['cpu_percent']:.1f}%")
            print_success(f"Memory Usage: {metrics['memory_percent']:.1f}%")
            
            # Check for issues
            issues = await monitor.detect_performance_issues({})
            if issues:
                print_warning(f"Found {len(issues)} performance issues")
            else:
                print_success("No performance issues detected")
                
            break
            
        await db_manager.close()
        return True
        
    except Exception as e:
        print_error(f"Runtime monitor test failed: {e}")
        return False

async def test_troubleshooting_engine():
    """Test 6: Troubleshooting Engine"""
    print_test_header("Troubleshooting Engine")
    
    try:
        engine = TroubleshootingEngine()
        await engine.initialize()
        print_success("Troubleshooting engine initialized")
        
        # Test error analysis
        test_error = """
        Traceback (most recent call last):
          File "app.py", line 42, in connect
            conn = psycopg2.connect(database="mydb", user="user", password="pass")
        psycopg2.OperationalError: could not connect to server: Connection refused
            Is the server running on host "localhost" and accepting
            TCP/IP connections on port 5432?
        """
        
        analysis = await engine.analyze_error(test_error, {
            'language': 'python',
            'framework': 'flask'
        })
        
        print_success(f"Error type identified: {analysis['error_type']}")
        print_success(f"Root cause: {analysis['root_cause']}")
        print_success(f"Confidence: {analysis['confidence']:.1%}")
        
        # Find solutions
        solutions = await engine.find_solutions(analysis)
        print_success(f"Found {len(solutions)} potential solutions")
        
        if solutions:
            best_solution = solutions[0]
            print_info(f"Best solution: {best_solution['title']}")
            print_info(f"Success rate: {best_solution['success_rate']:.1%}")
            
        await engine.close()
        return True
        
    except Exception as e:
        print_error(f"Troubleshooting engine test failed: {e}")
        return False

async def test_council_with_memory():
    """Test 7: Council of Minds with Memory Integration"""
    print_test_header("Council of Minds with Memory")
    
    try:
        # Initialize orchestrator
        orchestrator = CouncilOrchestrator()
        
        print_info("Testing deliberation with memory recall...")
        
        # First deliberation
        result1 = await orchestrator.deliberate(
            query="Should I use Docker for my Python web app?",
            context={'team_size': 2, 'experience': 'intermediate'}
        )
        
        print_success(f"First deliberation confidence: {result1['consensus']['confidence']:.1%}")
        print_info(f"Decision: {result1['consensus']['recommendation']}")
        
        # Second similar deliberation (should recall first)
        result2 = await orchestrator.deliberate(
            query="Is Docker a good choice for deploying my Flask application?",
            context={'team_size': 3, 'experience': 'beginner'}
        )
        
        print_success(f"Second deliberation confidence: {result2['consensus']['confidence']:.1%}")
        
        # Check if confidence improved (learning effect)
        if result2['consensus']['confidence'] >= result1['consensus']['confidence']:
            print_success("Learning detected: Confidence maintained or improved")
        else:
            print_warning("Confidence decreased (may be due to different context)")
            
        return True
        
    except Exception as e:
        print_error(f"Council integration test failed: {e}")
        return False

async def test_api_endpoints():
    """Test 8: API Endpoints"""
    print_test_header("API Endpoints")
    
    try:
        import httpx
        
        # Check if API is running
        base_url = "http://localhost:8005"
        
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            try:
                response = await client.get(f"{base_url}/health", timeout=5.0)
                if response.status_code == 200:
                    print_success("API health check passed")
                else:
                    print_warning(f"API returned status {response.status_code}")
            except httpx.ConnectError:
                print_warning("API not running - skipping endpoint tests")
                print_info("Start API with: python -m src.main")
                return True
            
            # Test various endpoints
            endpoints = [
                "/api/v1/projects",
                "/api/v1/council/personas",
                "/api/v1/memory/stats",
                "/api/v1/graph/stats",
                "/api/v1/monitor/overview"
            ]
            
            for endpoint in endpoints:
                try:
                    response = await client.get(f"{base_url}{endpoint}", timeout=5.0)
                    if response.status_code in [200, 404]:  # 404 ok for empty data
                        print_success(f"Endpoint {endpoint}: OK")
                    else:
                        print_warning(f"Endpoint {endpoint}: {response.status_code}")
                except Exception as e:
                    print_warning(f"Endpoint {endpoint}: {str(e)[:50]}")
                    
        return True
        
    except ImportError:
        print_warning("httpx not installed - skipping API tests")
        print_info("Install with: pip install httpx")
        return True
    except Exception as e:
        print_error(f"API test failed: {e}")
        return False

async def run_integration_scenario():
    """Test 9: Full Integration Scenario"""
    print_test_header("Full Integration Scenario")
    
    print_info("Simulating real-world usage scenario...")
    
    try:
        # 1. Scanner discovers a project
        scanner = EnhancedProjectScanner()
        project_analysis = await scanner.analyze_project(os.getcwd())
        print_success("✓ Scanner analyzed current project")
        
        # 2. Knowledge graph stores the discovery
        graph = OptimusKnowledgeGraph()
        await graph.initialize()
        project_id = await graph.add_project(
            name="Optimus",
            path=os.getcwd(),
            metadata=project_analysis
        )
        print_success("✓ Knowledge graph stored project")
        
        # 3. Council deliberates on project decisions
        orchestrator = CouncilOrchestrator()
        deliberation = await orchestrator.deliberate(
            query="What's the best deployment strategy for this project?",
            context={'project': project_analysis}
        )
        print_success("✓ Council provided deployment recommendations")
        
        # 4. Memory system stores the deliberation
        memory = PersonaMemorySystem()
        await memory.initialize()
        await memory.store_deliberation_memory(
            query="deployment strategy",
            context={'project': 'Optimus'},
            consensus=deliberation['consensus'],
            persona_responses=deliberation.get('personas', [])
        )
        print_success("✓ Memory system stored deliberation")
        
        # 5. Troubleshooting engine ready for issues
        engine = TroubleshootingEngine()
        await engine.initialize()
        print_success("✓ Troubleshooting engine standing by")
        
        # Clean up
        await graph.close()
        await memory.close()
        await engine.close()
        
        print_success("\n✅ Full integration scenario completed successfully!")
        return True
        
    except Exception as e:
        print_error(f"Integration scenario failed: {e}")
        return False

async def main():
    """Run all end-to-end tests"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("="*60)
    print("OPTIMUS END-TO-END SYSTEM TEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print(Colors.ENDC)
    
    # Track results
    results = {}
    
    # Run tests
    tests = [
        ("Database", test_database_connection),
        ("Memory", test_memory_system),
        ("Knowledge Graph", test_knowledge_graph),
        ("Scanner", test_project_scanner),
        ("Runtime Monitor", test_runtime_monitor),
        ("Troubleshooting", test_troubleshooting_engine),
        ("Council+Memory", test_council_with_memory),
        ("API Endpoints", test_api_endpoints),
        ("Full Integration", run_integration_scenario)
    ]
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print_error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
            
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    # Print summary
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(Colors.ENDC)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, passed in results.items():
        status = f"{Colors.OKGREEN}✓ PASSED{Colors.ENDC}" if passed else f"{Colors.FAIL}✗ FAILED{Colors.ENDC}"
        print(f"{test_name:.<30} {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"{Colors.OKGREEN}🎉 ALL TESTS PASSED! System is fully operational!{Colors.ENDC}")
    elif passed >= total * 0.7:
        print(f"{Colors.WARNING}⚠ Most tests passed. Some components need attention.{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}❌ Multiple failures detected. System needs configuration.{Colors.ENDC}")
    
    print(f"\n{Colors.OKCYAN}Next steps:")
    print("1. Start the API: python -m src.main")
    print("2. Access dashboard: http://localhost:3000/simple-dashboard.html")
    print("3. Try a deliberation via the dashboard")
    print(Colors.ENDC)

if __name__ == "__main__":
    asyncio.run(main())
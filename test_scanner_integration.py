#!/usr/bin/env python3
"""
Quick integration test for the enhanced scanner system.
Tests integration with existing knowledge graph and memory systems.
"""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.initialize import get_session
from src.council.memory_integration import MemoryIntegration
from src.council.knowledge_graph_integration import KnowledgeGraphIntegration
from src.services.enhanced_scanner import EnhancedProjectScanner
from src.services.runtime_monitor import RuntimeMonitor
from src.services.project_analyzer import ProjectAnalyzer
from src.services.scanner_orchestrator import ScannerOrchestrator, ScanType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("scanner_integration_test")


async def create_test_project():
    """Create a small test project for scanning."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)
    
    logger.info(f"Creating test project at: {project_path}")
    
    # Create a simple Python project
    (project_path / "main.py").write_text("""
#!/usr/bin/env python3
import os
import requests

# Test security issue: hardcoded secret
API_KEY = "sk-1234567890abcdef"

def main():
    print("Hello, world!")
    return True

if __name__ == "__main__":
    main()
""")
    
    (project_path / "requirements.txt").write_text("""
requests==2.31.0
flask==2.3.0
""")
    
    (project_path / "README.md").write_text("""
# Test Project

A simple test project for scanner integration testing.

## Usage

```bash
python main.py
```
""")
    
    return project_path


async def test_enhanced_scanner_integration():
    """Test enhanced scanner with real integrations."""
    logger.info("=== Testing Enhanced Scanner Integration ===")
    
    try:
        # Get database session
        async with get_session() as session:
            logger.info("✓ Database session created")
            
            # Initialize integrations
            memory = MemoryIntegration()
            await memory.initialize()
            logger.info("✓ Memory integration initialized")
            
            kg = KnowledgeGraphIntegration()
            await kg.initialize()
            logger.info("✓ Knowledge graph integration initialized")
            
            # Create test project
            test_project = await create_test_project()
            logger.info(f"✓ Test project created: {test_project}")
            
            # Test Enhanced Project Scanner
            logger.info("--- Testing Enhanced Project Scanner ---")
            scanner = EnhancedProjectScanner(session, memory, kg)
            
            # Scan the test project
            start_time = datetime.now()
            analysis = await scanner._analyze_project_comprehensive(test_project)
            scan_duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✓ Project analysis completed in {scan_duration:.2f}s")
            logger.info(f"  - Languages detected: {analysis.tech_stack.get('languages', [])}")
            logger.info(f"  - Frameworks found: {analysis.frameworks}")
            logger.info(f"  - Dependencies: {len(analysis.dependencies.get('runtime', {}))}")
            logger.info(f"  - Security issues: {len(analysis.security.get('vulnerabilities', []))}")
            logger.info(f"  - Code files analyzed: {analysis.tech_stack.get('total_files', 0)}")
            
            # Test Runtime Monitor
            logger.info("--- Testing Runtime Monitor ---")
            runtime_monitor = RuntimeMonitor(session, memory, kg)
            await runtime_monitor.initialize()
            
            # Scan for processes (just a few for testing)
            processes = await runtime_monitor.scan_processes()
            services = await runtime_monitor.scan_services()
            system_metrics = await runtime_monitor.collect_system_metrics()
            
            logger.info(f"✓ Runtime monitoring completed")
            logger.info(f"  - Development processes found: {len(processes)}")
            logger.info(f"  - Active services found: {len(services)}")
            logger.info(f"  - System CPU: {system_metrics.cpu_percent:.1f}%")
            logger.info(f"  - System Memory: {system_metrics.memory_percent:.1f}%")
            
            # Test Project Analyzer
            logger.info("--- Testing Project Analyzer ---")
            analyzer = ProjectAnalyzer(session, memory, kg)
            
            analysis_result = await analyzer.analyze_project(str(test_project), "test-project-123")
            
            logger.info(f"✓ Project analysis completed")
            logger.info(f"  - Overall score: {analysis_result.overall_score:.1f}")
            logger.info(f"  - Security issues: {len(analysis_result.security_issues)}")
            logger.info(f"  - Quality issues: {len(analysis_result.quality_issues)}")
            logger.info(f"  - Recommendations: {len(analysis_result.recommendations)}")
            
            if analysis_result.security_issues:
                logger.info(f"  - Sample security issue: {analysis_result.security_issues[0].description}")
            
            # Test Memory Integration
            logger.info("--- Testing Memory Integration ---")
            test_context = {
                "test_type": "scanner_integration",
                "timestamp": datetime.now().isoformat(),
                "project_analyzed": str(test_project),
                "scan_results": {
                    "languages": analysis.tech_stack.get('languages', []),
                    "security_score": max(0, 100 - len(analysis_result.security_issues) * 10),
                    "overall_score": analysis_result.overall_score
                }
            }
            
            await memory.store_context("integration_test", test_context)
            logger.info("✓ Context stored in memory system")
            
            # Test Knowledge Graph Integration
            logger.info("--- Testing Knowledge Graph Integration ---")
            
            # Add project node
            await kg.add_node("test-project-123", "Project", {
                "name": test_project.name,
                "path": str(test_project),
                "languages": analysis.tech_stack.get('languages', [])
            })
            
            # Add technology nodes
            for lang in analysis.tech_stack.get('languages', []):
                lang_id = f"lang_{lang}"
                await kg.add_node(lang_id, "Language", {"name": lang})
                await kg.add_relationship("test-project-123", lang_id, "USES_LANGUAGE", {})
            
            logger.info("✓ Project relationships added to knowledge graph")
            
            # Test Scanner Orchestrator (light test)
            logger.info("--- Testing Scanner Orchestrator ---")
            orchestrator = ScannerOrchestrator(session, memory, kg)
            
            # Just test initialization and status
            await orchestrator.initialize()
            status = await orchestrator.get_orchestrator_status()
            
            logger.info(f"✓ Scanner orchestrator initialized")
            logger.info(f"  - Active jobs: {status['active_jobs']}")
            logger.info(f"  - System health: {status['system_health']}")
            
            logger.info("=== Integration Test Completed Successfully ===")
            return True
            
    except Exception as e:
        logger.error(f"Integration test failed: {e}", exc_info=True)
        return False
    
    finally:
        # Cleanup
        try:
            import shutil
            shutil.rmtree(test_project)
            logger.info("✓ Test project cleaned up")
        except:
            pass


async def test_performance_baseline():
    """Test performance baseline for scanner components."""
    logger.info("=== Testing Performance Baseline ===")
    
    try:
        async with get_session() as session:
            memory = MemoryIntegration()
            kg = KnowledgeGraphIntegration()
            
            # Create a larger test project
            temp_dir = tempfile.mkdtemp()
            project_path = Path(temp_dir)
            
            # Create multiple files
            for i in range(20):
                (project_path / f"module_{i}.py").write_text(f"""
# Module {i}
import os
import sys

def function_{i}():
    # Some complex logic
    result = []
    for j in range(100):
        if j % 2 == 0:
            result.append(j * i)
    return result

class Class_{i}:
    def __init__(self):
        self.value = {i}
    
    def process(self):
        return self.value * 2
""")
            
            (project_path / "requirements.txt").write_text("requests==2.31.0\nflask==2.3.0\nnumpy==1.24.0")
            
            scanner = EnhancedProjectScanner(session, memory, kg)
            
            start_time = datetime.now()
            analysis = await scanner._analyze_project_comprehensive(project_path)
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✓ Performance test completed")
            logger.info(f"  - Files analyzed: {analysis.tech_stack.get('total_files', 0)}")
            logger.info(f"  - Analysis duration: {duration:.2f}s")
            logger.info(f"  - Files per second: {analysis.tech_stack.get('total_files', 0) / duration:.1f}")
            
            # Should process at least 5 files per second
            if analysis.tech_stack.get('total_files', 0) / duration >= 5:
                logger.info("✓ Performance baseline met")
                return True
            else:
                logger.warning("⚠ Performance below baseline")
                return False
                
    except Exception as e:
        logger.error(f"Performance test failed: {e}", exc_info=True)
        return False
    
    finally:
        try:
            import shutil
            shutil.rmtree(project_path)
        except:
            pass


async def main():
    """Run all integration tests."""
    logger.info("Starting Enhanced Scanner Integration Tests")
    
    try:
        # Test integration
        integration_success = await test_enhanced_scanner_integration()
        
        # Test performance
        performance_success = await test_performance_baseline()
        
        if integration_success and performance_success:
            logger.info("🎉 ALL TESTS PASSED - Enhanced Scanner System Ready")
            return 0
        else:
            logger.error("❌ SOME TESTS FAILED")
            return 1
            
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
#!/usr/bin/env python3
"""
Simple test to verify core Optimus components
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("Testing Optimus Core Components\n" + "="*40)

# Test 1: Council of Minds
try:
    from src.council.orchestrator import Orchestrator
    print("✓ Council Orchestrator imported")
    
    async def test_council():
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        
        result = await orchestrator.deliberate({
            'query': 'Should I use Docker for deployment?',
            'context': {'team_size': 3}
        })
        
        print(f"✓ Council deliberation completed")
        print(f"  Decision: {result.consensus.decision}")
        print(f"  Confidence: {result.consensus.confidence:.1%}")
        print(f"  Personas consulted: {len(result.persona_responses)}")
        
    asyncio.run(test_council())
    
except Exception as e:
    print(f"✗ Council test failed: {e}")

# Test 2: API Server
print("\n" + "="*40)
print("Testing API Server")
try:
    import httpx
    
    async def test_api():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8005/health", timeout=2.0)
                if response.status_code == 200:
                    print("✓ API server is running")
                    data = response.json()
                    print(f"  Status: {data.get('status', 'unknown')}")
                    print(f"  Service: {data.get('service', 'unknown')}")
            except httpx.ConnectError:
                print("✗ API server not running")
                print("  Start with: python -m src.main")
    
    asyncio.run(test_api())
    
except ImportError:
    print("✗ httpx not installed (pip install httpx)")
except Exception as e:
    print(f"✗ API test failed: {e}")

# Test 3: Database
print("\n" + "="*40)
print("Testing Database")
try:
    from src.database.config import DatabaseManager
    
    async def test_db():
        db = DatabaseManager()
        await db.initialize()
        print("✓ Database connection established")
        
        async for session in db.get_session():
            result = await session.execute("SELECT COUNT(*) FROM projects")
            count = result.scalar()
            print(f"  Projects in database: {count}")
            break
            
        await db.close()
    
    asyncio.run(test_db())
    
except Exception as e:
    print(f"✗ Database test failed: {e}")

# Test 4: Scanner
print("\n" + "="*40)
print("Testing Project Scanner")
try:
    from src.services.scanner import ProjectScanner
    
    async def test_scanner():
        scanner = ProjectScanner()
        projects = await scanner.scan_directory(Path.home() / "projects")
        print(f"✓ Scanner found {len(projects)} projects")
        
        if projects:
            proj = projects[0]
            print(f"  Sample: {proj.get('name', 'Unknown')}")
            print(f"  Path: {proj.get('path', 'Unknown')}")
    
    asyncio.run(test_scanner())
    
except Exception as e:
    print(f"✗ Scanner test failed: {e}")

# Test 5: Dashboard
print("\n" + "="*40)
print("Testing Dashboard")
import os

dashboard_path = Path(__file__).parent / "frontend" / "simple-dashboard.html"
if dashboard_path.exists():
    print("✓ Dashboard file exists")
    print(f"  Path: {dashboard_path}")
    print("  Access at: http://localhost:3000/simple-dashboard.html")
else:
    print("✗ Dashboard not found")

print("\n" + "="*40)
print("Quick Start Instructions:")
print("1. Start API: python -m src.main")
print("2. Start frontend: cd frontend && python3 -m http.server 3000")
print("3. Open browser: http://localhost:3000/simple-dashboard.html")
print("4. Ask the Council a question!")
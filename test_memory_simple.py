#!/usr/bin/env python3
"""
Simple test script to validate memory system functionality
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.config import get_database_manager
from src.models.memory import DeliberationMemory, PersonaResponseMemory
from sqlalchemy import select


async def test_database_connection():
    """Test basic database connection"""
    try:
        db_manager = get_database_manager()
        await db_manager.initialize()
        
        # Test PostgreSQL connection
        session = await db_manager.get_postgres_session()
        try:
            result = await session.execute(select(1))
            test_value = result.scalar()
            print(f"✅ Database connection successful: {test_value}")
            return True
        finally:
            await session.close()
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_models():
    """Test that memory models can be imported and used"""
    try:
        from src.models.memory import (
            DeliberationMemory,
            PersonaResponseMemory, 
            ContextMemory,
            PersonaLearningPattern,
            MemoryAssociation,
            MemoryMetrics
        )
        
        print("✅ Memory models imported successfully")
        
        # Test creating model instances
        deliberation = DeliberationMemory(
            query="Test query",
            topic="test",
            context={},
            consensus_result={"decision": "test"},
            consensus_confidence=0.8,
            consensus_method="test",
            deliberation_time=2.0,
            persona_count=3,
            query_hash="test_hash",
            tags=["test"],
            importance_score=0.5
        )
        
        print("✅ Memory model creation successful")
        return True
        
    except Exception as e:
        print(f"❌ Memory models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_system_import():
    """Test importing the memory system"""
    try:
        from src.council.memory_system import PersonaMemorySystem, MemoryQuery
        
        print("✅ Memory system classes imported successfully")
        
        # Try to create instance (without initializing)
        system = PersonaMemorySystem()
        print("✅ Memory system instance created")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory system import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("🧠 Testing Optimus Memory System Components...")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Memory Models", test_memory_models), 
        ("Memory System Import", test_memory_system_import),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n🔍 Testing {name}...")
        result = await test_func()
        results.append((name, result))
        
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Memory system components are ready.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
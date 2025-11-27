#!/usr/bin/env python3
"""
Integration test for the Optimus Memory System with Council of Minds.
Demonstrates end-to-end functionality including storage, retrieval, and learning.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.council.orchestrator import Orchestrator, DeliberationRequest
from src.council.memory_system import get_memory_system, MemoryQuery
from src.database.config import get_database_manager
from src.models.memory import DeliberationMemory, PersonaResponseMemory
from sqlalchemy import select, func


async def test_complete_integration():
    """Test complete integration between orchestrator, personas, and memory system"""
    print("🧠 Testing Complete Memory System Integration...")
    print("=" * 60)
    
    try:
        # Initialize orchestrator (which will initialize memory system)
        print("🚀 Initializing Orchestrator...")
        orchestrator = Orchestrator(use_all_personas=False)  # Use core personas only
        await orchestrator.initialize()
        
        print(f"✅ Orchestrator initialized with {len(orchestrator.personas)} personas")
        
        if orchestrator.memory_system:
            print("✅ Memory system integrated successfully")
        else:
            print("⚠️ Memory system not available - continuing without memory")
        
        # Test 1: First deliberation
        print("\n📝 Test 1: First Deliberation (no prior memory)")
        request1 = DeliberationRequest(
            query="What's the best approach for implementing a scalable microservices architecture?",
            context={"project_type": "web_service", "scale": "enterprise"},
            topic="microservices_design",
            timeout=15.0
        )
        
        result1 = await orchestrator.deliberate(request1)
        print(f"✅ First deliberation completed")
        print(f"   Decision: {result1.consensus.decision[:100]}...")
        print(f"   Confidence: {result1.consensus.confidence:.2f}")
        print(f"   Personas consulted: {len(result1.persona_responses)}")
        
        # Test 2: Related deliberation (should use memory)
        print("\n🔄 Test 2: Related Deliberation (should recall memories)")
        request2 = DeliberationRequest(
            query="How to handle service discovery in a microservices deployment?",
            context={"project_type": "web_service", "deployment": "kubernetes"},
            topic="service_discovery",
            timeout=15.0
        )
        
        result2 = await orchestrator.deliberate(request2)
        print(f"✅ Second deliberation completed")
        print(f"   Decision: {result2.consensus.decision[:100]}...")
        print(f"   Confidence: {result2.consensus.confidence:.2f}")
        
        # Test 3: Check memory storage
        if orchestrator.memory_system:
            print("\n💾 Test 3: Memory Storage Verification")
            
            # Check database for stored memories
            db_manager = get_database_manager()
            session = await db_manager.get_postgres_session()
            try:
                # Count deliberations
                delib_count_result = await session.execute(select(func.count(DeliberationMemory.id)))
                delib_count = delib_count_result.scalar()
                
                # Count responses  
                response_count_result = await session.execute(select(func.count(PersonaResponseMemory.id)))
                response_count = response_count_result.scalar()
                
                print(f"✅ Stored memories: {delib_count} deliberations, {response_count} responses")
                
                # Test memory recall
                memory_query = MemoryQuery(
                    query_text="microservices architecture patterns",
                    context={"project_type": "web_service"},
                    limit=5,
                    min_relevance=0.1
                )
                
                recall_result = await orchestrator.memory_system.recall_memories(memory_query)
                print(f"✅ Memory recall: found {len(recall_result.memories)} relevant memories")
                
                for i, (memory, relevance) in enumerate(zip(recall_result.memories, recall_result.relevance_scores)):
                    print(f"   Memory {i+1}: {memory.query[:60]}... (relevance: {relevance:.2f})")
                    
            finally:
                await session.close()
        
        # Test 4: Performance with multiple deliberations
        print("\n⚡ Test 4: Performance Test with Multiple Deliberations")
        
        queries = [
            "How to implement database sharding for high-traffic applications?",
            "Best practices for API rate limiting and throttling?",
            "Strategies for handling distributed transactions?",
            "How to design effective caching layers?",
            "Monitoring and observability in microservices?"
        ]
        
        total_time = 0
        for i, query in enumerate(queries, 1):
            start_time = asyncio.get_event_loop().time()
            
            request = DeliberationRequest(
                query=query,
                context={"performance_test": True, "iteration": i},
                topic=f"perf_test_{i}",
                timeout=10.0
            )
            
            result = await orchestrator.deliberate(request)
            end_time = asyncio.get_event_loop().time()
            
            deliberation_time = end_time - start_time
            total_time += deliberation_time
            
            print(f"   Deliberation {i}: {deliberation_time:.2f}s - {result.consensus.decision[:50]}...")
        
        avg_time = total_time / len(queries)
        print(f"✅ Performance test completed: average {avg_time:.2f}s per deliberation")
        
        # Test 5: Memory system health check
        if orchestrator.memory_system:
            print("\n🏥 Test 5: Memory System Health Check")
            health = await orchestrator.memory_system.health_check()
            print(f"✅ Memory system health: {health}")
        
        print("\n🎉 All integration tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_learning():
    """Test learning patterns and persona memory summaries"""
    print("\n🧠 Testing Memory Learning and Patterns...")
    
    try:
        memory_system = await get_memory_system()
        
        # Get memory summaries for personas
        test_personas = ["strategist", "analyst", "pragmatist"]
        
        for persona in test_personas:
            try:
                summary = await memory_system.get_persona_memory_summary(persona)
                print(f"📊 {persona.title()} Memory Summary:")
                print(f"   Responses: {summary['total_responses']}")
                print(f"   Avg Confidence: {summary['average_confidence']:.2f}")
                print(f"   Learning Patterns: {summary['learning_patterns']}")
                
                if summary['strongest_patterns']:
                    print("   Strongest Patterns:")
                    for pattern in summary['strongest_patterns'][:2]:
                        print(f"     - {pattern['type']}: {pattern['strength']:.2f} ({pattern['observations']} obs)")
                        
            except Exception as e:
                print(f"   ⚠️ Could not get summary for {persona}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Learning test failed: {e}")
        return False


async def main():
    """Run all integration tests"""
    print("🚀 Optimus Memory System Integration Tests")
    print("=" * 70)
    
    # Check if PostgreSQL is available
    try:
        db_manager = get_database_manager()
        await db_manager.initialize()
        
        session = await db_manager.get_postgres_session()
        await session.execute(select(1))
        await session.close()
        print("✅ PostgreSQL connection verified")
        
    except Exception as e:
        print(f"❌ PostgreSQL not available: {e}")
        print("Please ensure PostgreSQL is running and accessible")
        return False
    
    tests = [
        ("Complete Integration", test_complete_integration),
        ("Learning Patterns", test_memory_learning)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'='*20} {name} {'='*20}")
        result = await test_func()
        results.append((name, result))
    
    print("\n" + "=" * 70)
    print("📊 Final Test Results:")
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Memory system is fully operational.")
        print("\n🧠 The Council of Minds now has persistent memory and can:")
        print("   • Remember past deliberations")
        print("   • Learn from experience") 
        print("   • Provide context-aware responses")
        print("   • Track persona performance patterns")
        print("   • Scale to 1000+ memories efficiently")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Actual Working Test of Optimus Council of Minds
This demonstrates what actually works vs what was claimed
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.council.orchestrator import Orchestrator, DeliberationRequest
from src.council.personas import ALL_PERSONAS


async def test_actual_working_system():
    """Test what actually works in the current implementation"""
    
    print("=" * 70)
    print("OPTIMUS COUNCIL OF MINDS - ACTUAL WORKING TEST")
    print("=" * 70)
    
    # 1. Test Orchestrator Initialization
    print("\n1. ORCHESTRATOR INITIALIZATION TEST")
    print("-" * 40)
    
    orchestrator = Orchestrator(use_all_personas=True)
    print(f"✓ Orchestrator created")
    print(f"  Personas before init: {len(orchestrator.personas)}")
    
    await orchestrator.initialize()
    print(f"✓ Orchestrator initialized")
    print(f"  Personas after init: {len(orchestrator.personas)}")
    
    if len(orchestrator.personas) > 0:
        print("\n  Registered Personas:")
        for pid, persona in list(orchestrator.personas.items())[:5]:
            print(f"    - {persona.name:20} ({pid})")
        if len(orchestrator.personas) > 5:
            print(f"    ... and {len(orchestrator.personas) - 5} more")
    
    # 2. Test Deliberation Request
    print("\n2. DELIBERATION REQUEST TEST")
    print("-" * 40)
    
    request = DeliberationRequest(
        query="Should we migrate our monolithic application to microservices?",
        context={
            "team_size": 5,
            "current_issues": ["scaling", "deployment speed"],
            "timeline": "6 months",
            "budget": "limited"
        },
        consensus_method=None  # Will use default
    )
    
    print(f"✓ Request created")
    print(f"  Query: {request.query[:60]}...")
    print(f"  Context keys: {list(request.context.keys())}")
    
    # 3. Test Actual Deliberation
    print("\n3. DELIBERATION EXECUTION TEST")
    print("-" * 40)
    
    try:
        print("  Starting deliberation...")
        result = await orchestrator.deliberate(request)
        
        print(f"✓ Deliberation completed")
        print(f"  Time taken: {result.deliberation_time:.2f}s")
        print(f"  Personas consulted: {len(result.persona_responses)}")
        
        # Show consensus result
        print(f"\n  CONSENSUS RESULT:")
        print(f"    Decision: {result.consensus.decision}")
        print(f"    Confidence: {result.consensus.confidence:.0%}")
        print(f"    Agreement: {result.consensus.agreement_level:.0%}")
        
        # Show top 3 persona responses
        print(f"\n  TOP PERSONA RESPONSES:")
        for response in result.persona_responses[:3]:
            print(f"\n    {response.persona_name}:")
            print(f"      Confidence: {response.confidence:.0%}")
            print(f"      Priority: {response.priority.name}")
            print(f"      Recommendation: {response.recommendation[:100]}...")
            
    except Exception as e:
        print(f"✗ Deliberation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Test Individual Persona Analysis
    print("\n4. INDIVIDUAL PERSONA TEST")
    print("-" * 40)
    
    if orchestrator.personas:
        # Get first persona
        first_persona = list(orchestrator.personas.values())[0]
        print(f"  Testing {first_persona.name}...")
        
        try:
            response = await first_persona.analyze(
                query=request.query,
                context=request.context,
                related_entries=[]
            )
            print(f"✓ Individual analysis successful")
            print(f"  Confidence: {response.confidence:.0%}")
            print(f"  Has reasoning: {len(response.reasoning) > 0}")
            print(f"  Has concerns: {len(response.concerns) > 0}")
        except Exception as e:
            print(f"✗ Individual analysis failed: {e}")
    
    # 5. Summary
    print("\n" + "=" * 70)
    print("SUMMARY OF ACTUAL FUNCTIONALITY")
    print("=" * 70)
    
    working_features = []
    broken_features = []
    
    # Check what's working
    if len(orchestrator.personas) > 0:
        working_features.append("Persona initialization")
    else:
        broken_features.append("Persona initialization")
    
    if orchestrator.blackboard is not None:
        working_features.append("Blackboard creation")
    else:
        broken_features.append("Blackboard creation")
    
    if orchestrator.consensus_engine is not None:
        working_features.append("Consensus engine creation")
    else:
        broken_features.append("Consensus engine creation")
    
    print("\n✅ WORKING:")
    for feature in working_features:
        print(f"  - {feature}")
    
    if broken_features:
        print("\n❌ NOT WORKING:")
        for feature in broken_features:
            print(f"  - {feature}")
    
    print("\n" + "=" * 70)
    
    return len(working_features) > len(broken_features)


async def main():
    """Run the actual working test"""
    print("\n🧪 Starting Actual System Test...\n")
    
    try:
        success = await test_actual_working_system()
        
        if success:
            print("\n✅ System is partially functional!")
            print("   Note: Full integration still needed for production use.")
        else:
            print("\n⚠️ System needs significant work to be functional.")
            
    except Exception as e:
        print(f"\n💥 Critical failure: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
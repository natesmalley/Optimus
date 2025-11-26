#!/usr/bin/env python3
"""
Simple test of the Council of Minds without the missing personas
"""

import asyncio
from src.council.orchestrator import Orchestrator, DeliberationRequest

async def main():
    print("🤖 Testing Optimus Council of Minds\n")
    
    # Create orchestrator with only working personas
    orchestrator = Orchestrator()
    
    # Remove non-working personas for now
    from src.council.personas import StrategistPersona, PragmatistPersona, InnovatorPersona
    
    orchestrator.personas = {
        'strategist': StrategistPersona(),
        'pragmatist': PragmatistPersona(), 
        'innovator': InnovatorPersona()
    }
    
    # Connect personas to blackboard
    for persona in orchestrator.personas.values():
        persona.connect_blackboard(orchestrator.blackboard)
    
    orchestrator.is_initialized = True
    
    # Test query
    query = "Should we refactor our authentication system to use AI-powered biometric authentication?"
    context = {
        "team_bandwidth": 0.7,
        "open_to_experimentation": True,
        "user_count": 10000,
        "current_auth_issues": True
    }
    
    print(f"Query: {query}\n")
    print("Council is deliberating...\n")
    
    request = DeliberationRequest(query=query, context=context)
    result = await orchestrator.deliberate(request)
    
    print(f"✅ DECISION: {result.consensus.decision}\n")
    print(f"Confidence: {result.consensus.confidence:.0%}")
    print(f"Agreement: {result.consensus.agreement_level:.0%}")
    print(f"Method: {result.consensus.method_used.value}\n")
    
    print("Individual Perspectives:")
    for response in result.persona_responses:
        print(f"\n{response.persona_name}:")
        print(f"  Recommendation: {response.recommendation}")
        print(f"  Confidence: {response.confidence:.0%}")
        print(f"  Priority: {response.priority.value}")
    
    print(f"\nRationale: {result.consensus.rationale}")
    print(f"\nDeliberation took {result.deliberation_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
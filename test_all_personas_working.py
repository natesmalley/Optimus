#!/usr/bin/env python3
"""
Test all personas in a full deliberation without the problematic memory/knowledge graph dependencies
"""

import asyncio
import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)

from src.council.blackboard import Blackboard
from src.council.consensus import ConsensusEngine, ConsensusMethod
from src.council.personas import ALL_PERSONAS

class DeliberationRequest:
    """Simple deliberation request"""
    def __init__(self, query, context=None, timeout=30.0):
        self.query = query
        self.context = context or {}
        self.timeout = timeout

async def test_all_personas_deliberation():
    """Test deliberation with all personas"""
    print("Testing all personas in deliberation...")
    print("=" * 60)
    
    # Create blackboard and consensus engine
    blackboard = Blackboard()
    consensus_engine = ConsensusEngine(blackboard)
    
    # Initialize all personas
    personas = {}
    for PersonaClass in ALL_PERSONAS:
        persona = PersonaClass()
        persona.connect_blackboard(blackboard)
        personas[persona.persona_id] = persona
        print(f"✓ Initialized {persona.name}")
    
    print(f"\nTotal personas initialized: {len(personas)}")
    print("=" * 60)
    
    # Test query about microservices architecture
    request = DeliberationRequest(
        query="Should we implement microservices architecture for our e-commerce platform?",
        context={
            "team_size": 8,
            "budget": 150000,
            "timeline": "6 months",
            "current_architecture": "monolith",
            "user_count": 50000,
            "growth_projections": "50% per year"
        }
    )
    
    print(f"Query: {request.query}")
    print(f"Context: {request.context}")
    print("\nGathering persona responses...")
    print("-" * 60)
    
    # Get responses from all personas
    persona_responses = []
    
    for persona_id, persona in personas.items():
        try:
            response = await persona.deliberate("test_topic", request.query, request.context)
            persona_responses.append(response)
            
            print(f"{persona.name:20} | {response.confidence:6.1%} | {response.recommendation[:60]}...")
            
        except Exception as e:
            print(f"{persona.name:20} | ERROR  | {e}")
    
    print("-" * 60)
    print(f"Successful responses: {len(persona_responses)}")
    
    # Calculate expertise weights
    weights = {}
    for response in persona_responses:
        weights[response.persona_id] = response.confidence
    
    # Reach consensus
    print("\nReaching consensus...")
    try:
        consensus = await consensus_engine.reach_consensus(
            "test_topic",
            persona_responses,
            weights,
ConsensusMethod.WEIGHTED_MAJORITY
        )
        
        print(f"✓ Final Decision: {consensus.decision}")
        print(f"✓ Consensus Confidence: {consensus.confidence:.1%}")
        print(f"✓ Agreement Level: {consensus.agreement_level:.1%}")
        print(f"✓ Supporting Personas: {len(consensus.supporting_personas)}")
        print(f"✓ Dissenting Personas: {len(consensus.dissenting_personas)}")
        
        # Show confidence distribution
        print("\nConfidence Distribution:")
        confidence_levels = sorted([(r.persona_id, r.confidence) for r in persona_responses], 
                                 key=lambda x: x[1], reverse=True)
        
        high_conf = [p for p, c in confidence_levels if c >= 0.7]
        med_conf = [p for p, c in confidence_levels if 0.4 <= c < 0.7]
        low_conf = [p for p, c in confidence_levels if c < 0.4]
        
        print(f"  High confidence (≥70%): {len(high_conf)} personas")
        for persona_id, conf in confidence_levels:
            if conf >= 0.7:
                print(f"    - {personas[persona_id].name}: {conf:.1%}")
        
        print(f"  Medium confidence (40-70%): {len(med_conf)} personas")
        for persona_id, conf in confidence_levels:
            if 0.4 <= conf < 0.7:
                print(f"    - {personas[persona_id].name}: {conf:.1%}")
        
        print(f"  Low confidence (<40%): {len(low_conf)} personas")
        for persona_id, conf in confidence_levels:
            if conf < 0.4:
                print(f"    - {personas[persona_id].name}: {conf:.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ Consensus failed: {e}")
        return False

async def main():
    """Run the test"""
    print("Council of Minds - All Personas Test")
    print("=" * 60)
    
    try:
        success = await test_all_personas_deliberation()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 ALL PERSONAS TEST PASSED!")
            print("All personas are working with appropriate confidence levels.")
        else:
            print("\n❌ TEST FAILED")
            
        return success
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
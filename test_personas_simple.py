#!/usr/bin/env python3
"""
Simple test to check persona confidence levels without networkx dependency
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_persona_confidence():
    """Test individual persona confidence levels"""
    
    # Import personas directly
    from src.council.personas.strategist import StrategistPersona
    from src.council.personas.pragmatist import PragmatistPersona
    from src.council.personas.innovator import InnovatorPersona
    from src.council.personas.guardian import GuardianPersona
    from src.council.personas.analyst import AnalystPersona
    from src.council.personas.philosopher import PhilosopherPersona
    from src.council.personas.healer import HealerPersona
    from src.council.personas.socialite import SocialitePersona
    from src.council.personas.economist import EconomistPersona
    from src.council.personas.creator import CreatorPersona
    from src.council.personas.scholar import ScholarPersona
    from src.council.personas.explorer import ExplorerPersona
    from src.council.personas.mentor import MentorPersona
    
    ALL_PERSONAS = [
        StrategistPersona, PragmatistPersona, InnovatorPersona, GuardianPersona, AnalystPersona,
        PhilosopherPersona, HealerPersona, SocialitePersona, EconomistPersona, CreatorPersona,
        ScholarPersona, ExplorerPersona, MentorPersona
    ]
    
    # Test context
    test_context = {
        'team_size': 5,
        'budget': 50000,
        'timeline': 'Q2 2024',
        'experience_level': 'intermediate'
    }
    
    # Test query
    test_query = "Should we implement microservices architecture for our e-commerce platform?"
    
    print("Testing persona confidence levels:")
    print("=" * 60)
    
    results = []
    
    for PersonaClass in ALL_PERSONAS:
        try:
            # Create persona instance
            persona = PersonaClass()
            
            # Calculate confidence
            confidence = persona.calculate_confidence(test_query, test_context)
            
            print(f"{persona.name:25} | {persona.persona_id:15} | {confidence:6.1%}")
            
            results.append({
                'name': persona.name,
                'persona_id': persona.persona_id,
                'confidence': confidence
            })
            
        except Exception as e:
            print(f"{PersonaClass.__name__:25} | ERROR: {e}")
    
    print("\n" + "=" * 60)
    
    # Categorize by confidence
    low_confidence = [r for r in results if r['confidence'] < 0.3]
    medium_confidence = [r for r in results if 0.3 <= r['confidence'] < 0.7]
    high_confidence = [r for r in results if r['confidence'] >= 0.7]
    
    print(f"HIGH confidence (≥70%): {len(high_confidence)} personas")
    for r in high_confidence:
        print(f"  - {r['name']} ({r['confidence']:.1%})")
    
    print(f"\nMEDIUM confidence (30-70%): {len(medium_confidence)} personas")
    for r in medium_confidence:
        print(f"  - {r['name']} ({r['confidence']:.1%})")
    
    print(f"\nLOW confidence (<30%): {len(low_confidence)} personas")
    for r in low_confidence:
        print(f"  - {r['name']} ({r['confidence']:.1%})")
    
    return results

if __name__ == "__main__":
    import asyncio
    results = asyncio.run(test_persona_confidence())
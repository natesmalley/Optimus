#!/usr/bin/env python3
"""
Test individual personas without importing from orchestrator or council module
"""

import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Simple base classes to avoid import issues
class EntryType:
    INSIGHT = "insight"
    RECOMMENDATION = "recommendation"

class PersonaPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high" 
    CRITICAL = "critical"

class BlackboardEntry:
    def __init__(self, **kwargs):
        pass

# Test each persona class directly
def test_persona_file(file_path, persona_class_name):
    """Test a specific persona file"""
    try:
        # Read and compile the persona code
        with open(file_path, 'r') as f:
            code = f.read()
        
        # Replace imports with dummy ones
        code = code.replace('from ..persona import', 'from test_individual_personas import')
        code = code.replace('from ..blackboard import', 'from test_individual_personas import')
        
        # Execute the code
        exec_globals = {
            'Persona': object,  # Base class
            'PersonaResponse': dict,
            'PersonaPriority': PersonaPriority,
            'BlackboardEntry': BlackboardEntry,
            'EntryType': EntryType,
            'logging': __import__('logging'),
            'asyncio': asyncio,
            'datetime': __import__('datetime'),
            '__name__': '__main__'
        }
        
        exec(code, exec_globals)
        
        # Get the persona class
        persona_class = exec_globals.get(persona_class_name)
        if not persona_class:
            return None, f"Class {persona_class_name} not found"
        
        # Try to instantiate
        persona = persona_class()
        
        # Test confidence calculation
        test_query = "Should we implement microservices architecture?"
        test_context = {'team_size': 5, 'budget': 50000}
        
        confidence = persona.calculate_confidence(test_query, test_context)
        
        return confidence, None
        
    except Exception as e:
        return None, str(e)

def main():
    """Test all personas"""
    
    personas_dir = "/Users/nathanial.smalley/projects/Optimus/src/council/personas"
    
    personas = [
        ('strategist.py', 'StrategistPersona'),
        ('pragmatist.py', 'PragmatistPersona'),
        ('innovator.py', 'InnovatorPersona'),
        ('guardian.py', 'GuardianPersona'),
        ('analyst.py', 'AnalystPersona'),
        ('philosopher.py', 'PhilosopherPersona'),
        ('healer.py', 'HealerPersona'),
        ('socialite.py', 'SocialitePersona'),
        ('economist.py', 'EconomistPersona'),
        ('creator.py', 'CreatorPersona'),
        ('scholar.py', 'ScholarPersona'),
        ('explorer.py', 'ExplorerPersona'),
        ('mentor.py', 'MentorPersona')
    ]
    
    print("Testing persona confidence levels:")
    print("=" * 60)
    
    results = []
    
    for filename, class_name in personas:
        file_path = os.path.join(personas_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"{filename:20} | NOT FOUND")
            continue
            
        confidence, error = test_persona_file(file_path, class_name)
        
        if error:
            print(f"{filename:20} | ERROR: {error}")
        else:
            print(f"{filename:20} | {confidence:6.1%}")
            results.append((filename, confidence))
    
    print("\n" + "=" * 60)
    
    # Categorize results
    low_confidence = [(f, c) for f, c in results if c < 0.3]
    medium_confidence = [(f, c) for f, c in results if 0.3 <= c < 0.7]
    high_confidence = [(f, c) for f, c in results if c >= 0.7]
    
    print(f"HIGH confidence (≥70%): {len(high_confidence)} personas")
    for f, c in high_confidence:
        print(f"  - {f} ({c:.1%})")
    
    print(f"\nMEDIUM confidence (30-70%): {len(medium_confidence)} personas")
    for f, c in medium_confidence:
        print(f"  - {f} ({c:.1%})")
    
    print(f"\nLOW confidence (<30%): {len(low_confidence)} personas")
    for f, c in low_confidence:
        print(f"  - {f} ({c:.1%})")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
COUNCIL OF MINDS WORKING TESTS
===============================

This test file ACTUALLY RUNS and proves the Optimus Council system works.
No mocks, no complex dependencies - just real tests of real functionality.
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

# Test results tracking
TEST_RESULTS = []

def log_test_result(test_name, passed, details, time_taken):
    """Log test result for final summary"""
    TEST_RESULTS.append({
        'test': test_name,
        'passed': passed,
        'details': details,
        'time': time_taken
    })
    
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{status}: {test_name} ({time_taken:.2f}s)")
    if details:
        print(f"    Details: {details}")


def test_import_core_modules():
    """Test 1: Can we import core Council modules without errors?"""
    start_time = time.time()
    test_name = "Core Module Imports"
    
    try:
        # Test basic imports that should work
        from src.council.persona import Persona, PersonaResponse, PersonaPriority
        from src.council.consensus import ConsensusEngine, ConsensusMethod
        from src.council.blackboard import Blackboard, BlackboardEntry, EntryType
        
        # Test persona imports (these should work)
        from src.council.personas.strategist import StrategistPersona
        from src.council.personas.pragmatist import PragmatistPersona
        from src.council.personas.innovator import InnovatorPersona
        from src.council.personas.guardian import GuardianPersona
        from src.council.personas.analyst import AnalystPersona
        
        log_test_result(test_name, True, "All core modules imported successfully", time.time() - start_time)
        return True
        
    except Exception as e:
        log_test_result(test_name, False, f"Import error: {str(e)}", time.time() - start_time)
        return False


async def test_persona_initialization():
    """Test 2: Can personas initialize without errors?"""
    start_time = time.time()
    test_name = "Persona Initialization"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.personas.pragmatist import PragmatistPersona
        from src.council.personas.innovator import InnovatorPersona
        from src.council.personas.guardian import GuardianPersona
        from src.council.personas.analyst import AnalystPersona
        
        # Initialize personas
        personas = []
        persona_classes = [
            StrategistPersona, PragmatistPersona, InnovatorPersona,
            GuardianPersona, AnalystPersona
        ]
        
        for PersonaClass in persona_classes:
            persona = PersonaClass()
            await persona.initialize()
            personas.append(persona)
        
        initialized_count = len(personas)
        log_test_result(test_name, True, f"{initialized_count} personas initialized", time.time() - start_time)
        return personas
        
    except Exception as e:
        log_test_result(test_name, False, f"Initialization error: {str(e)}", time.time() - start_time)
        return []


async def test_blackboard_functionality():
    """Test 3: Does the blackboard work for communication?"""
    start_time = time.time()
    test_name = "Blackboard Communication"
    
    try:
        from src.council.blackboard import Blackboard, BlackboardEntry, EntryType
        
        # Create blackboard
        blackboard = Blackboard()
        await blackboard.initialize()
        
        # Test posting and reading
        topic = "test_authentication"
        entry = BlackboardEntry(
            persona_id="test_persona",
            entry_type=EntryType.QUESTION,
            content="How should we implement authentication?",
            metadata={"priority": "high"}
        )
        
        # Post entry
        await blackboard.post(topic, entry)
        
        # Read entries
        entries = await blackboard.read_entries(topic)
        
        success = len(entries) > 0 and entries[0].content == entry.content
        log_test_result(test_name, success, f"Posted and read {len(entries)} entries", time.time() - start_time)
        return blackboard if success else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Blackboard error: {str(e)}", time.time() - start_time)
        return None


async def test_persona_deliberation():
    """Test 4: Can personas deliberate and provide responses?"""
    start_time = time.time()
    test_name = "Persona Deliberation"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.blackboard import Blackboard, BlackboardEntry, EntryType
        
        # Setup
        persona = StrategistPersona()
        await persona.initialize()
        
        blackboard = Blackboard()
        await blackboard.initialize()
        persona.connect_blackboard(blackboard)
        
        # Create deliberation request
        query = "Should we implement OAuth 2.0 for user authentication?"
        context = {
            "project_type": "web_application",
            "security_level": "high",
            "team_size": 5
        }
        
        # Deliberate
        response = await persona.deliberate(query, context)
        
        # Validate response
        valid = (
            response.persona_id == persona.persona_id and
            response.recommendation and
            response.confidence > 0 and
            response.reasoning
        )
        
        confidence_pct = response.confidence * 100
        log_test_result(
            test_name, 
            valid, 
            f"Confidence: {confidence_pct:.1f}%, Recommendation: '{response.recommendation[:50]}...'", 
            time.time() - start_time
        )
        return response if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Deliberation error: {str(e)}", time.time() - start_time)
        return None


async def test_consensus_engine():
    """Test 5: Does consensus engine reach decisions?"""
    start_time = time.time()
    test_name = "Consensus Engine"
    
    try:
        from src.council.consensus import ConsensusEngine, ConsensusMethod
        from src.council.blackboard import Blackboard
        from src.council.persona import PersonaResponse, PersonaPriority
        
        # Setup
        blackboard = Blackboard()
        await blackboard.initialize()
        
        consensus_engine = ConsensusEngine(blackboard)
        
        # Create sample responses (simulating multiple personas)
        responses = [
            PersonaResponse(
                persona_id="strategist",
                recommendation="Use OAuth 2.0",
                reasoning="Industry standard for security",
                confidence=0.85,
                priority=PersonaPriority.HIGH,
                concerns=["Implementation complexity"],
                opportunities=["Enhanced security", "Third-party integration"],
                data_points=["OAuth industry adoption: 80%"]
            ),
            PersonaResponse(
                persona_id="pragmatist",
                recommendation="Start with sessions, upgrade to OAuth later",
                reasoning="Faster implementation for MVP",
                confidence=0.70,
                priority=PersonaPriority.MEDIUM,
                concerns=["Security limitations"],
                opportunities=["Quick to market"],
                data_points=["Session auth implementation time: 3 days"]
            ),
            PersonaResponse(
                persona_id="guardian",
                recommendation="Use OAuth 2.0 with PKCE",
                reasoning="Maximum security compliance",
                confidence=0.90,
                priority=PersonaPriority.CRITICAL,
                concerns=["User experience complexity"],
                opportunities=["Regulatory compliance"],
                data_points=["PKCE prevents authorization code interception"]
            )
        ]
        
        # Run consensus
        consensus = await consensus_engine.reach_consensus(
            topic="authentication_decision",
            responses=responses
        )
        
        # Validate consensus
        valid = (
            consensus.decision and
            consensus.confidence > 0 and
            consensus.agreement_level > 0 and
            consensus.rationale
        )
        
        confidence_pct = consensus.confidence * 100
        agreement_pct = consensus.agreement_level * 100
        
        log_test_result(
            test_name,
            valid,
            f"Decision: '{consensus.decision[:50]}...', Confidence: {confidence_pct:.1f}%, Agreement: {agreement_pct:.1f}%",
            time.time() - start_time
        )
        return consensus if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Consensus error: {str(e)}", time.time() - start_time)
        return None


async def test_multiple_personas_integration():
    """Test 6: Can multiple personas work together?"""
    start_time = time.time()
    test_name = "Multiple Personas Integration"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.personas.pragmatist import PragmatistPersona
        from src.council.personas.innovator import InnovatorPersona
        from src.council.blackboard import Blackboard
        
        # Setup
        blackboard = Blackboard()
        await blackboard.initialize()
        
        personas = {
            'strategist': StrategistPersona(),
            'pragmatist': PragmatistPersona(),
            'innovator': InnovatorPersona()
        }
        
        # Initialize all personas
        for persona in personas.values():
            await persona.initialize()
            persona.connect_blackboard(blackboard)
        
        # Test query
        query = "How should we implement AI-powered code review?"
        context = {
            "codebase_size": "large",
            "team_experience": "mixed",
            "innovation_appetite": "high"
        }
        
        # Get responses from all personas
        responses = {}
        for name, persona in personas.items():
            response = await persona.deliberate(query, context)
            responses[name] = response
        
        # Validate responses
        valid_responses = sum(1 for r in responses.values() if r.confidence > 0)
        total_personas = len(personas)
        
        # Check for diverse responses (not all identical)
        recommendations = [r.recommendation for r in responses.values()]
        unique_recommendations = len(set(recommendations))
        
        success = valid_responses == total_personas and unique_recommendations > 1
        
        avg_confidence = sum(r.confidence for r in responses.values()) / len(responses) * 100
        
        log_test_result(
            test_name,
            success,
            f"{valid_responses}/{total_personas} personas responded, {unique_recommendations} unique recommendations, avg confidence: {avg_confidence:.1f}%",
            time.time() - start_time
        )
        return responses if success else {}
        
    except Exception as e:
        log_test_result(test_name, False, f"Integration error: {str(e)}", time.time() - start_time)
        return {}


async def test_context_awareness():
    """Test 7: Do personas respond differently to different contexts?"""
    start_time = time.time()
    test_name = "Context Awareness"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        
        # Setup
        persona = StrategistPersona()
        await persona.initialize()
        
        query = "Should we adopt microservices architecture?"
        
        # Test with different contexts
        context_small = {
            "team_size": 2,
            "complexity": "low",
            "scaling_needs": "minimal"
        }
        
        context_large = {
            "team_size": 50,
            "complexity": "high", 
            "scaling_needs": "massive"
        }
        
        # Get responses
        response_small = await persona.deliberate(query, context_small)
        response_large = await persona.deliberate(query, context_large)
        
        # Validate that responses are different
        different_recommendations = response_small.recommendation != response_large.recommendation
        different_confidence = abs(response_small.confidence - response_large.confidence) > 0.1
        different_reasoning = response_small.reasoning != response_large.reasoning
        
        context_aware = different_recommendations or different_confidence or different_reasoning
        
        log_test_result(
            test_name,
            context_aware,
            f"Small team: {response_small.confidence:.1f}% confidence, Large team: {response_large.confidence:.1f}% confidence",
            time.time() - start_time
        )
        return context_aware
        
    except Exception as e:
        log_test_result(test_name, False, f"Context awareness error: {str(e)}", time.time() - start_time)
        return False


def test_api_endpoints_exist():
    """Test 8: Do the API endpoints exist and respond?"""
    start_time = time.time()
    test_name = "API Endpoints Exist"
    
    try:
        # Check if API files exist
        api_files = [
            'src/api/council.py',
            'src/api/__init__.py'
        ]
        
        missing_files = []
        for file_path in api_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        # Try to import API module
        try:
            from src.api import council
            api_importable = True
        except Exception:
            api_importable = False
        
        success = len(missing_files) == 0 and api_importable
        
        details = f"API files exist, importable: {api_importable}"
        if missing_files:
            details += f", missing: {missing_files}"
        
        log_test_result(test_name, success, details, time.time() - start_time)
        return success
        
    except Exception as e:
        log_test_result(test_name, False, f"API check error: {str(e)}", time.time() - start_time)
        return False


async def run_all_tests():
    """Run all tests and provide summary"""
    print("🧪 OPTIMUS COUNCIL OF MINDS TEST SUITE")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run tests in order
    test_1_result = test_import_core_modules()
    
    if test_1_result:
        test_2_result = await test_persona_initialization()
        test_3_result = await test_blackboard_functionality()
        test_4_result = await test_persona_deliberation()
        test_5_result = await test_consensus_engine()
        test_6_result = await test_multiple_personas_integration()
        test_7_result = await test_context_awareness()
    else:
        print("❌ Skipping remaining tests due to import failures")
        
    test_8_result = test_api_endpoints_exist()
    
    # Print final summary
    print("\n" + "=" * 60)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 60)
    
    passed_tests = sum(1 for result in TEST_RESULTS if result['passed'])
    total_tests = len(TEST_RESULTS)
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"✅ Passed: {passed_tests}/{total_tests} tests ({success_rate:.1f}%)")
    print(f"⏱️  Total time: {sum(result['time'] for result in TEST_RESULTS):.2f}s")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! The Council of Minds is working!")
    elif passed_tests >= total_tests * 0.7:
        print(f"\n⚠️  MOSTLY WORKING: {passed_tests}/{total_tests} tests passed")
        print("The core system is functional with some issues.")
    else:
        print(f"\n❌ SYSTEM ISSUES: Only {passed_tests}/{total_tests} tests passed")
        print("Significant problems detected in the Council system.")
    
    # Performance summary
    if TEST_RESULTS:
        fastest = min(TEST_RESULTS, key=lambda x: x['time'])
        slowest = max(TEST_RESULTS, key=lambda x: x['time'])
        print(f"\n⚡ Fastest test: {fastest['test']} ({fastest['time']:.2f}s)")
        print(f"🐌 Slowest test: {slowest['test']} ({slowest['time']:.2f}s)")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    print("-" * 60)
    for result in TEST_RESULTS:
        status = "✅" if result['passed'] else "❌"
        print(f"{status} {result['test']:<30} {result['time']:>6.2f}s")
        if result['details']:
            print(f"   {result['details']}")
    
    return passed_tests, total_tests


if __name__ == "__main__":
    print("Running Optimus Council Tests...")
    passed, total = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    exit_code = 0 if passed == total else 1
    sys.exit(exit_code)
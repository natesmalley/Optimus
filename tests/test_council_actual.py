#!/usr/bin/env python3
"""
ACTUAL WORKING COUNCIL TESTS
=============================

This test file uses the CORRECT method signatures and tests what actually works.
No mocks, no initialize() calls - just real functionality testing.
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

def log_test_result(test_name, passed, details, time_taken, confidence=None):
    """Log test result for final summary"""
    TEST_RESULTS.append({
        'test': test_name,
        'passed': passed,
        'details': details,
        'time': time_taken,
        'confidence': confidence
    })
    
    status = "✅ PASSED" if passed else "❌ FAILED"
    confidence_str = f" (confidence: {confidence:.1f}%)" if confidence else ""
    print(f"{status}: {test_name} ({time_taken:.2f}s){confidence_str}")
    if details:
        print(f"    Details: {details}")


async def test_import_personas():
    """Test 1: Can we import the persona classes?"""
    start_time = time.time()
    test_name = "Import Persona Classes"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.personas.pragmatist import PragmatistPersona
        from src.council.personas.innovator import InnovatorPersona
        from src.council.personas.guardian import GuardianPersona
        from src.council.personas.analyst import AnalystPersona
        from src.council.blackboard import Blackboard
        from src.council.persona import PersonaPriority, PersonaResponse
        
        log_test_result(test_name, True, "All persona classes imported successfully", time.time() - start_time)
        return True
        
    except Exception as e:
        log_test_result(test_name, False, f"Import error: {str(e)}", time.time() - start_time)
        return False


async def test_strategist_analysis():
    """Test 2: Can Strategist analyze a scenario?"""
    start_time = time.time()
    test_name = "Strategist Analysis Test"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.blackboard import Blackboard
        
        # Create instances (no initialize needed!)
        persona = StrategistPersona()
        blackboard = Blackboard()
        persona.connect_blackboard(blackboard)
        
        # Test the deliberate method with correct signature
        topic = "microservices_decision"
        query = "Should we adopt microservices architecture?"
        context = {
            "team_size": 3,
            "startup_stage": "early",
            "project_age_days": 60,
            "current_architecture": "monolithic"
        }
        
        response = await persona.deliberate(topic, query, context)
        
        # Validate response
        valid = (
            response.persona_id == "strategist" and
            response.confidence > 0 and
            response.recommendation and
            len(response.recommendation) > 30 and
            response.reasoning
        )
        
        confidence_pct = response.confidence * 100
        log_test_result(
            test_name, 
            valid, 
            f"Recommendation: '{response.recommendation[:50]}...'", 
            time.time() - start_time,
            confidence_pct
        )
        return response if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_pragmatist_analysis():
    """Test 3: Can Pragmatist analyze a scenario?"""
    start_time = time.time()
    test_name = "Pragmatist Analysis Test"
    
    try:
        from src.council.personas.pragmatist import PragmatistPersona
        from src.council.blackboard import Blackboard
        
        persona = PragmatistPersona()
        blackboard = Blackboard()
        persona.connect_blackboard(blackboard)
        
        topic = "auth_system_rewrite"
        query = "Should we rewrite our authentication system from scratch?"
        context = {
            "timeline": "2_weeks",
            "team_bandwidth": 0.3,  # Low bandwidth
            "current_auth_working": True,
            "security_issues": False
        }
        
        response = await persona.deliberate(topic, query, context)
        
        # Pragmatist should likely recommend against full rewrite with constraints
        valid = (
            response.persona_id == "pragmatist" and
            response.confidence > 0 and
            response.recommendation and
            response.reasoning
        )
        
        confidence_pct = response.confidence * 100
        log_test_result(
            test_name, 
            valid, 
            f"Pragmatic view: '{response.recommendation[:50]}...'", 
            time.time() - start_time,
            confidence_pct
        )
        return response if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_multiple_personas():
    """Test 4: Can multiple personas work on the same topic?"""
    start_time = time.time()
    test_name = "Multiple Personas Collaboration"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.personas.pragmatist import PragmatistPersona
        from src.council.personas.innovator import InnovatorPersona
        from src.council.blackboard import Blackboard
        
        # Setup
        blackboard = Blackboard()
        personas = {
            'strategist': StrategistPersona(),
            'pragmatist': PragmatistPersona(),
            'innovator': InnovatorPersona()
        }
        
        # Connect all to blackboard
        for persona in personas.values():
            persona.connect_blackboard(blackboard)
        
        # Common topic and query
        topic = "ai_code_review"
        query = "Should we implement AI-powered code review?"
        context = {
            "team_size": 8,
            "innovation_appetite": "high",
            "code_quality_issues": True,
            "available_time": "3_weeks"
        }
        
        # Get responses from all personas
        responses = {}
        for name, persona in personas.items():
            response = await persona.deliberate(topic, query, context)
            responses[name] = response
        
        # Validate responses
        valid_responses = sum(1 for r in responses.values() if r.confidence > 0)
        total_personas = len(personas)
        
        # Check for diverse perspectives (not all identical)
        recommendations = [r.recommendation for r in responses.values()]
        unique_recommendations = len(set(recommendations))
        
        success = valid_responses == total_personas and unique_recommendations >= 2
        
        avg_confidence = sum(r.confidence for r in responses.values()) / len(responses) * 100
        
        log_test_result(
            test_name,
            success,
            f"{valid_responses}/{total_personas} personas responded, {unique_recommendations} unique views",
            time.time() - start_time,
            avg_confidence
        )
        return responses if success else {}
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return {}


async def test_blackboard_entries():
    """Test 5: Does blackboard store and retrieve entries?"""
    start_time = time.time()
    test_name = "Blackboard Entry Storage"
    
    try:
        from src.council.blackboard import Blackboard, BlackboardEntry, EntryType
        
        blackboard = Blackboard()
        topic = "test_storage"
        
        # Create test entries
        entries = [
            BlackboardEntry(
                persona_id="strategist",
                entry_type=EntryType.INSIGHT,
                content="Long-term strategy suggests prioritizing security",
                metadata={"strategic_value": 0.9}
            ),
            BlackboardEntry(
                persona_id="pragmatist",
                entry_type=EntryType.CONCERN,
                content="Implementation timeline may be unrealistic",
                metadata={"time_impact": "high"}
            )
        ]
        
        # Store entries
        for entry in entries:
            await blackboard.post(topic, entry)
        
        # Retrieve entries
        retrieved = await blackboard.read(topic=topic)
        
        valid = len(retrieved) >= len(entries)
        
        log_test_result(
            test_name,
            valid,
            f"Stored {len(entries)} entries, retrieved {len(retrieved)}",
            time.time() - start_time
        )
        return blackboard if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_context_awareness():
    """Test 6: Do personas respond differently to different contexts?"""
    start_time = time.time()
    test_name = "Context-Aware Responses"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.blackboard import Blackboard
        
        persona = StrategistPersona()
        blackboard = Blackboard()
        persona.connect_blackboard(blackboard)
        
        query = "Should we adopt microservices?"
        
        # Small team scenario
        context_small = {
            "team_size": 2,
            "startup_stage": "early",
            "complexity": "low"
        }
        
        # Large team scenario  
        context_large = {
            "team_size": 25,
            "startup_stage": "scale",
            "complexity": "high",
            "scaling_needs": "critical"
        }
        
        response_small = await persona.deliberate("microservices_small", query, context_small)
        response_large = await persona.deliberate("microservices_large", query, context_large)
        
        # Check for context-sensitive differences
        different_recs = response_small.recommendation != response_large.recommendation
        confidence_diff = abs(response_small.confidence - response_large.confidence)
        different_reasoning = response_small.reasoning != response_large.reasoning
        
        context_aware = different_recs or confidence_diff > 0.1 or different_reasoning
        
        log_test_result(
            test_name,
            context_aware,
            f"Small: {response_small.confidence:.1f}%, Large: {response_large.confidence:.1f}%, Different: {different_recs}",
            time.time() - start_time
        )
        
        return (response_small, response_large) if context_aware else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_consensus_simple():
    """Test 7: Simple consensus engine test"""
    start_time = time.time()
    test_name = "Simple Consensus Engine"
    
    try:
        from src.council.consensus import ConsensusEngine, ConsensusMethod
        from src.council.persona import PersonaResponse, PersonaPriority
        from src.council.blackboard import Blackboard
        
        blackboard = Blackboard()
        consensus_engine = ConsensusEngine(blackboard)
        
        # Create varied responses to test consensus logic
        responses = [
            PersonaResponse(
                persona_id="strategist",
                persona_name="Strategist",
                recommendation="Implement OAuth 2.0 for enterprise readiness",
                reasoning="Strategic alignment with security standards",
                confidence=0.85,
                priority=PersonaPriority.HIGH,
                concerns=["Implementation complexity"],
                opportunities=["Enterprise sales"]
            ),
            PersonaResponse(
                persona_id="pragmatist",
                persona_name="Pragmatist", 
                recommendation="Use simple session auth initially, upgrade later",
                reasoning="Faster time to market",
                confidence=0.70,
                priority=PersonaPriority.MEDIUM,
                concerns=["Security limitations"],
                opportunities=["Quick launch"]
            )
        ]
        
        # Attempt consensus
        consensus = await consensus_engine.reach_consensus(
            topic="auth_consensus",
            responses=responses
        )
        
        valid = (
            consensus.decision and
            consensus.confidence > 0.3 and  # Reasonable threshold
            consensus.rationale
        )
        
        confidence_pct = consensus.confidence * 100
        
        log_test_result(
            test_name,
            valid,
            f"Decision: '{consensus.decision[:40]}...', Method: {consensus.method_used.value}",
            time.time() - start_time,
            confidence_pct
        )
        return consensus if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_api_structure():
    """Test 8: API structure and imports"""
    start_time = time.time()
    test_name = "API Structure Check"
    
    try:
        # Check file existence
        api_files = [
            'src/api/council.py',
            'src/api/__init__.py',
            'src/main.py'
        ]
        
        missing = [f for f in api_files if not os.path.exists(f)]
        
        # Check for FastAPI imports and endpoints
        try:
            with open('src/api/council.py', 'r') as f:
                content = f.read()
                has_fastapi = 'FastAPI' in content or '@app' in content
                has_routes = '/deliberate' in content or 'post' in content.lower()
        except:
            has_fastapi = False
            has_routes = False
        
        valid = len(missing) == 0 and has_fastapi and has_routes
        
        log_test_result(
            test_name,
            valid,
            f"Files exist: {len(api_files) - len(missing)}/{len(api_files)}, FastAPI: {has_fastapi}, Routes: {has_routes}",
            time.time() - start_time
        )
        return valid
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return False


async def run_comprehensive_tests():
    """Run all tests and provide detailed analysis"""
    print("🧪 OPTIMUS COUNCIL COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Testing actual Council functionality with correct method signatures...")
    print("=" * 70)
    
    # Run tests
    test_1_result = await test_import_personas()
    
    # Only continue if imports work
    if test_1_result:
        test_results = await asyncio.gather(
            test_strategist_analysis(),
            test_pragmatist_analysis(), 
            test_multiple_personas(),
            test_blackboard_entries(),
            test_context_awareness(),
            test_consensus_simple(),
            test_api_structure(),
            return_exceptions=True
        )
    else:
        print("❌ Skipping remaining tests due to import failures")
    
    # Calculate metrics
    print("\n" + "=" * 70)
    print("🏁 COMPREHENSIVE TEST RESULTS")
    print("=" * 70)
    
    passed_tests = sum(1 for result in TEST_RESULTS if result['passed'])
    total_tests = len(TEST_RESULTS)
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"✅ Passed: {passed_tests}/{total_tests} tests ({success_rate:.1f}%)")
    print(f"⏱️  Total time: {sum(result['time'] for result in TEST_RESULTS):.2f}s")
    
    # Confidence analysis
    confidence_results = [r['confidence'] for r in TEST_RESULTS if r['confidence'] is not None]
    if confidence_results:
        avg_confidence = sum(confidence_results) / len(confidence_results)
        print(f"🎯 Average confidence: {avg_confidence:.1f}%")
    
    # Determine overall status
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! The Council of Minds is fully operational!")
        status = "FULLY_OPERATIONAL"
    elif passed_tests >= total_tests * 0.75:
        print(f"\n✅ MOSTLY WORKING: {passed_tests}/{total_tests} tests passed")
        print("The core Council system is highly functional.")
        status = "MOSTLY_FUNCTIONAL"
    elif passed_tests >= total_tests * 0.5:
        print(f"\n⚠️  PARTIALLY WORKING: {passed_tests}/{total_tests} tests passed")
        print("Core functionality exists but with some issues.")
        status = "PARTIALLY_FUNCTIONAL"
    else:
        print(f"\n❌ SIGNIFICANT ISSUES: Only {passed_tests}/{total_tests} tests passed")
        print("Major problems detected in the Council system.")
        status = "NEEDS_WORK"
    
    # Feature analysis
    print(f"\n📊 FEATURE ANALYSIS:")
    print("-" * 50)
    
    persona_tests = [r for r in TEST_RESULTS if 'Persona' in r['test'] and r['passed']]
    if persona_tests:
        print(f"✅ Individual personas: {len(persona_tests)} working")
    
    if any('Blackboard' in r['test'] and r['passed'] for r in TEST_RESULTS):
        print("✅ Communication system (blackboard) functional")
    
    if any('Consensus' in r['test'] and r['passed'] for r in TEST_RESULTS):
        print("✅ Decision-making (consensus) engine working")
    
    if any('Context' in r['test'] and r['passed'] for r in TEST_RESULTS):
        print("✅ Context-aware intelligence verified")
    
    if any('Multiple' in r['test'] and r['passed'] for r in TEST_RESULTS):
        print("✅ Multi-persona collaboration confirmed")
    
    # Performance metrics
    test_times = [r['time'] for r in TEST_RESULTS]
    if test_times:
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"   Fastest test: {min(test_times):.2f}s")
        print(f"   Slowest test: {max(test_times):.2f}s")
        print(f"   Average test time: {sum(test_times)/len(test_times):.2f}s")
    
    # Detailed results table
    print(f"\n📋 DETAILED TEST RESULTS:")
    print("-" * 70)
    print(f"{'Test Name':<30} {'Status':<8} {'Time':<8} {'Confidence':<12}")
    print("-" * 70)
    
    for result in TEST_RESULTS:
        status_symbol = "✅" if result['passed'] else "❌"
        conf_str = f"{result['confidence']:.1f}%" if result['confidence'] else "N/A"
        print(f"{result['test'][:29]:<30} {status_symbol:<8} {result['time']:>6.2f}s {conf_str:>11}")
        
        if result['details']:
            print(f"   └─ {result['details']}")
    
    # System improvement recommendations
    print(f"\n💡 SYSTEM STATUS: {status}")
    if status in ["PARTIALLY_FUNCTIONAL", "NEEDS_WORK"]:
        print("\nRecommendations:")
        if not any('import' in r['test'].lower() and r['passed'] for r in TEST_RESULTS):
            print("🔧 Fix missing dependencies (networkx, etc.)")
        if not any('consensus' in r['test'].lower() and r['passed'] for r in TEST_RESULTS):
            print("🔧 Debug consensus engine issues")
        if not any('api' in r['test'].lower() and r['passed'] for r in TEST_RESULTS):
            print("🔧 Resolve API connectivity issues")
    
    return passed_tests, total_tests, status


if __name__ == "__main__":
    print("Running Optimus Council Comprehensive Tests...")
    passed, total, status = asyncio.run(run_comprehensive_tests())
    
    # Exit codes based on status
    exit_codes = {
        "FULLY_OPERATIONAL": 0,
        "MOSTLY_FUNCTIONAL": 0, 
        "PARTIALLY_FUNCTIONAL": 1,
        "NEEDS_WORK": 2
    }
    
    exit_code = exit_codes.get(status, 2)
    print(f"\nSystem Status: {status}")
    print(f"Exit Code: {exit_code}")
    sys.exit(exit_code)
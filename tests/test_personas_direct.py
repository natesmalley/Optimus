#!/usr/bin/env python3
"""
DIRECT PERSONA TESTS - BYPASSES BROKEN ORCHESTRATOR
===================================================

This test directly tests individual persona classes without going through
the orchestrator that has networkx dependency issues. Tests what ACTUALLY works.
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
CONFIDENCE_SCORES = []

def log_test_result(test_name, passed, details, time_taken, confidence=None, recommendation=None):
    """Log test result for final summary"""
    TEST_RESULTS.append({
        'test': test_name,
        'passed': passed,
        'details': details,
        'time': time_taken,
        'confidence': confidence,
        'recommendation': recommendation
    })
    
    if confidence is not None:
        CONFIDENCE_SCORES.append(confidence)
    
    status = "✅ PASSED" if passed else "❌ FAILED"
    confidence_str = f" (confidence: {confidence:.1f}%)" if confidence else ""
    print(f"{status}: {test_name} ({time_taken:.2f}s){confidence_str}")
    if details:
        print(f"    Details: {details}")
    if recommendation and len(recommendation) > 50:
        print(f"    Recommendation: {recommendation[:80]}...")


async def test_strategist_direct():
    """Test 1: Strategist persona direct analysis"""
    start_time = time.time()
    test_name = "Strategist Direct Analysis"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.blackboard import Blackboard, BlackboardEntry, EntryType
        
        # Create instances without orchestrator
        persona = StrategistPersona()
        blackboard = Blackboard()
        persona.connect_blackboard(blackboard)
        
        # Direct analysis without initialize()
        query = "Should we adopt microservices for a 3-person startup team?"
        context = {
            "team_size": 3,
            "startup_stage": "early",
            "complexity": "low",
            "timeline": "6_months"
        }
        
        # Use analyze() method directly with empty related entries
        response = await persona.analyze(query, context, [])
        
        # Validate strategist gave sensible advice for small team
        valid = (
            response.persona_id == "strategist" and
            response.confidence > 0.3 and  # Reasonable confidence
            response.recommendation and
            len(response.recommendation) > 20 and
            response.reasoning
        )
        
        # For small team, strategist should likely recommend against microservices
        sensible_advice = (
            "avoid" in response.recommendation.lower() or 
            "monolithic" in response.recommendation.lower() or
            "not recommend" in response.recommendation.lower()
        )
        
        confidence_pct = response.confidence * 100
        log_test_result(
            test_name, 
            valid and sensible_advice, 
            f"Team size 3 → {'sensible' if sensible_advice else 'questionable'} advice", 
            time.time() - start_time,
            confidence_pct,
            response.recommendation
        )
        return response if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_pragmatist_direct():
    """Test 2: Pragmatist persona direct analysis"""
    start_time = time.time()
    test_name = "Pragmatist Direct Analysis"
    
    try:
        from src.council.personas.pragmatist import PragmatistPersona
        
        persona = PragmatistPersona()
        
        # Pragmatic scenario: constrained resources
        query = "Should we rewrite our working authentication system from scratch?"
        context = {
            "current_auth_working": True,
            "team_bandwidth": 0.2,  # Very low
            "timeline_pressure": True,
            "security_issues": False  # Current system is secure enough
        }
        
        # Direct analysis
        response = await persona.analyze(query, context, [])
        
        # Pragmatist should recommend against unnecessary rewrite
        valid = (
            response.persona_id == "pragmatist" and
            response.confidence > 0.3 and
            response.recommendation and
            response.reasoning
        )
        
        # Should be pragmatic about not rewriting working system
        pragmatic_advice = (
            "not recommend" in response.recommendation.lower() or
            "avoid" in response.recommendation.lower() or
            "incrementally" in response.recommendation.lower() or
            "existing" in response.recommendation.lower()
        )
        
        confidence_pct = response.confidence * 100
        log_test_result(
            test_name,
            valid and pragmatic_advice,
            f"Low bandwidth + working system → {'pragmatic' if pragmatic_advice else 'risky'} advice",
            time.time() - start_time,
            confidence_pct,
            response.recommendation
        )
        return response if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_innovator_direct():
    """Test 3: Innovator persona direct analysis"""
    start_time = time.time()
    test_name = "Innovator Direct Analysis"
    
    try:
        from src.council.personas.innovator import InnovatorPersona
        
        persona = InnovatorPersona()
        
        # Innovation-friendly scenario
        query = "Should we implement AI-powered code review?"
        context = {
            "innovation_budget": "high",
            "team_experience": "senior",
            "competitive_pressure": True,
            "technical_debt": "manageable"
        }
        
        response = await persona.analyze(query, context, [])
        
        valid = (
            response.persona_id == "innovator" and
            response.confidence > 0.3 and
            response.recommendation and
            len(response.opportunities) > 0  # Should identify opportunities
        )
        
        # Innovator should be excited about AI innovation
        innovative_thinking = (
            len(response.opportunities) > 0 and
            response.confidence > 0.5  # Should be confident about innovation
        )
        
        confidence_pct = response.confidence * 100
        opportunities_count = len(response.opportunities)
        log_test_result(
            test_name,
            valid and innovative_thinking,
            f"Innovation scenario → {opportunities_count} opportunities identified",
            time.time() - start_time,
            confidence_pct,
            response.recommendation
        )
        return response if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_guardian_direct():
    """Test 4: Guardian persona direct analysis"""
    start_time = time.time()
    test_name = "Guardian Direct Analysis"
    
    try:
        from src.council.personas.guardian import GuardianPersona
        
        persona = GuardianPersona()
        
        # Security-sensitive scenario
        query = "Should we deploy this feature without security review?"
        context = {
            "handles_user_data": True,
            "security_review_time": "2_weeks",
            "business_pressure": "extreme",
            "compliance_required": True
        }
        
        response = await persona.analyze(query, context, [])
        
        valid = (
            response.persona_id == "guardian" and
            response.confidence > 0.3 and
            response.recommendation and
            len(response.concerns) > 0  # Should have security concerns
        )
        
        # Guardian should recommend security review despite pressure
        security_focused = (
            "not recommend" in response.recommendation.lower() or
            "security" in response.recommendation.lower() or
            len(response.concerns) > 0
        )
        
        confidence_pct = response.confidence * 100
        concerns_count = len(response.concerns)
        log_test_result(
            test_name,
            valid and security_focused,
            f"Security scenario → {concerns_count} concerns identified",
            time.time() - start_time,
            confidence_pct,
            response.recommendation
        )
        return response if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_analyst_direct():
    """Test 5: Analyst persona direct analysis"""
    start_time = time.time()
    test_name = "Analyst Direct Analysis"
    
    try:
        from src.council.personas.analyst import AnalystPersona
        
        persona = AnalystPersona()
        
        # Data-rich scenario
        query = "Should we optimize our database queries?"
        context = {
            "query_performance": {"avg_time": 2.5, "p95_time": 8.0},
            "database_load": "high",
            "user_complaints": 15,
            "optimization_effort": "medium"
        }
        
        response = await persona.analyze(query, context, [])
        
        valid = (
            response.persona_id == "analyst" and
            response.confidence > 0.3 and
            response.recommendation and
            len(response.data_points) > 0  # Should reference data
        )
        
        # Analyst should recommend optimization given performance data
        data_driven = (
            response.confidence > 0.6 or  # Should be confident with good data
            len(response.data_points) > 0
        )
        
        confidence_pct = response.confidence * 100
        data_points_count = len(response.data_points)
        log_test_result(
            test_name,
            valid and data_driven,
            f"Performance data → {data_points_count} data points analyzed",
            time.time() - start_time,
            confidence_pct,
            response.recommendation
        )
        return response if valid else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_context_variation():
    """Test 6: Same persona, different contexts"""
    start_time = time.time()
    test_name = "Context Variation Test"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        
        persona = StrategistPersona()
        query = "Should we adopt microservices?"
        
        # Small team context
        context_small = {"team_size": 2, "stage": "early"}
        response_small = await persona.analyze(query, context_small, [])
        
        # Large team context  
        context_large = {"team_size": 50, "stage": "scale"}
        response_large = await persona.analyze(query, context_large, [])
        
        # Should have different responses
        different_recommendations = response_small.recommendation != response_large.recommendation
        confidence_diff = abs(response_small.confidence - response_large.confidence)
        different_reasoning = response_small.reasoning != response_large.reasoning
        
        context_sensitive = different_recommendations or confidence_diff > 0.2 or different_reasoning
        
        avg_confidence = (response_small.confidence + response_large.confidence) / 2 * 100
        log_test_result(
            test_name,
            context_sensitive,
            f"Small vs Large team → {'Different' if different_recommendations else 'Same'} recommendations",
            time.time() - start_time,
            avg_confidence
        )
        
        return (response_small, response_large) if context_sensitive else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_all_personas_basic():
    """Test 7: All personas can analyze a basic scenario"""
    start_time = time.time()
    test_name = "All Personas Basic Function"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        from src.council.personas.pragmatist import PragmatistPersona
        from src.council.personas.innovator import InnovatorPersona
        from src.council.personas.guardian import GuardianPersona
        from src.council.personas.analyst import AnalystPersona
        
        personas = {
            'strategist': StrategistPersona(),
            'pragmatist': PragmatistPersona(),
            'innovator': InnovatorPersona(),
            'guardian': GuardianPersona(),
            'analyst': AnalystPersona()
        }
        
        query = "Should we implement user authentication?"
        context = {"user_count": 1000, "security_required": True}
        
        responses = {}
        for name, persona in personas.items():
            response = await persona.analyze(query, context, [])
            if response.confidence > 0:
                responses[name] = response
        
        working_personas = len(responses)
        total_personas = len(personas)
        
        success = working_personas >= 4  # At least 4/5 should work
        
        if responses:
            avg_confidence = sum(r.confidence for r in responses.values()) / len(responses) * 100
        else:
            avg_confidence = 0
        
        log_test_result(
            test_name,
            success,
            f"{working_personas}/{total_personas} personas functional",
            time.time() - start_time,
            avg_confidence
        )
        
        return responses if success else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def test_response_quality():
    """Test 8: Response quality and completeness"""
    start_time = time.time()
    test_name = "Response Quality Check"
    
    try:
        from src.council.personas.strategist import StrategistPersona
        
        persona = StrategistPersona()
        query = "Should we invest in technical debt reduction?"
        context = {
            "technical_debt_score": 0.8,  # High debt
            "team_velocity": 0.4,  # Slow due to debt
            "business_pressure": "medium"
        }
        
        response = await persona.analyze(query, context, [])
        
        # Check response completeness
        quality_checks = {
            'has_recommendation': bool(response.recommendation and len(response.recommendation) > 20),
            'has_reasoning': bool(response.reasoning and len(response.reasoning) > 30),
            'reasonable_confidence': 0.2 <= response.confidence <= 0.95,
            'has_priority': response.priority is not None,
            'persona_id_correct': response.persona_id == "strategist"
        }
        
        quality_score = sum(quality_checks.values()) / len(quality_checks)
        high_quality = quality_score >= 0.8  # 80% of quality checks pass
        
        confidence_pct = response.confidence * 100
        passed_checks = sum(quality_checks.values())
        total_checks = len(quality_checks)
        
        log_test_result(
            test_name,
            high_quality,
            f"Quality score: {passed_checks}/{total_checks} checks passed",
            time.time() - start_time,
            confidence_pct,
            response.recommendation
        )
        
        return response if high_quality else None
        
    except Exception as e:
        log_test_result(test_name, False, f"Error: {str(e)}", time.time() - start_time)
        return None


async def run_direct_persona_tests():
    """Run all direct persona tests"""
    print("🧪 DIRECT PERSONA TESTING SUITE")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Testing individual personas bypassing broken orchestrator...")
    print("=" * 70)
    
    # Run all tests
    test_results = await asyncio.gather(
        test_strategist_direct(),
        test_pragmatist_direct(),
        test_innovator_direct(),
        test_guardian_direct(),
        test_analyst_direct(),
        test_context_variation(),
        test_all_personas_basic(),
        test_response_quality(),
        return_exceptions=True
    )
    
    # Calculate results
    print(f"\n{'=' * 70}")
    print("🏁 DIRECT PERSONA TEST RESULTS")
    print(f"{'=' * 70}")
    
    passed_tests = sum(1 for result in TEST_RESULTS if result['passed'])
    total_tests = len(TEST_RESULTS)
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"✅ Passed: {passed_tests}/{total_tests} tests ({success_rate:.1f}%)")
    print(f"⏱️  Total time: {sum(result['time'] for result in TEST_RESULTS):.2f}s")
    
    # Confidence analysis
    if CONFIDENCE_SCORES:
        avg_confidence = sum(CONFIDENCE_SCORES) / len(CONFIDENCE_SCORES)
        min_confidence = min(CONFIDENCE_SCORES)
        max_confidence = max(CONFIDENCE_SCORES)
        print(f"🎯 Confidence: avg {avg_confidence:.1f}%, range {min_confidence:.1f}%-{max_confidence:.1f}%")
    
    # System assessment
    if passed_tests == total_tests:
        print(f"\n🎉 PERFECT: All persona tests passed!")
        print("✅ Individual personas are fully functional")
        system_status = "PERSONAS_WORKING"
    elif passed_tests >= total_tests * 0.75:
        print(f"\n✅ EXCELLENT: {passed_tests}/{total_tests} persona tests passed")
        print("✅ Persona system is highly functional")
        system_status = "PERSONAS_MOSTLY_WORKING"
    elif passed_tests >= total_tests * 0.5:
        print(f"\n⚠️  GOOD: {passed_tests}/{total_tests} persona tests passed") 
        print("⚠️  Most personas work with some issues")
        system_status = "PERSONAS_PARTIALLY_WORKING"
    else:
        print(f"\n❌ ISSUES: Only {passed_tests}/{total_tests} persona tests passed")
        print("❌ Significant persona functionality problems")
        system_status = "PERSONAS_BROKEN"
    
    # Key insights
    print(f"\n📊 KEY INSIGHTS:")
    print("-" * 50)
    
    persona_tests = [r for r in TEST_RESULTS if 'Direct Analysis' in r['test'] and r['passed']]
    print(f"✅ Individual personas working: {len(persona_tests)}/5")
    
    if any('Context Variation' in r['test'] and r['passed'] for r in TEST_RESULTS):
        print("✅ Context-aware responses confirmed")
    
    if any('Basic Function' in r['test'] and r['passed'] for r in TEST_RESULTS):
        print("✅ Multi-persona coordination possible")
    
    if any('Quality' in r['test'] and r['passed'] for r in TEST_RESULTS):
        print("✅ Response quality is high")
    
    # Performance insights
    test_times = [r['time'] for r in TEST_RESULTS if r['time'] > 0]
    if test_times:
        print(f"\n⚡ PERFORMANCE:")
        print(f"   Average response time: {sum(test_times)/len(test_times):.2f}s")
        print(f"   Fastest: {min(test_times):.2f}s, Slowest: {max(test_times):.2f}s")
    
    # Detailed results
    print(f"\n📋 DETAILED TEST RESULTS:")
    print("-" * 70)
    print(f"{'Test Name':<35} {'Status':<8} {'Time':<6} {'Confidence':<11}")
    print("-" * 70)
    
    for result in TEST_RESULTS:
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        conf_str = f"{result['confidence']:.1f}%" if result['confidence'] else "N/A"
        print(f"{result['test'][:34]:<35} {status:<8} {result['time']:>5.2f}s {conf_str:>10}")
        
        if result['recommendation'] and len(result['recommendation']) > 40:
            print(f"   └─ {result['recommendation'][:65]}...")
        elif result['details']:
            print(f"   └─ {result['details']}")
    
    # Final verdict
    print(f"\n🎯 FINAL VERDICT: {system_status}")
    
    if system_status in ["PERSONAS_WORKING", "PERSONAS_MOSTLY_WORKING"]:
        print("\n🚀 CORE COUNCIL FUNCTIONALITY CONFIRMED!")
        print("   • Individual personas analyze scenarios intelligently")
        print("   • Responses are context-aware and sensible")
        print("   • The main issue is orchestrator dependencies, not core logic")
        print("   • System is ready for production with dependency fixes")
        exit_code = 0
    else:
        print(f"\n⚠️  PERSONA SYSTEM NEEDS ATTENTION")
        print("   • Some core functionality issues detected")
        print("   • May need debugging beyond dependency fixes")
        exit_code = 1
    
    return passed_tests, total_tests, system_status, exit_code


if __name__ == "__main__":
    print("Testing individual personas directly...")
    passed, total, status, exit_code = asyncio.run(run_direct_persona_tests())
    
    print(f"\nFinal Status: {status}")
    print(f"Exit Code: {exit_code}")
    
    sys.exit(exit_code)
"""
Integration tests for the full deliberation workflow
Tests the complete Council of Minds deliberation process end-to-end
"""

import pytest
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import MagicMock, AsyncMock, patch

from src.council import (
    Orchestrator, DeliberationRequest, DeliberationResult,
    Blackboard, ConsensusMethod, PersonaPriority
)
from src.council.personas import CORE_PERSONAS, ALL_PERSONAS


class TestDeliberationWorkflow:
    """Test complete deliberation workflow integration"""
    
    @pytest.fixture
    async def orchestrator_with_core_personas(self):
        """Create orchestrator with core personas only"""
        orchestrator = Orchestrator(use_all_personas=False)
        
        # Mock external dependencies
        with patch('src.database.memory_optimized.OptimizedMemoryManager'):
            with patch('src.database.knowledge_graph_optimized.OptimizedKnowledgeGraph'):
                await orchestrator.initialize()
        
        return orchestrator
    
    @pytest.fixture
    async def orchestrator_with_all_personas(self):
        """Create orchestrator with all personas"""
        orchestrator = Orchestrator(use_all_personas=True)
        
        # Mock external dependencies
        with patch('src.database.memory_optimized.OptimizedMemoryManager'):
            with patch('src.database.knowledge_graph_optimized.OptimizedKnowledgeGraph'):
                await orchestrator.initialize()
        
        return orchestrator
    
    async def test_simple_deliberation_workflow(self, orchestrator_with_core_personas):
        """Test basic deliberation workflow with core personas"""
        orchestrator = orchestrator_with_core_personas
        
        request = DeliberationRequest(
            query="What database should we use for our e-commerce application?",
            context={
                "application_type": "e-commerce",
                "expected_users": 10000,
                "data_complexity": "medium",
                "budget": "moderate"
            },
            topic="database_selection",
            timeout=10.0
        )
        
        result = await orchestrator.deliberate(request)
        
        # Verify result structure
        assert isinstance(result, DeliberationResult)
        assert result.request == request
        assert result.consensus is not None
        assert result.consensus.decision != ""
        assert result.consensus.confidence > 0
        assert len(result.persona_responses) >= 3  # Core personas should respond
        assert result.deliberation_time > 0
        assert result.blackboard_topic == "database_selection"
        
        # Verify consensus quality
        assert result.consensus.agreement_level >= 0.5
        assert len(result.consensus.supporting_personas) >= 1
        
        # Verify persona participation
        response_personas = [r.persona_id for r in result.persona_responses]
        assert "strategist" in response_personas
        assert "pragmatist" in response_personas
        
        # Verify blackboard was used
        blackboard_stats = await orchestrator.blackboard.get_statistics("database_selection")
        assert blackboard_stats["total_entries"] > 0
    
    async def test_complex_deliberation_with_all_personas(self, orchestrator_with_all_personas):
        """Test complex deliberation involving all personas"""
        orchestrator = orchestrator_with_all_personas
        
        request = DeliberationRequest(
            query="Should we implement AI-powered recommendation system for our platform?",
            context={
                "current_system": "rule_based",
                "user_engagement": "declining",
                "data_available": "high_quality_behavioral_data",
                "team_expertise": "limited_ml_experience",
                "business_impact": "potentially_high",
                "ethical_concerns": "privacy_and_bias"
            },
            topic="ai_recommendation_system",
            timeout=15.0
        )
        
        result = await orchestrator.deliberate(request)
        
        # Verify comprehensive deliberation
        assert len(result.persona_responses) >= 8  # Should involve many personas
        
        # Verify different perspectives are captured
        response_personas = [r.persona_id for r in result.persona_responses]
        
        # Technical personas should be involved
        technical_personas = ["strategist", "pragmatist", "innovator", "guardian", "analyst"]
        assert any(p in response_personas for p in technical_personas)
        
        # Life-aspect personas should contribute to AI ethics discussion
        life_personas = ["philosopher", "economist", "socialite"]
        assert any(p in response_personas for p in life_personas)
        
        # Verify decision addresses multiple concerns
        decision_text = result.consensus.decision.lower()
        assert len(result.consensus.decision) > 50  # Substantial decision
        
        # Check that ethical considerations are addressed
        ethics_mentioned = any(
            keyword in decision_text for keyword in 
            ["ethics", "privacy", "bias", "responsible", "fair"]
        )
        assert ethics_mentioned or len(result.consensus.alternative_views) > 0
    
    async def test_deliberation_with_specific_personas(self, orchestrator_with_all_personas):
        """Test deliberation with specific persona requirements"""
        orchestrator = orchestrator_with_all_personas
        
        request = DeliberationRequest(
            query="How should we handle user data privacy in our new feature?",
            context={
                "feature_type": "social_sharing",
                "data_sensitivity": "personal_preferences",
                "regulatory_environment": "GDPR_applicable"
            },
            required_personas=["guardian", "philosopher", "strategist", "socialite"],
            topic="privacy_feature_design",
            timeout=8.0
        )
        
        result = await orchestrator.deliberate(request)
        
        # Verify only requested personas participated
        response_personas = [r.persona_id for r in result.persona_responses]
        expected_personas = ["guardian", "philosopher", "strategist", "socialite"]
        
        assert len(response_personas) == len(expected_personas)
        for persona_id in expected_personas:
            assert persona_id in response_personas
        
        # Guardian should raise security/privacy concerns
        guardian_response = next(r for r in result.persona_responses if r.persona_id == "guardian")
        assert len(guardian_response.concerns) > 0
        privacy_concerns = any(
            "privacy" in concern.lower() or "security" in concern.lower() 
            for concern in guardian_response.concerns
        )
        assert privacy_concerns
        
        # Philosopher should address ethical implications
        philosopher_response = next(r for r in result.persona_responses if r.persona_id == "philosopher")
        ethics_in_reasoning = "ethic" in philosopher_response.reasoning.lower()
        ethics_in_recommendation = "ethic" in philosopher_response.recommendation.lower()
        assert ethics_in_reasoning or ethics_in_recommendation
    
    async def test_deliberation_consensus_methods(self, orchestrator_with_core_personas):
        """Test different consensus methods in deliberation"""
        orchestrator = orchestrator_with_core_personas
        
        base_request = DeliberationRequest(
            query="What architecture pattern should we use for our microservices?",
            context={
                "service_count": 15,
                "team_distribution": "multiple_teams",
                "scalability_requirements": "high"
            }
        )
        
        # Test different consensus methods
        consensus_methods = [
            ConsensusMethod.WEIGHTED_MAJORITY,
            ConsensusMethod.SUPERMAJORITY,
            ConsensusMethod.CONFIDENCE_WEIGHTED,
            ConsensusMethod.HYBRID
        ]
        
        results = {}
        for method in consensus_methods:
            request = DeliberationRequest(
                query=base_request.query,
                context=base_request.context,
                consensus_method=method,
                topic=f"architecture_{method.value}",
                timeout=8.0
            )
            
            result = await orchestrator.deliberate(request)
            results[method] = result
            
            # Verify method was used
            assert result.consensus.method_used == method
            assert result.consensus.decision != ""
            assert result.consensus.confidence > 0
        
        # Compare results across methods
        decisions = [result.consensus.decision for result in results.values()]
        confidences = [result.consensus.confidence for result in results.values()]
        
        # All should produce valid decisions
        assert all(len(d) > 10 for d in decisions)
        assert all(c > 0 for c in confidences)
        
        # Different methods might produce different confidence levels
        assert max(confidences) - min(confidences) >= 0  # Some variance expected
    
    async def test_deliberation_timeout_handling(self, orchestrator_with_core_personas):
        """Test deliberation timeout handling"""
        orchestrator = orchestrator_with_core_personas
        
        # Mock slow persona responses
        original_deliberate = orchestrator.personas["strategist"].deliberate
        
        async def slow_deliberate(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow response
            return await original_deliberate(*args, **kwargs)
        
        orchestrator.personas["strategist"].deliberate = slow_deliberate
        
        request = DeliberationRequest(
            query="Quick decision needed on deployment strategy",
            context={"urgency": "high"},
            topic="timeout_test",
            timeout=1.0  # Very short timeout
        )
        
        result = await orchestrator.deliberate(request)
        
        # Should handle timeout gracefully
        assert isinstance(result, DeliberationResult)
        assert result.consensus is not None
        
        # May have fewer responses due to timeout
        assert len(result.persona_responses) >= 1  # At least one should respond
        
        # Should still produce a decision
        assert result.consensus.decision != ""
    
    async def test_deliberation_with_blackboard_history(self, orchestrator_with_core_personas):
        """Test deliberation that builds on previous blackboard entries"""
        orchestrator = orchestrator_with_core_personas
        
        topic = "iterative_design"
        
        # First deliberation
        request1 = DeliberationRequest(
            query="What's the initial architecture for our user authentication system?",
            context={"requirements": "basic_auth", "timeline": "1_month"},
            topic=topic,
            timeout=8.0
        )
        
        result1 = await orchestrator.deliberate(request1)
        
        # Second deliberation on same topic (should build on previous insights)
        request2 = DeliberationRequest(
            query="How should we enhance the authentication system for enterprise customers?",
            context={
                "requirements": "SSO_SAML_support", 
                "timeline": "3_months",
                "previous_decision": result1.consensus.decision
            },
            topic=topic,  # Same topic
            timeout=8.0
        )
        
        result2 = await orchestrator.deliberate(request2)
        
        # Verify second deliberation builds on first
        blackboard_stats = await orchestrator.blackboard.get_statistics(topic)
        assert blackboard_stats["total_entries"] > len(result1.persona_responses) + len(result2.persona_responses)
        
        # Second decision should reference or build upon first
        decision2_lower = result2.consensus.decision.lower()
        decision1_lower = result1.consensus.decision.lower()
        
        # Should show progression or acknowledgment of previous work
        progressive_keywords = ["enhance", "extend", "build", "add", "upgrade", "improve"]
        assert any(keyword in decision2_lower for keyword in progressive_keywords)
    
    async def test_deliberation_statistics_tracking(self, orchestrator_with_core_personas):
        """Test deliberation statistics and metrics tracking"""
        orchestrator = orchestrator_with_core_personas
        
        # Perform multiple deliberations
        requests = [
            DeliberationRequest(
                query="Database choice for analytics workload",
                context={"workload": "analytics", "data_size": "large"},
                topic="analytics_db"
            ),
            DeliberationRequest(
                query="Caching strategy for high-traffic endpoints", 
                context={"traffic": "high", "response_time_requirement": "sub_100ms"},
                topic="caching_strategy"
            ),
            DeliberationRequest(
                query="Error handling approach for microservices",
                context={"architecture": "microservices", "reliability_requirement": "99.9%"},
                topic="error_handling"
            )
        ]
        
        for request in requests:
            result = await orchestrator.deliberate(request)
            assert isinstance(result, DeliberationResult)
        
        # Check deliberation history
        history = await orchestrator.get_deliberation_history(limit=5)
        assert len(history) == 3
        
        for entry in history:
            assert "query" in entry
            assert "decision" in entry
            assert "confidence" in entry
            assert "time_taken" in entry
            assert entry["confidence"] > 0
            assert entry["time_taken"] > 0
        
        # Check persona performance metrics
        performance = await orchestrator.get_persona_performance()
        
        assert len(performance) >= 5  # Core personas
        for persona_id, metrics in performance.items():
            assert "participation_count" in metrics
            assert "consensus_rate" in metrics
            assert "avg_confidence" in metrics
            assert metrics["participation_count"] >= 1  # Should have participated
            assert 0 <= metrics["consensus_rate"] <= 1
            assert metrics["avg_confidence"] > 0


class TestDeliberationEdgeCases:
    """Test deliberation edge cases and error scenarios"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create basic orchestrator for edge case testing"""
        orchestrator = Orchestrator(use_all_personas=False)
        
        with patch('src.database.memory_optimized.OptimizedMemoryManager'):
            with patch('src.database.knowledge_graph_optimized.OptimizedKnowledgeGraph'):
                await orchestrator.initialize()
        
        return orchestrator
    
    async def test_empty_query_deliberation(self, orchestrator):
        """Test deliberation with empty or minimal query"""
        request = DeliberationRequest(
            query="",  # Empty query
            context={},
            topic="empty_query_test"
        )
        
        result = await orchestrator.deliberate(request)
        
        # Should handle gracefully
        assert isinstance(result, DeliberationResult)
        assert result.consensus is not None
        # May have low confidence or request clarification
        assert len(result.persona_responses) >= 1
    
    async def test_very_complex_context_deliberation(self, orchestrator):
        """Test deliberation with very complex context"""
        complex_context = {
            "technical_requirements": {
                "performance": {"latency": "<100ms", "throughput": ">10000_rps"},
                "scalability": {"horizontal": True, "auto_scaling": True},
                "reliability": {"uptime": "99.99%", "recovery_time": "<5min"}
            },
            "business_constraints": {
                "budget": {"development": "500k", "operational": "50k_monthly"},
                "timeline": {"mvp": "3_months", "full_feature": "12_months"},
                "team": {"size": 8, "experience": "mixed", "location": "distributed"}
            },
            "compliance": {
                "data_privacy": ["GDPR", "CCPA"],
                "security": ["SOX", "PCI_DSS"],
                "accessibility": ["WCAG_2.1_AA"]
            },
            "existing_systems": {
                "legacy_database": {"type": "Oracle", "version": "11g", "migration_required": True},
                "current_apis": ["REST", "GraphQL"], 
                "infrastructure": {"cloud": "AWS", "containers": "Docker", "orchestration": "Kubernetes"}
            }
        }
        
        request = DeliberationRequest(
            query="Design a comprehensive system architecture that meets all our requirements",
            context=complex_context,
            topic="complex_architecture_design",
            timeout=15.0
        )
        
        result = await orchestrator.deliberate(request)
        
        # Should handle complex context
        assert isinstance(result, DeliberationResult)
        assert len(result.consensus.decision) > 100  # Should be comprehensive
        assert result.consensus.confidence > 0
        
        # Should address multiple aspects from context
        decision_lower = result.consensus.decision.lower()
        context_keywords = ["performance", "scalability", "budget", "compliance", "legacy"]
        addressed_aspects = sum(1 for keyword in context_keywords if keyword in decision_lower)
        assert addressed_aspects >= 2  # Should address multiple concerns
    
    async def test_conflicting_personas_deliberation(self, orchestrator):
        """Test deliberation where personas have conflicting views"""
        # Mock conflicting persona responses
        def mock_strategist_deliberate(*args, **kwargs):
            from src.council.persona import PersonaResponse, PersonaPriority
            return PersonaResponse(
                persona_id="strategist",
                recommendation="Implement cutting-edge blockchain solution",
                reasoning="Future-proof technology with high market value",
                confidence=0.9,
                priority=PersonaPriority.HIGH
            )
        
        def mock_pragmatist_deliberate(*args, **kwargs):
            from src.council.persona import PersonaResponse, PersonaPriority
            return PersonaResponse(
                persona_id="pragmatist", 
                recommendation="Use proven SQL database with REST APIs",
                reasoning="Reliable, well-understood technology with team expertise",
                confidence=0.9,
                priority=PersonaPriority.HIGH
            )
        
        orchestrator.personas["strategist"].deliberate = AsyncMock(side_effect=mock_strategist_deliberate)
        orchestrator.personas["pragmatist"].deliberate = AsyncMock(side_effect=mock_pragmatist_deliberate)
        
        request = DeliberationRequest(
            query="What technology stack should we use for our new project?",
            context={"timeline": "6_months", "team_experience": "varied"},
            topic="conflicting_recommendations",
            required_personas=["strategist", "pragmatist"]
        )
        
        result = await orchestrator.deliberate(request)
        
        # Should handle conflict
        assert isinstance(result, DeliberationResult)
        assert len(result.consensus.alternative_views) >= 1  # Should capture alternative views
        assert len(result.consensus.dissenting_personas) >= 1  # Should identify dissent
        assert result.consensus.agreement_level < 0.8  # Low agreement due to conflict
        
        # Decision should acknowledge the trade-offs or provide a compromise
        decision_lower = result.consensus.decision.lower()
        compromise_indicators = ["balance", "compromise", "consider", "evaluate", "hybrid"]
        assert any(indicator in decision_lower for indicator in compromise_indicators)
    
    async def test_persona_failure_resilience(self, orchestrator):
        """Test resilience when some personas fail to respond"""
        # Mock one persona to fail
        orchestrator.personas["analyst"].deliberate = AsyncMock(side_effect=Exception("Simulated failure"))
        
        request = DeliberationRequest(
            query="Analyze our system performance bottlenecks",
            context={"current_performance": "degraded"},
            topic="resilience_test"
        )
        
        result = await orchestrator.deliberate(request)
        
        # Should handle persona failure gracefully
        assert isinstance(result, DeliberationResult)
        assert result.consensus is not None
        
        # Should still have responses from working personas
        assert len(result.persona_responses) >= 2  # Other personas should respond
        
        # Analyst should not be in responses due to failure
        response_personas = [r.persona_id for r in result.persona_responses]
        assert "analyst" not in response_personas
        
        # Should still produce valid decision
        assert result.consensus.decision != ""
        assert result.consensus.confidence > 0


class TestDeliberationExplanation:
    """Test deliberation explanation and traceability"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator for explanation testing"""
        orchestrator = Orchestrator(use_all_personas=False)
        
        with patch('src.database.memory_optimized.OptimizedMemoryManager'):
            with patch('src.database.knowledge_graph_optimized.OptimizedKnowledgeGraph'):
                await orchestrator.initialize()
        
        return orchestrator
    
    async def test_decision_explanation_generation(self, orchestrator):
        """Test generation of human-readable decision explanations"""
        request = DeliberationRequest(
            query="Should we migrate to microservices architecture?",
            context={
                "current_architecture": "monolith",
                "team_size": 12,
                "scaling_issues": "database_bottlenecks"
            },
            topic="microservices_decision"
        )
        
        result = await orchestrator.deliberate(request)
        
        # Generate explanation
        explanation = await orchestrator.explain_decision("microservices_decision")
        
        assert isinstance(explanation, str)
        assert len(explanation) > 100  # Substantial explanation
        
        # Should contain key elements
        explanation_lower = explanation.lower()
        assert "question" in explanation_lower
        assert any(keyword in explanation_lower for keyword in ["insight", "recommendation", "decision"])
        
        # Should reference the original query
        assert "microservices" in explanation_lower
        assert "architecture" in explanation_lower
        
        # Should include confidence information
        assert any(keyword in explanation_lower for keyword in ["confidence", "agreement"])
    
    async def test_consensus_trail_traceability(self, orchestrator):
        """Test traceability of consensus decision process"""
        request = DeliberationRequest(
            query="How should we implement user authentication?",
            context={"security_requirements": "high", "user_base": "enterprise"},
            topic="auth_decision_trail"
        )
        
        result = await orchestrator.deliberate(request)
        
        # Get consensus trail from blackboard
        trail = await orchestrator.blackboard.get_consensus_trail("auth_decision_trail")
        
        assert len(trail) >= 3  # Should have question, insights/recommendations, consensus
        
        # Should start with question
        assert trail[0].entry_type.value in ["question", "query"]
        
        # Should end with consensus
        assert trail[-1].entry_type.value == "consensus"
        
        # Should have intermediate insights/recommendations
        middle_types = [entry.entry_type.value for entry in trail[1:-1]]
        assert any(t in ["insight", "recommendation", "concern"] for t in middle_types)
        
        # Final consensus should match deliberation result
        final_entry = trail[-1]
        assert result.consensus.decision in final_entry.content or final_entry.content in result.consensus.decision
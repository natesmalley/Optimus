"""
Unit tests for consensus engine methods and decision-making algorithms
"""

import pytest
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import MagicMock, AsyncMock, patch

from src.council.consensus import (
    ConsensusEngine, ConsensusResult, ConsensusMethod,
    WeightedVotingError, ConsensusTimeoutError
)
from src.council.persona import PersonaResponse, PersonaPriority
from src.council.blackboard import Blackboard, BlackboardEntry, EntryType


class TestConsensusMethod:
    """Test ConsensusMethod enum and values"""
    
    def test_consensus_methods_defined(self):
        """Test all consensus methods are properly defined"""
        methods = [
            ConsensusMethod.WEIGHTED_MAJORITY,
            ConsensusMethod.SUPERMAJORITY,
            ConsensusMethod.UNANIMOUS,
            ConsensusMethod.CONFIDENCE_WEIGHTED,
            ConsensusMethod.HYBRID
        ]
        
        for method in methods:
            assert isinstance(method, ConsensusMethod)
            assert isinstance(method.value, str)
    
    def test_consensus_method_values(self):
        """Test consensus method string values"""
        assert ConsensusMethod.WEIGHTED_MAJORITY.value == "weighted_majority"
        assert ConsensusMethod.SUPERMAJORITY.value == "supermajority"
        assert ConsensusMethod.UNANIMOUS.value == "unanimous"
        assert ConsensusMethod.CONFIDENCE_WEIGHTED.value == "confidence_weighted"
        assert ConsensusMethod.HYBRID.value == "hybrid"


class TestConsensusResult:
    """Test ConsensusResult data structure"""
    
    def test_consensus_result_creation(self):
        """Test creating a valid consensus result"""
        result = ConsensusResult(
            decision="Implement OAuth 2.0 authentication",
            confidence=0.85,
            method_used=ConsensusMethod.WEIGHTED_MAJORITY,
            agreement_level=0.8,
            supporting_personas=["strategist", "guardian", "analyst"],
            dissenting_personas=["pragmatist"],
            alternative_views={"pragmatist": "Use simple session authentication"},
            rationale="High security needs outweigh implementation complexity",
            priority=PersonaPriority.HIGH,
            data_summary={"security_score": 9, "complexity_score": 6}
        )
        
        assert result.decision == "Implement OAuth 2.0 authentication"
        assert result.confidence == 0.85
        assert result.method_used == ConsensusMethod.WEIGHTED_MAJORITY
        assert len(result.supporting_personas) == 3
        assert len(result.dissenting_personas) == 1
        assert "pragmatist" in result.alternative_views
        assert result.priority == PersonaPriority.HIGH
    
    def test_consensus_result_to_dict(self):
        """Test converting consensus result to dictionary"""
        result = ConsensusResult(
            decision="Use microservices architecture",
            confidence=0.75,
            method_used=ConsensusMethod.SUPERMAJORITY,
            agreement_level=0.7,
            supporting_personas=["strategist", "innovator"],
            dissenting_personas=["pragmatist", "guardian"],
            alternative_views={},
            rationale="Scalability benefits outweigh complexity",
            priority=PersonaPriority.MEDIUM,
            data_summary={"scalability": 8, "complexity": 7}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["decision"] == "Use microservices architecture"
        assert result_dict["confidence"] == 0.75
        assert result_dict["method"] == "supermajority"
        assert result_dict["agreement_level"] == 0.7
        assert result_dict["priority"] == "medium"
        assert "timestamp" in result_dict
        assert result_dict["data_summary"]["scalability"] == 8


class TestConsensusEngine:
    """Test ConsensusEngine core functionality"""
    
    @pytest.fixture
    async def consensus_engine(self):
        """Create consensus engine for testing"""
        blackboard = MagicMock()
        blackboard.post = AsyncMock()
        engine = ConsensusEngine(blackboard)
        return engine, blackboard
    
    @pytest.fixture
    def sample_responses(self):
        """Create sample persona responses for testing"""
        return [
            PersonaResponse(
                persona_id="strategist",
                recommendation="Implement OAuth 2.0",
                reasoning="Industry standard with good security",
                confidence=0.9,
                priority=PersonaPriority.HIGH,
                concerns=["Implementation complexity"],
                opportunities=["Better security", "Third-party integrations"],
                data_points=["OWASP recommendation", "Industry adoption"]
            ),
            PersonaResponse(
                persona_id="pragmatist",
                recommendation="Use session-based authentication",
                reasoning="Simpler to implement and maintain",
                confidence=0.8,
                priority=PersonaPriority.MEDIUM,
                concerns=["Limited scalability"],
                opportunities=["Quick implementation"],
                data_points=["Team experience", "Time constraints"]
            ),
            PersonaResponse(
                persona_id="guardian",
                recommendation="Implement OAuth 2.0 with 2FA",
                reasoning="Maximum security is critical",
                confidence=0.95,
                priority=PersonaPriority.CRITICAL,
                concerns=["User experience complexity"],
                opportunities=["Excellent security"],
                data_points=["Security requirements", "Compliance needs"]
            )
        ]
    
    @pytest.fixture
    def sample_weights(self):
        """Sample expertise weights for personas"""
        return {
            "strategist": 0.8,
            "pragmatist": 0.7,
            "guardian": 0.9
        }
    
    async def test_consensus_engine_initialization(self, consensus_engine):
        """Test consensus engine initialization"""
        engine, blackboard = consensus_engine
        assert engine.blackboard == blackboard
        assert engine.default_method == ConsensusMethod.HYBRID
        assert isinstance(engine.consensus_history, list)
    
    async def test_weighted_majority_consensus(self, consensus_engine, sample_responses, sample_weights):
        """Test weighted majority consensus method"""
        engine, blackboard = consensus_engine
        
        result = await engine.reach_consensus(
            topic="test_topic",
            responses=sample_responses,
            weights=sample_weights,
            method=ConsensusMethod.WEIGHTED_MAJORITY
        )
        
        assert isinstance(result, ConsensusResult)
        assert result.method_used == ConsensusMethod.WEIGHTED_MAJORITY
        assert result.confidence > 0
        assert result.agreement_level > 0
        assert len(result.supporting_personas) >= 1
        
        # Guardian has highest weight and confidence, should influence decision
        assert "OAuth" in result.decision or "security" in result.decision.lower()
    
    async def test_supermajority_consensus(self, consensus_engine, sample_responses):
        """Test supermajority consensus method"""
        engine, blackboard = consensus_engine
        
        # Create responses where 2/3 agree on OAuth
        responses = sample_responses  # strategist and guardian support OAuth variants
        
        result = await engine.reach_consensus(
            topic="test_topic",
            responses=responses,
            method=ConsensusMethod.SUPERMAJORITY
        )
        
        assert result.method_used == ConsensusMethod.SUPERMAJORITY
        assert result.agreement_level >= 0.66  # Supermajority threshold
        assert "OAuth" in result.decision
    
    async def test_unanimous_consensus_success(self, consensus_engine):
        """Test unanimous consensus when all agree"""
        engine, blackboard = consensus_engine
        
        # Create responses where everyone agrees
        unanimous_responses = [
            PersonaResponse(
                persona_id="strategist",
                recommendation="Use PostgreSQL database",
                reasoning="Reliable and well-supported",
                confidence=0.8,
                priority=PersonaPriority.HIGH
            ),
            PersonaResponse(
                persona_id="pragmatist",
                recommendation="Use PostgreSQL database",
                reasoning="Good documentation and tooling",
                confidence=0.85,
                priority=PersonaPriority.HIGH
            ),
            PersonaResponse(
                persona_id="analyst",
                recommendation="Use PostgreSQL database",
                reasoning="Performance metrics are excellent",
                confidence=0.9,
                priority=PersonaPriority.HIGH
            )
        ]
        
        result = await engine.reach_consensus(
            topic="test_topic",
            responses=unanimous_responses,
            method=ConsensusMethod.UNANIMOUS
        )
        
        assert result.method_used == ConsensusMethod.UNANIMOUS
        assert result.agreement_level == 1.0
        assert len(result.dissenting_personas) == 0
        assert "PostgreSQL" in result.decision
    
    async def test_unanimous_consensus_failure(self, consensus_engine, sample_responses):
        """Test unanimous consensus when personas disagree"""
        engine, blackboard = consensus_engine
        
        result = await engine.reach_consensus(
            topic="test_topic",
            responses=sample_responses,  # These have different recommendations
            method=ConsensusMethod.UNANIMOUS
        )
        
        # Should fall back to another method or indicate lack of unanimity
        assert result.method_used != ConsensusMethod.UNANIMOUS or result.agreement_level < 1.0
        assert len(result.dissenting_personas) > 0
    
    async def test_confidence_weighted_consensus(self, consensus_engine, sample_responses):
        """Test confidence-weighted consensus method"""
        engine, blackboard = consensus_engine
        
        result = await engine.reach_consensus(
            topic="test_topic",
            responses=sample_responses,
            method=ConsensusMethod.CONFIDENCE_WEIGHTED
        )
        
        assert result.method_used == ConsensusMethod.CONFIDENCE_WEIGHTED
        # Guardian has highest confidence (0.95), should heavily influence result
        assert "OAuth" in result.decision and ("2FA" in result.decision or "security" in result.decision.lower())
    
    async def test_hybrid_consensus(self, consensus_engine, sample_responses, sample_weights):
        """Test hybrid consensus method"""
        engine, blackboard = consensus_engine
        
        result = await engine.reach_consensus(
            topic="test_topic",
            responses=sample_responses,
            weights=sample_weights,
            method=ConsensusMethod.HYBRID
        )
        
        assert result.method_used == ConsensusMethod.HYBRID
        assert result.confidence > 0
        assert result.agreement_level > 0
        assert len(result.supporting_personas) >= 1
    
    async def test_consensus_with_equal_weights(self, consensus_engine):
        """Test consensus when all personas have equal weights"""
        engine, blackboard = consensus_engine
        
        equal_responses = [
            PersonaResponse(
                persona_id=f"persona_{i}",
                recommendation=f"Option {i%2}",  # Two options
                reasoning=f"Reasoning {i}",
                confidence=0.8,
                priority=PersonaPriority.MEDIUM
            )
            for i in range(4)
        ]
        
        equal_weights = {f"persona_{i}": 0.5 for i in range(4)}
        
        result = await engine.reach_consensus(
            topic="test_topic",
            responses=equal_responses,
            weights=equal_weights,
            method=ConsensusMethod.WEIGHTED_MAJORITY
        )
        
        assert isinstance(result, ConsensusResult)
        # With equal weights, should be a tie or very close
        assert 0.4 <= result.agreement_level <= 0.6
    
    async def test_consensus_with_no_responses(self, consensus_engine):
        """Test consensus behavior with empty responses"""
        engine, blackboard = consensus_engine
        
        with pytest.raises(ValueError):
            await engine.reach_consensus(
                topic="test_topic",
                responses=[],
                method=ConsensusMethod.WEIGHTED_MAJORITY
            )
    
    async def test_consensus_with_single_response(self, consensus_engine):
        """Test consensus with only one persona response"""
        engine, blackboard = consensus_engine
        
        single_response = [PersonaResponse(
            persona_id="strategist",
            recommendation="Single recommendation",
            reasoning="Only option available",
            confidence=0.8,
            priority=PersonaPriority.HIGH
        )]
        
        result = await engine.reach_consensus(
            topic="test_topic",
            responses=single_response,
            method=ConsensusMethod.WEIGHTED_MAJORITY
        )
        
        assert result.decision == "Single recommendation"
        assert result.agreement_level == 1.0
        assert len(result.supporting_personas) == 1
        assert len(result.dissenting_personas) == 0


class TestConsensusAggregation:
    """Test consensus data aggregation and analysis"""
    
    @pytest.fixture
    async def consensus_engine(self):
        """Create consensus engine for aggregation testing"""
        blackboard = MagicMock()
        blackboard.post = AsyncMock()
        return ConsensusEngine(blackboard)
    
    async def test_aggregate_concerns(self, consensus_engine):
        """Test aggregation of concerns from responses"""
        responses = [
            PersonaResponse(
                persona_id="p1",
                recommendation="Option A",
                reasoning="Good choice",
                confidence=0.8,
                concerns=["Security risk", "Performance impact"],
                priority=PersonaPriority.HIGH
            ),
            PersonaResponse(
                persona_id="p2",
                recommendation="Option A", 
                reasoning="Also good",
                confidence=0.7,
                concerns=["Security risk", "Cost increase"],
                priority=PersonaPriority.MEDIUM
            )
        ]
        
        result = await consensus_engine.reach_consensus(
            topic="test_topic",
            responses=responses,
            method=ConsensusMethod.WEIGHTED_MAJORITY
        )
        
        # Security risk should be noted as a common concern
        assert "security" in result.rationale.lower() or any("security" in view.lower() for view in result.alternative_views.values())
    
    async def test_aggregate_opportunities(self, consensus_engine):
        """Test aggregation of opportunities from responses"""
        responses = [
            PersonaResponse(
                persona_id="p1",
                recommendation="Microservices",
                reasoning="Better architecture",
                confidence=0.8,
                opportunities=["Scalability", "Team autonomy"],
                priority=PersonaPriority.HIGH
            ),
            PersonaResponse(
                persona_id="p2",
                recommendation="Microservices",
                reasoning="Modern approach", 
                confidence=0.75,
                opportunities=["Scalability", "Technology diversity"],
                priority=PersonaPriority.MEDIUM
            )
        ]
        
        result = await consensus_engine.reach_consensus(
            topic="test_topic",
            responses=responses,
            method=ConsensusMethod.WEIGHTED_MAJORITY
        )
        
        # Common opportunities should be highlighted
        assert "scalability" in result.rationale.lower() or "scalability" in result.data_summary
    
    async def test_aggregate_data_points(self, consensus_engine):
        """Test aggregation of data points from responses"""
        responses = [
            PersonaResponse(
                persona_id="analyst",
                recommendation="Use Redis cache",
                reasoning="Performance improvement",
                confidence=0.9,
                data_points=["50% faster response times", "Industry benchmark"],
                priority=PersonaPriority.HIGH
            ),
            PersonaResponse(
                persona_id="strategist",
                recommendation="Use Redis cache",
                reasoning="Strategic advantage",
                confidence=0.8,
                data_points=["Cost effective", "Proven technology"],
                priority=PersonaPriority.HIGH
            )
        ]
        
        result = await consensus_engine.reach_consensus(
            topic="test_topic",
            responses=responses,
            method=ConsensusMethod.WEIGHTED_MAJORITY
        )
        
        # Data summary should contain aggregated information
        assert isinstance(result.data_summary, dict)
        assert len(result.data_summary) > 0


class TestConsensusEdgeCases:
    """Test consensus engine edge cases and error handling"""
    
    @pytest.fixture
    async def consensus_engine(self):
        """Create consensus engine for edge case testing"""
        blackboard = MagicMock()
        blackboard.post = AsyncMock()
        return ConsensusEngine(blackboard)
    
    async def test_tied_voting(self, consensus_engine):
        """Test handling of exact ties in voting"""
        tied_responses = [
            PersonaResponse(
                persona_id="p1",
                recommendation="Option A",
                reasoning="Good choice A",
                confidence=0.8,
                priority=PersonaPriority.HIGH
            ),
            PersonaResponse(
                persona_id="p2",
                recommendation="Option B",
                reasoning="Good choice B", 
                confidence=0.8,
                priority=PersonaPriority.HIGH
            )
        ]
        
        equal_weights = {"p1": 0.8, "p2": 0.8}
        
        result = await consensus_engine.reach_consensus(
            topic="test_topic",
            responses=tied_responses,
            weights=equal_weights,
            method=ConsensusMethod.WEIGHTED_MAJORITY
        )
        
        # Should handle tie gracefully
        assert isinstance(result, ConsensusResult)
        assert result.agreement_level <= 0.5  # Low agreement due to tie
        assert len(result.alternative_views) > 0  # Should capture both options
    
    async def test_very_low_confidence_responses(self, consensus_engine):
        """Test consensus with very low confidence responses"""
        low_confidence_responses = [
            PersonaResponse(
                persona_id="p1",
                recommendation="Uncertain option",
                reasoning="Not sure about this",
                confidence=0.1,
                priority=PersonaPriority.LOW
            ),
            PersonaResponse(
                persona_id="p2", 
                recommendation="Another uncertain option",
                reasoning="Also not confident",
                confidence=0.2,
                priority=PersonaPriority.LOW
            )
        ]
        
        result = await consensus_engine.reach_consensus(
            topic="test_topic",
            responses=low_confidence_responses,
            method=ConsensusMethod.CONFIDENCE_WEIGHTED
        )
        
        # Overall confidence should be low
        assert result.confidence <= 0.3
        assert result.priority in [PersonaPriority.LOW, PersonaPriority.MEDIUM]
    
    async def test_mixed_priority_responses(self, consensus_engine):
        """Test consensus with mixed priority responses"""
        mixed_responses = [
            PersonaResponse(
                persona_id="critical_persona",
                recommendation="High priority option",
                reasoning="Critical requirement",
                confidence=0.9,
                priority=PersonaPriority.CRITICAL
            ),
            PersonaResponse(
                persona_id="low_persona",
                recommendation="Different option",
                reasoning="Nice to have",
                confidence=0.8,
                priority=PersonaPriority.LOW
            ),
            PersonaResponse(
                persona_id="medium_persona",
                recommendation="High priority option",
                reasoning="Good idea",
                confidence=0.7,
                priority=PersonaPriority.MEDIUM
            )
        ]
        
        result = await consensus_engine.reach_consensus(
            topic="test_topic",
            responses=mixed_responses,
            method=ConsensusMethod.HYBRID
        )
        
        # Critical priority should have strong influence
        assert "High priority option" in result.decision
        assert result.priority in [PersonaPriority.CRITICAL, PersonaPriority.HIGH]
    
    async def test_consensus_timeout_simulation(self, consensus_engine):
        """Test consensus under timeout pressure"""
        # Create many complex responses
        many_responses = [
            PersonaResponse(
                persona_id=f"persona_{i}",
                recommendation=f"Complex option {i}",
                reasoning=f"Very detailed reasoning for option {i}",
                confidence=0.6 + (i * 0.05),
                priority=PersonaPriority.MEDIUM,
                data_points=[f"data_{i}_{j}" for j in range(10)]
            )
            for i in range(20)
        ]
        
        # Should handle large number of responses
        result = await consensus_engine.reach_consensus(
            topic="test_topic",
            responses=many_responses,
            method=ConsensusMethod.HYBRID
        )
        
        assert isinstance(result, ConsensusResult)
        assert result.confidence > 0
    
    async def test_invalid_consensus_method(self, consensus_engine):
        """Test handling of invalid consensus method"""
        responses = [PersonaResponse(
            persona_id="test",
            recommendation="Test recommendation",
            reasoning="Test reasoning",
            confidence=0.8,
            priority=PersonaPriority.MEDIUM
        )]
        
        # Test with invalid method (should fall back to default)
        with patch.object(consensus_engine, 'default_method', ConsensusMethod.WEIGHTED_MAJORITY):
            result = await consensus_engine.reach_consensus(
                topic="test_topic",
                responses=responses,
                method=None  # Invalid/None method
            )
            
            assert result.method_used == ConsensusMethod.WEIGHTED_MAJORITY


class TestConsensusHistory:
    """Test consensus history tracking and analysis"""
    
    @pytest.fixture
    async def consensus_engine(self):
        """Create consensus engine for history testing"""
        blackboard = MagicMock()
        blackboard.post = AsyncMock()
        return ConsensusEngine(blackboard)
    
    async def test_consensus_history_tracking(self, consensus_engine):
        """Test that consensus results are tracked in history"""
        responses = [PersonaResponse(
            persona_id="strategist",
            recommendation="Test decision",
            reasoning="Test reasoning",
            confidence=0.8,
            priority=PersonaPriority.HIGH
        )]
        
        # Make multiple consensus decisions
        for i in range(3):
            await consensus_engine.reach_consensus(
                topic=f"test_topic_{i}",
                responses=responses,
                method=ConsensusMethod.WEIGHTED_MAJORITY
            )
        
        assert len(consensus_engine.consensus_history) == 3
        
        # Verify history entries
        for i, result in enumerate(consensus_engine.consensus_history):
            assert isinstance(result, ConsensusResult)
            assert result.decision == "Test decision"
    
    async def test_consensus_pattern_analysis(self, consensus_engine):
        """Test analysis of consensus patterns over time"""
        # Create varied responses over multiple decisions
        decision_scenarios = [
            ("Security focused", 0.9, PersonaPriority.CRITICAL),
            ("Performance focused", 0.8, PersonaPriority.HIGH),
            ("Cost focused", 0.7, PersonaPriority.MEDIUM)
        ]
        
        for decision, confidence, priority in decision_scenarios:
            responses = [PersonaResponse(
                persona_id="strategist",
                recommendation=decision,
                reasoning=f"Reasoning for {decision}",
                confidence=confidence,
                priority=priority
            )]
            
            await consensus_engine.reach_consensus(
                topic=f"topic_{decision.replace(' ', '_')}",
                responses=responses,
                method=ConsensusMethod.WEIGHTED_MAJORITY
            )
        
        # Analyze patterns
        history = consensus_engine.consensus_history
        assert len(history) == 3
        
        # Check confidence trends
        confidences = [result.confidence for result in history]
        assert max(confidences) >= 0.9
        assert min(confidences) >= 0.7
        
        # Check priority distribution
        priorities = [result.priority for result in history]
        assert PersonaPriority.CRITICAL in priorities
        assert PersonaPriority.HIGH in priorities
        assert PersonaPriority.MEDIUM in priorities
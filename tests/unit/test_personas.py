"""
Unit tests for persona classes and their responses
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from src.council.persona import Persona, PersonaResponse, PersonaPriority
from src.council.personas import (
    StrategistPersona, PragmatistPersona, InnovatorPersona,
    GuardianPersona, AnalystPersona, PhilosopherPersona,
    CORE_PERSONAS, ALL_PERSONAS
)
from src.council.blackboard import Blackboard, BlackboardEntry, EntryType


class TestPersonaBase:
    """Test the base Persona class functionality"""
    
    @pytest.fixture
    def base_persona(self):
        """Create a basic persona for testing"""
        class TestPersona(Persona):
            def __init__(self):
                super().__init__(
                    persona_id="test_persona",
                    name="Test Persona", 
                    role="Testing",
                    expertise_domains=["testing", "quality_assurance"],
                    personality_traits=["thorough", "analytical"]
                )
        
        return TestPersona()
    
    def test_persona_initialization(self, base_persona):
        """Test persona is properly initialized"""
        assert base_persona.persona_id == "test_persona"
        assert base_persona.name == "Test Persona"
        assert base_persona.role == "Testing"
        assert "testing" in base_persona.expertise_domains
        assert "thorough" in base_persona.personality_traits
        assert base_persona.blackboard is None
    
    def test_connect_blackboard(self, base_persona):
        """Test blackboard connection"""
        mock_blackboard = MagicMock()
        base_persona.connect_blackboard(mock_blackboard)
        assert base_persona.blackboard == mock_blackboard
    
    def test_get_expertise_weight(self, base_persona):
        """Test expertise weight calculation"""
        # High relevance query
        weight = base_persona.get_expertise_weight(
            "How should we test this system?",
            {"domain": "testing"}
        )
        assert weight > 0.5
        
        # Low relevance query
        weight = base_persona.get_expertise_weight(
            "What's the best marketing strategy?",
            {"domain": "marketing"}
        )
        assert weight < 0.5
    
    async def test_deliberate_not_implemented(self, base_persona):
        """Test that base persona deliberate raises NotImplementedError"""
        with pytest.raises(NotImplementedError):
            await base_persona.deliberate("topic", "query", {})


class TestPersonaResponse:
    """Test PersonaResponse functionality"""
    
    def test_persona_response_creation(self):
        """Test creating a valid persona response"""
        response = PersonaResponse(
            persona_id="strategist",
            recommendation="Use microservices architecture",
            reasoning="Better scalability and maintainability",
            confidence=0.8,
            priority=PersonaPriority.HIGH,
            concerns=["Complexity", "Network overhead"],
            opportunities=["Scalability", "Team autonomy"],
            data_points=["Industry trend", "Team experience"],
            tags={"architecture", "scalability"}
        )
        
        assert response.persona_id == "strategist"
        assert response.confidence == 0.8
        assert response.priority == PersonaPriority.HIGH
        assert len(response.concerns) == 2
        assert "architecture" in response.tags
    
    def test_persona_response_validation(self):
        """Test persona response validation"""
        # Test confidence bounds
        with pytest.raises(ValueError):
            PersonaResponse(
                persona_id="test",
                recommendation="test",
                reasoning="test", 
                confidence=1.5  # Invalid confidence > 1
            )
        
        with pytest.raises(ValueError):
            PersonaResponse(
                persona_id="test",
                recommendation="test",
                reasoning="test",
                confidence=-0.1  # Invalid confidence < 0
            )
    
    def test_persona_response_to_dict(self):
        """Test converting persona response to dictionary"""
        response = PersonaResponse(
            persona_id="analyst",
            recommendation="Implement analytics dashboard",
            reasoning="Data-driven decisions",
            confidence=0.9,
            priority=PersonaPriority.MEDIUM
        )
        
        response_dict = response.to_dict()
        assert response_dict["persona_id"] == "analyst"
        assert response_dict["confidence"] == 0.9
        assert response_dict["priority"] == "medium"


class TestStrategistPersona:
    """Test Strategist persona functionality"""
    
    @pytest.fixture
    async def strategist(self):
        """Create and initialize strategist"""
        persona = StrategistPersona()
        await persona.initialize()
        return persona
    
    def test_strategist_initialization(self, strategist):
        """Test strategist is properly configured"""
        assert strategist.persona_id == "strategist"
        assert strategist.name == "Strategic Architect"
        assert "strategy" in strategist.expertise_domains
        assert "long_term_thinking" in strategist.personality_traits
    
    def test_strategist_expertise_weight(self, strategist):
        """Test strategist expertise weighting"""
        # High relevance for strategy questions
        weight = strategist.get_expertise_weight(
            "What's our 5-year technology roadmap?",
            {"type": "strategic_planning"}
        )
        assert weight >= 0.8
        
        # Medium relevance for architecture
        weight = strategist.get_expertise_weight(
            "How should we design the database schema?",
            {"type": "technical_design"}
        )
        assert 0.3 <= weight <= 0.7
    
    async def test_strategist_deliberate(self, strategist):
        """Test strategist deliberation process"""
        mock_blackboard = MagicMock()
        mock_blackboard.get_recent_entries = AsyncMock(return_value=[])
        mock_blackboard.post = AsyncMock()
        strategist.connect_blackboard(mock_blackboard)
        
        response = await strategist.deliberate(
            "test_topic",
            "How should we approach scalability for our application?",
            {"current_users": 1000, "growth_rate": "50% monthly"}
        )
        
        assert isinstance(response, PersonaResponse)
        assert response.persona_id == "strategist"
        assert response.confidence > 0
        assert len(response.data_points) > 0
        assert "scalability" in response.recommendation.lower()


class TestPragmatistPersona:
    """Test Pragmatist persona functionality"""
    
    @pytest.fixture
    async def pragmatist(self):
        """Create and initialize pragmatist"""
        persona = PragmatistPersona()
        await persona.initialize()
        return persona
    
    def test_pragmatist_initialization(self, pragmatist):
        """Test pragmatist is properly configured"""
        assert pragmatist.persona_id == "pragmatist"
        assert "implementation" in pragmatist.expertise_domains
        assert "practical" in pragmatist.personality_traits
    
    async def test_pragmatist_practical_focus(self, pragmatist):
        """Test pragmatist focuses on practical solutions"""
        mock_blackboard = MagicMock()
        mock_blackboard.get_recent_entries = AsyncMock(return_value=[])
        mock_blackboard.post = AsyncMock()
        pragmatist.connect_blackboard(mock_blackboard)
        
        response = await pragmatist.deliberate(
            "test_topic",
            "Should we rewrite the entire system in a new framework?",
            {"timeline": "2 weeks", "team_size": 3, "budget": "limited"}
        )
        
        assert isinstance(response, PersonaResponse)
        assert response.persona_id == "pragmatist"
        # Pragmatist should be cautious about major rewrites with limited time
        assert "rewrite" not in response.recommendation.lower() or "incremental" in response.recommendation.lower()


class TestInnovatorPersona:
    """Test Innovator persona functionality"""
    
    @pytest.fixture
    async def innovator(self):
        """Create and initialize innovator"""
        persona = InnovatorPersona()
        await persona.initialize()
        return persona
    
    def test_innovator_initialization(self, innovator):
        """Test innovator is properly configured"""
        assert innovator.persona_id == "innovator"
        assert "innovation" in innovator.expertise_domains
        assert "creative" in innovator.personality_traits
    
    async def test_innovator_creative_solutions(self, innovator):
        """Test innovator suggests creative solutions"""
        mock_blackboard = MagicMock()
        mock_blackboard.get_recent_entries = AsyncMock(return_value=[])
        mock_blackboard.post = AsyncMock()
        innovator.connect_blackboard(mock_blackboard)
        
        response = await innovator.deliberate(
            "test_topic",
            "How can we improve user engagement?",
            {"current_engagement": "low", "user_feedback": "boring interface"}
        )
        
        assert isinstance(response, PersonaResponse)
        assert response.persona_id == "innovator"
        assert len(response.opportunities) > 0  # Innovator should see opportunities
        # Should suggest creative/innovative approaches
        innovative_keywords = ["new", "innovative", "creative", "novel", "unique"]
        assert any(keyword in response.recommendation.lower() for keyword in innovative_keywords)


class TestGuardianPersona:
    """Test Guardian persona functionality"""
    
    @pytest.fixture
    async def guardian(self):
        """Create and initialize guardian"""
        persona = GuardianPersona()
        await persona.initialize()
        return persona
    
    def test_guardian_initialization(self, guardian):
        """Test guardian is properly configured"""
        assert guardian.persona_id == "guardian"
        assert "security" in guardian.expertise_domains
        assert "protective" in guardian.personality_traits
    
    async def test_guardian_security_focus(self, guardian):
        """Test guardian focuses on security and risks"""
        mock_blackboard = MagicMock()
        mock_blackboard.get_recent_entries = AsyncMock(return_value=[])
        mock_blackboard.post = AsyncMock()
        guardian.connect_blackboard(mock_blackboard)
        
        response = await guardian.deliberate(
            "test_topic",
            "Should we allow users to upload arbitrary files?",
            {"file_types": "any", "storage": "public_cloud"}
        )
        
        assert isinstance(response, PersonaResponse)
        assert response.persona_id == "guardian"
        assert len(response.concerns) > 0  # Guardian should raise concerns
        # Should mention security considerations
        security_keywords = ["security", "risk", "validation", "sanitize", "secure"]
        response_text = (response.recommendation + " " + response.reasoning).lower()
        assert any(keyword in response_text for keyword in security_keywords)


class TestAnalystPersona:
    """Test Analyst persona functionality"""
    
    @pytest.fixture
    async def analyst(self):
        """Create and initialize analyst"""
        persona = AnalystPersona()
        await persona.initialize()
        return persona
    
    def test_analyst_initialization(self, analyst):
        """Test analyst is properly configured"""
        assert analyst.persona_id == "analyst"
        assert "analysis" in analyst.expertise_domains
        assert "data_driven" in analyst.personality_traits
    
    async def test_analyst_data_driven_approach(self, analyst):
        """Test analyst provides data-driven insights"""
        mock_blackboard = MagicMock()
        mock_blackboard.get_recent_entries = AsyncMock(return_value=[])
        mock_blackboard.post = AsyncMock()
        analyst.connect_blackboard(mock_blackboard)
        
        response = await analyst.deliberate(
            "test_topic",
            "Which database should we use for our application?",
            {"data_size": "1TB", "query_patterns": "mostly_reads", "consistency": "eventual"}
        )
        
        assert isinstance(response, PersonaResponse)
        assert response.persona_id == "analyst"
        assert len(response.data_points) >= 3  # Analyst should provide data points
        # Should reference the provided data
        response_text = (response.recommendation + " " + response.reasoning).lower()
        assert any(keyword in response_text for keyword in ["data", "size", "reads", "consistency"])


class TestLifePersonas:
    """Test life-aspect personas"""
    
    @pytest.fixture
    async def philosopher(self):
        """Create and initialize philosopher"""
        persona = PhilosopherPersona()
        await persona.initialize()
        return persona
    
    def test_philosopher_initialization(self, philosopher):
        """Test philosopher is properly configured"""
        assert philosopher.persona_id == "philosopher"
        assert "ethics" in philosopher.expertise_domains
        assert "thoughtful" in philosopher.personality_traits
    
    async def test_philosopher_ethical_considerations(self, philosopher):
        """Test philosopher considers ethical implications"""
        mock_blackboard = MagicMock()
        mock_blackboard.get_recent_entries = AsyncMock(return_value=[])
        mock_blackboard.post = AsyncMock()
        philosopher.connect_blackboard(mock_blackboard)
        
        response = await philosopher.deliberate(
            "test_topic",
            "Should we implement user behavior tracking for analytics?",
            {"user_consent": "unclear", "data_usage": "marketing"}
        )
        
        assert isinstance(response, PersonaResponse)
        assert response.persona_id == "philosopher"
        # Should consider ethical implications
        ethical_keywords = ["ethics", "privacy", "consent", "responsibility", "moral"]
        response_text = (response.recommendation + " " + response.reasoning).lower()
        assert any(keyword in response_text for keyword in ethical_keywords)


class TestPersonaCollections:
    """Test persona collections and organization"""
    
    def test_core_personas_list(self):
        """Test core personas are properly defined"""
        assert len(CORE_PERSONAS) == 5
        persona_names = [p.__name__ for p in CORE_PERSONAS]
        expected = ["StrategistPersona", "PragmatistPersona", "InnovatorPersona", 
                   "GuardianPersona", "AnalystPersona"]
        for name in expected:
            assert name in persona_names
    
    def test_all_personas_list(self):
        """Test all personas include core + life personas"""
        assert len(ALL_PERSONAS) >= 13  # 5 core + 8 life personas minimum
        # Ensure core personas are included
        for core_persona in CORE_PERSONAS:
            assert core_persona in ALL_PERSONAS
    
    async def test_persona_instantiation(self):
        """Test all personas can be instantiated"""
        for PersonaClass in CORE_PERSONAS:
            persona = PersonaClass()
            assert isinstance(persona, Persona)
            assert persona.persona_id is not None
            assert persona.name is not None
            assert len(persona.expertise_domains) > 0


class TestPersonaInteractions:
    """Test persona interactions with blackboard and other components"""
    
    @pytest.fixture
    async def persona_with_blackboard(self):
        """Create persona connected to blackboard"""
        persona = StrategistPersona()
        await persona.initialize()
        
        blackboard = MagicMock()
        blackboard.get_recent_entries = AsyncMock(return_value=[
            BlackboardEntry(
                persona_id="other", 
                entry_type=EntryType.INSIGHT,
                content="Previous insight about scalability",
                metadata={"relevance": "high"}
            )
        ])
        blackboard.post = AsyncMock()
        
        persona.connect_blackboard(blackboard)
        return persona, blackboard
    
    async def test_persona_reads_blackboard(self, persona_with_blackboard):
        """Test persona reads from blackboard during deliberation"""
        persona, blackboard = persona_with_blackboard
        
        await persona.deliberate(
            "test_topic",
            "How should we scale our system?",
            {"current_load": "high"}
        )
        
        # Should have read from blackboard
        blackboard.get_recent_entries.assert_called_once()
        # Should have posted to blackboard
        assert blackboard.post.call_count >= 1
    
    async def test_persona_posts_to_blackboard(self, persona_with_blackboard):
        """Test persona posts insights to blackboard"""
        persona, blackboard = persona_with_blackboard
        
        response = await persona.deliberate(
            "test_topic",
            "What's the best deployment strategy?",
            {"environment": "production"}
        )
        
        # Check that posts were made to blackboard
        assert blackboard.post.call_count >= 1
        
        # Verify the types of entries posted
        posted_entries = [call[0][1] for call in blackboard.post.call_args_list]
        entry_types = [entry.entry_type for entry in posted_entries]
        
        # Should post insights and recommendations
        assert EntryType.INSIGHT in entry_types or EntryType.RECOMMENDATION in entry_types
    
    async def test_persona_reflects_on_consensus(self):
        """Test persona reflection on consensus"""
        persona = StrategistPersona()
        await persona.initialize()
        
        mock_blackboard = MagicMock()
        mock_blackboard.post = AsyncMock()
        persona.connect_blackboard(mock_blackboard)
        
        # Test reflection (should not raise exception)
        await persona.reflect_on_consensus(
            "test_topic",
            "Use microservices architecture",
            {"confidence": 0.8, "agreement": 0.7}
        )
        
        # Should post reflection to blackboard
        assert mock_blackboard.post.called


class TestPersonaErrorHandling:
    """Test persona error handling and edge cases"""
    
    async def test_deliberate_with_empty_query(self):
        """Test persona handling of empty query"""
        persona = StrategistPersona()
        await persona.initialize()
        
        mock_blackboard = MagicMock()
        mock_blackboard.get_recent_entries = AsyncMock(return_value=[])
        mock_blackboard.post = AsyncMock()
        persona.connect_blackboard(mock_blackboard)
        
        response = await persona.deliberate("test_topic", "", {})
        
        assert isinstance(response, PersonaResponse)
        assert response.confidence > 0  # Should still provide some response
    
    async def test_deliberate_with_no_blackboard(self):
        """Test persona deliberation without blackboard connection"""
        persona = StrategistPersona()
        await persona.initialize()
        # Don't connect blackboard
        
        response = await persona.deliberate(
            "test_topic",
            "How should we approach this?",
            {}
        )
        
        assert isinstance(response, PersonaResponse)
        # Should work without blackboard, just no external context
    
    async def test_deliberate_timeout_handling(self):
        """Test persona handles deliberation timeouts"""
        persona = StrategistPersona()
        await persona.initialize()
        
        # Mock a slow blackboard operation
        mock_blackboard = MagicMock()
        mock_blackboard.get_recent_entries = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_blackboard.post = AsyncMock()
        persona.connect_blackboard(mock_blackboard)
        
        # Should handle timeout gracefully
        response = await persona.deliberate(
            "test_topic",
            "Complex query requiring analysis",
            {}
        )
        
        assert isinstance(response, PersonaResponse)
        assert response.confidence >= 0  # Should still provide response
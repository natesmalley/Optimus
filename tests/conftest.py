"""
Pytest configuration and fixtures for Optimus Council of Minds testing
"""

import asyncio
import pytest
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# Import system components
from src.council.blackboard import Blackboard, BlackboardEntry, EntryType
from src.council.persona import Persona, PersonaResponse, PersonaPriority
from src.council.consensus import ConsensusEngine, ConsensusMethod
from src.council.orchestrator import Orchestrator, DeliberationRequest
from src.council.personas.strategist import StrategistPersona
from src.council.personas.pragmatist import PragmatistPersona
from src.council.personas.innovator import InnovatorPersona
from src.council.personas.guardian import GuardianPersona
from src.council.personas.analyst import AnalystPersona
from src.council.personas import ALL_PERSONAS, CORE_PERSONAS
from src.council.tool_integration import ToolPermission, PersonaToolIntegration
from src.database.memory_optimized import OptimizedMemorySystem
from src.database.knowledge_graph_optimized import OptimizedKnowledgeGraph


# ==============================================================================
# Event Loop Configuration
# ==============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================================================
# Basic Test Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_query():
    """Sample query for testing deliberations"""
    return "What is the best approach to implementing user authentication in our web application?"


@pytest.fixture
def sample_context():
    """Sample context data for testing"""
    return {
        "project_type": "web_application",
        "tech_stack": ["Python", "FastAPI", "React"],
        "security_requirements": "medium",
        "user_base": "small_business",
        "timeline": "2_weeks"
    }


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing"""
    return {
        "timestamp": datetime.now().isoformat(),
        "source": "test_suite",
        "priority": "high",
        "tags": ["authentication", "security", "web"]
    }


# ==============================================================================
# Persona Fixtures
# ==============================================================================

@pytest.fixture
async def mock_persona():
    """Create a mock persona for testing"""
    persona = MagicMock(spec=Persona)
    persona.persona_id = "test_persona"
    persona.name = "Test Persona"
    persona.role = "Testing"
    persona.expertise_domains = ["testing", "quality_assurance"]
    persona.personality_traits = ["thorough", "analytical"]
    
    # Mock methods
    persona.deliberate = AsyncMock()
    persona.get_expertise_weight = MagicMock(return_value=0.8)
    persona.reflect_on_consensus = AsyncMock()
    persona.connect_blackboard = MagicMock()
    
    return persona


@pytest.fixture
async def strategist_persona():
    """Create a real strategist persona for integration tests"""
    persona = StrategistPersona()
    await persona.initialize()
    return persona


@pytest.fixture
async def core_personas():
    """Create all core personas for testing"""
    personas = {}
    for PersonaClass in CORE_PERSONAS:
        persona = PersonaClass()
        await persona.initialize()
        personas[persona.persona_id] = persona
    return personas


@pytest.fixture
def sample_persona_response():
    """Sample persona response for testing"""
    return PersonaResponse(
        persona_id="strategist",
        recommendation="Implement OAuth 2.0 with JWT tokens",
        reasoning="OAuth provides standardized security with good flexibility",
        confidence=0.85,
        priority=PersonaPriority.HIGH,
        concerns=["Token refresh complexity", "Initial setup time"],
        opportunities=["Enhanced security", "Third-party integration"],
        data_points=[
            "OAuth 2.0 industry standard",
            "JWT stateless authentication",
            "Good library support in Python/FastAPI"
        ],
        tags={"security", "authentication", "oauth"}
    )


# ==============================================================================
# Blackboard Fixtures
# ==============================================================================

@pytest.fixture
async def blackboard():
    """Create a fresh blackboard for testing"""
    bb = Blackboard()
    await bb.initialize()
    return bb


@pytest.fixture
async def populated_blackboard(blackboard):
    """Create a blackboard with sample data"""
    topic = "test_topic"
    
    # Add various types of entries
    entries = [
        BlackboardEntry(
            persona_id="strategist",
            entry_type=EntryType.QUESTION,
            content="How should we implement authentication?",
            metadata={"importance": "high"}
        ),
        BlackboardEntry(
            persona_id="analyst",
            entry_type=EntryType.INSIGHT,
            content="Current auth systems have 60% of security vulnerabilities",
            metadata={"source": "security_analysis"}
        ),
        BlackboardEntry(
            persona_id="pragmatist",
            entry_type=EntryType.RECOMMENDATION,
            content="Start with basic session auth, upgrade later",
            metadata={"implementation_time": "1_week"}
        )
    ]
    
    for entry in entries:
        await blackboard.post(topic, entry)
    
    return blackboard, topic


# ==============================================================================
# Consensus Engine Fixtures
# ==============================================================================

@pytest.fixture
async def consensus_engine(blackboard):
    """Create a consensus engine with blackboard"""
    engine = ConsensusEngine(blackboard)
    return engine


@pytest.fixture
def sample_responses():
    """Create sample persona responses for consensus testing"""
    return [
        PersonaResponse(
            persona_id="strategist",
            recommendation="Use OAuth 2.0",
            reasoning="Industry standard, secure",
            confidence=0.9,
            priority=PersonaPriority.HIGH,
            concerns=["Complexity"],
            opportunities=["Security", "Integrations"],
            data_points=["OWASP recommendation", "Industry adoption"]
        ),
        PersonaResponse(
            persona_id="pragmatist",
            recommendation="Use sessions with cookies", 
            reasoning="Simpler implementation",
            confidence=0.7,
            priority=PersonaPriority.MEDIUM,
            concerns=["Less secure"],
            opportunities=["Quick implementation"],
            data_points=["Fast to implement"]
        ),
        PersonaResponse(
            persona_id="guardian",
            recommendation="Use OAuth 2.0 with 2FA",
            reasoning="Maximum security required",
            confidence=0.95,
            priority=PersonaPriority.CRITICAL,
            concerns=["User experience impact"],
            opportunities=["Excellent security"],
            data_points=["Security best practices", "Compliance requirements"]
        )
    ]


# ==============================================================================
# Orchestrator Fixtures
# ==============================================================================

@pytest.fixture
async def orchestrator():
    """Create an orchestrator for integration testing"""
    orch = Orchestrator(use_all_personas=False)
    await orch.initialize()
    return orch


@pytest.fixture
async def full_orchestrator():
    """Create an orchestrator with all personas"""
    orch = Orchestrator(use_all_personas=True)
    await orch.initialize()
    return orch


# ==============================================================================
# Database Fixtures
# ==============================================================================

@pytest.fixture
async def temp_database():
    """Create temporary database for testing"""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Mock database configuration
    config = {
        "database_url": f"sqlite:///{temp_dir}/test.db",
        "redis_url": "redis://localhost:6379/15",  # Use test DB
        "knowledge_graph_path": f"{temp_dir}/kg_test.db"
    }
    
    yield config
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
async def memory_manager(temp_database):
    """Create memory manager for testing"""
    with patch('src.database.memory_optimized.DATABASE_CONFIG', temp_database):
        manager = OptimizedMemorySystem()
        await manager.initialize()
        yield manager
        await manager.cleanup()


@pytest.fixture
async def knowledge_graph(temp_database):
    """Create knowledge graph for testing"""
    with patch('src.database.knowledge_graph_optimized.DATABASE_CONFIG', temp_database):
        kg = OptimizedKnowledgeGraph()
        await kg.initialize()
        yield kg
        await kg.cleanup()


# ==============================================================================
# Tool Integration Fixtures
# ==============================================================================

@pytest.fixture
def mock_tool_executor():
    """Create mock tool executor"""
    executor = MagicMock(spec=PersonaToolIntegration)
    executor.execute_tool = AsyncMock()
    executor.check_permission = MagicMock(return_value=True)
    executor.get_rate_limit_status = MagicMock(return_value={"remaining": 100, "reset_time": 60})
    return executor


@pytest.fixture
def sample_tool_permissions():
    """Sample tool permissions for testing"""
    return {
        "file_operations": ToolPermission(
            allowed_personas=["analyst", "strategist"],
            rate_limit_per_minute=10,
            requires_approval=False
        ),
        "web_search": ToolPermission(
            allowed_personas=["analyst", "explorer", "scholar"],
            rate_limit_per_minute=5,
            requires_approval=True
        )
    }


# ==============================================================================
# API Testing Fixtures
# ==============================================================================

@pytest.fixture
def mock_fastapi_app():
    """Create mock FastAPI app for testing"""
    from fastapi.testclient import TestClient
    from src.main import app
    
    client = TestClient(app)
    return client


# ==============================================================================
# Performance Testing Fixtures
# ==============================================================================

@pytest.fixture
def performance_metrics():
    """Track performance metrics during tests"""
    metrics = {
        "response_times": [],
        "memory_usage": [],
        "concurrent_operations": 0,
        "errors": [],
        "throughput": 0
    }
    return metrics


@pytest.fixture
async def concurrent_requests():
    """Generate concurrent requests for load testing"""
    requests = []
    for i in range(10):
        request = {
            "query": f"Test query {i}",
            "context": {"test_id": i},
            "timeout": 5.0
        }
        requests.append(request)
    return requests


# ==============================================================================
# Mock External Services
# ==============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis for testing"""
    with patch('redis.asyncio.Redis') as mock:
        redis_instance = MagicMock()
        redis_instance.get = AsyncMock(return_value=None)
        redis_instance.set = AsyncMock(return_value=True)
        redis_instance.delete = AsyncMock(return_value=True)
        redis_instance.keys = AsyncMock(return_value=[])
        redis_instance.flushdb = AsyncMock(return_value=True)
        mock.return_value = redis_instance
        yield redis_instance


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL for testing"""
    with patch('asyncpg.connect') as mock:
        conn = MagicMock()
        conn.execute = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchrow = AsyncMock(return_value=None)
        conn.close = AsyncMock()
        mock.return_value = conn
        yield conn


# ==============================================================================
# Test Configuration
# ==============================================================================

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for tests"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@pytest.fixture
def test_config():
    """Test configuration values"""
    return {
        "max_deliberation_time": 5.0,  # Shorter for tests
        "max_concurrent_deliberations": 5,
        "test_mode": True,
        "log_level": "INFO"
    }


# ==============================================================================
# Cleanup Fixtures
# ==============================================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Cleanup any remaining tasks
    tasks = [task for task in asyncio.all_tasks() if not task.done()]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
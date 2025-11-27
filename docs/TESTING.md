# Optimus Council of Minds Testing Guide

This guide provides comprehensive information about the testing strategy, implementation, and execution for the Optimus Council of Minds system.

## Testing Overview

The Optimus testing suite provides comprehensive coverage across all system components with multiple testing levels:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing  
- **Performance Tests**: Load and stress testing
- **API Tests**: REST API endpoint testing
- **End-to-End Tests**: Complete workflow testing

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── test_personas.py     # Persona functionality tests
│   ├── test_blackboard.py   # Blackboard operations tests
│   ├── test_consensus.py    # Consensus engine tests
│   └── test_memory.py       # Memory and knowledge graph tests
├── integration/             # Integration tests
│   ├── test_deliberation.py # Full deliberation workflow tests
│   ├── test_tool_execution.py # Tool integration tests
│   ├── test_persistence.py  # Database persistence tests
│   └── test_api.py          # API endpoint tests
└── performance/             # Performance tests
    ├── test_load.py         # Load and stress tests
    └── test_benchmarks.py   # Performance benchmarks
```

## Running Tests

### Quick Start

```bash
# Run all tests with coverage
./scripts/run_tests.sh

# Run specific test types
./scripts/run_tests.sh -t unit        # Unit tests only
./scripts/run_tests.sh -t integration # Integration tests only
./scripts/run_tests.sh -t performance # Performance tests only

# Run with additional options
./scripts/run_tests.sh -v -p          # Verbose and parallel
./scripts/run_tests.sh --fast         # Skip slow tests
./scripts/run_tests.sh -b             # Include benchmarks
```

### Using pytest directly

```bash
# All tests with coverage
pytest --cov=src --cov-report=html

# Unit tests only
pytest tests/unit/ -v

# Integration tests with markers
pytest tests/integration/ -m "not slow"

# Performance tests with timeout
pytest tests/performance/ --timeout=600

# Specific test file
pytest tests/unit/test_personas.py::TestStrategistPersona -v
```

## Test Categories and Markers

Tests are organized using pytest markers:

```python
@pytest.mark.unit           # Unit test marker
@pytest.mark.integration    # Integration test marker  
@pytest.mark.performance    # Performance test marker
@pytest.mark.slow          # Slow running test
@pytest.mark.api           # API endpoint test
@pytest.mark.database      # Database-related test
@pytest.mark.stress        # Stress test
@pytest.mark.benchmark     # Performance benchmark
```

### Running specific categories

```bash
# Run only fast unit tests
pytest -m "unit and not slow"

# Run integration tests excluding database tests
pytest -m "integration and not database"

# Run all performance and benchmark tests
pytest -m "performance or benchmark"
```

## Test Configuration

### Environment Setup

Create a `.env.test` file for test configuration:

```env
# Test Database
TEST_DATABASE_URL=postgresql://postgres:password@localhost:5432/optimus_test
TEST_REDIS_URL=redis://localhost:6379/1

# Test Mode
TESTING=true
LOG_LEVEL=DEBUG
ENABLE_TEST_FIXTURES=true

# Performance Test Settings
PERFORMANCE_TEST_TIMEOUT=600
LOAD_TEST_CONCURRENCY=20
STRESS_TEST_DURATION=300
```

### Database Setup

Tests require a test database. Set up PostgreSQL and Redis for testing:

```bash
# PostgreSQL setup
createdb optimus_test
psql -d optimus_test -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Redis setup (use database 1 for testing)
redis-cli -n 1 FLUSHDB
```

## Writing Tests

### Unit Test Example

```python
import pytest
from src.council.personas import StrategistPersona
from src.council.persona import PersonaResponse

class TestStrategistPersona:
    @pytest.fixture
    async def strategist(self):
        persona = StrategistPersona()
        await persona.initialize()
        return persona
    
    async def test_strategic_recommendation(self, strategist):
        response = await strategist.deliberate(
            topic="test",
            query="What's our technology strategy?",
            context={"domain": "technology"}
        )
        
        assert isinstance(response, PersonaResponse)
        assert response.persona_id == "strategist"
        assert response.confidence > 0
        assert len(response.recommendation) > 10
```

### Integration Test Example

```python
import pytest
from src.council.orchestrator import Orchestrator, DeliberationRequest

class TestDeliberationWorkflow:
    @pytest.fixture
    async def orchestrator(self):
        orch = Orchestrator(use_all_personas=False)
        await orch.initialize()
        return orch
    
    async def test_complete_deliberation(self, orchestrator):
        request = DeliberationRequest(
            query="What database should we use?",
            context={"application": "web_app"},
            topic="database_selection"
        )
        
        result = await orchestrator.deliberate(request)
        
        assert result.consensus is not None
        assert result.consensus.decision != ""
        assert result.consensus.confidence > 0
        assert len(result.persona_responses) >= 3
```

### Performance Test Example

```python
import pytest
import asyncio
import time
from src.council.orchestrator import Orchestrator

class TestPerformance:
    @pytest.mark.performance
    async def test_deliberation_performance(self):
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        
        # Measure single deliberation time
        start_time = time.time()
        result = await orchestrator.deliberate(request)
        end_time = time.time()
        
        deliberation_time = end_time - start_time
        
        # Performance assertions
        assert deliberation_time < 3.0  # Should complete within 3 seconds
        assert result.deliberation_time < 2.5
```

## Test Fixtures

### Common Fixtures

The `conftest.py` provides shared fixtures:

```python
# Database fixtures
@pytest.fixture
async def temp_database():
    """Temporary database for testing"""

@pytest.fixture  
async def memory_manager(temp_database):
    """Memory manager with test database"""

@pytest.fixture
async def knowledge_graph(temp_database):
    """Knowledge graph with test database"""

# Orchestrator fixtures
@pytest.fixture
async def orchestrator():
    """Basic orchestrator for testing"""

@pytest.fixture
async def full_orchestrator():
    """Orchestrator with all personas"""

# Mock fixtures
@pytest.fixture
def mock_redis():
    """Mock Redis client"""

@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL client"""
```

### Using Fixtures

```python
async def test_with_fixtures(orchestrator, memory_manager, mock_redis):
    # Test uses provided fixtures
    result = await orchestrator.deliberate(request)
    await memory_manager.store_memory(memory_entry)
    mock_redis.set.assert_called()
```

## Mocking and Test Doubles

### Mocking External Dependencies

```python
from unittest.mock import MagicMock, AsyncMock, patch

# Mock database operations
with patch('src.database.memory_optimized.OptimizedMemoryManager') as mock_memory:
    mock_memory.return_value.store_memory = AsyncMock()
    # Test code here

# Mock persona responses
persona.deliberate = AsyncMock(return_value=PersonaResponse(...))

# Mock external APIs
with patch('requests.get') as mock_get:
    mock_get.return_value.json.return_value = {"data": "test"}
    # Test code here
```

### Test Data Builders

```python
def create_sample_deliberation_request(query="Test query", **kwargs):
    return DeliberationRequest(
        query=query,
        context=kwargs.get("context", {}),
        topic=kwargs.get("topic", "test_topic"),
        timeout=kwargs.get("timeout", 5.0)
    )

def create_sample_persona_response(persona_id="test", **kwargs):
    return PersonaResponse(
        persona_id=persona_id,
        recommendation=kwargs.get("recommendation", "Test recommendation"),
        reasoning=kwargs.get("reasoning", "Test reasoning"),
        confidence=kwargs.get("confidence", 0.8),
        priority=kwargs.get("priority", PersonaPriority.MEDIUM)
    )
```

## Performance Testing

### Load Testing

Performance tests simulate various load conditions:

```python
@pytest.mark.performance
async def test_concurrent_deliberations():
    orchestrator = Orchestrator()
    await orchestrator.initialize()
    
    # Run multiple deliberations concurrently
    tasks = [
        orchestrator.deliberate(create_request(i))
        for i in range(10)
    ]
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    # Performance assertions
    total_time = end_time - start_time
    assert total_time < 15.0  # Should complete within 15 seconds
    assert all(r.consensus is not None for r in results)
```

### Memory Testing

```python
import psutil

@pytest.mark.performance
def test_memory_usage():
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024
    
    # Run memory-intensive operations
    for i in range(100):
        # Perform operations
        pass
    
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_growth = final_memory - initial_memory
    
    assert memory_growth < 100  # Should not grow more than 100MB
```

### Benchmarking

```python
@pytest.mark.benchmark
def test_persona_response_benchmark(benchmark):
    persona = StrategistPersona()
    
    def deliberate_sync():
        return asyncio.run(persona.deliberate("test", "query", {}))
    
    result = benchmark(deliberate_sync)
    assert result is not None
```

## Coverage Requirements

### Coverage Targets

- **Overall Coverage**: Minimum 85%
- **Unit Test Coverage**: Minimum 90%
- **Integration Test Coverage**: Minimum 80%
- **Critical Path Coverage**: 100%

### Generating Coverage Reports

```bash
# HTML coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# XML coverage report (for CI)
pytest --cov=src --cov-report=xml

# Terminal coverage report
pytest --cov=src --cov-report=term-missing

# Coverage with branch analysis
pytest --cov=src --cov-branch --cov-report=term-missing
```

### Exclusions

Coverage exclusions are configured in `pyproject.toml`:

```toml
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/venv/*", 
    "*/migrations/*",
    "*/__init__.py"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "pass",
    "except ImportError:"
]
```

## Continuous Integration

### GitHub Actions

The `.github/workflows/tests.yml` file configures automated testing:

- **Unit Tests**: Run on every push and PR
- **Integration Tests**: Run on main branch and PRs  
- **Performance Tests**: Run nightly and on release branches
- **Coverage Reporting**: Automated coverage reports to Codecov
- **Quality Gates**: Enforce coverage and performance thresholds

### Local CI Simulation

```bash
# Simulate CI environment
export CI=true
./scripts/run_tests.sh

# Run with CI-specific settings
pytest --cov=src --cov-fail-under=85 --junit-xml=junit.xml -x
```

## Debugging Tests

### Running Individual Tests

```bash
# Single test with verbose output
pytest tests/unit/test_personas.py::TestStrategistPersona::test_initialization -v -s

# Test with debugger
pytest tests/unit/test_personas.py::test_specific -v -s --pdb

# Test with logging
pytest tests/unit/test_personas.py -v -s --log-cli-level=DEBUG
```

### Test Debugging Tips

1. **Use print statements or logging** for debugging test logic
2. **Set breakpoints** with `pytest --pdb` for interactive debugging
3. **Isolate failures** by running specific test methods
4. **Check fixtures** ensure fixtures are properly configured
5. **Verify mocks** ensure mocks are set up correctly
6. **Review test data** check that test data matches expectations

## Best Practices

### Test Writing Guidelines

1. **Test Structure**: Follow Arrange-Act-Assert pattern
2. **Test Independence**: Each test should be independent and isolated
3. **Descriptive Names**: Use clear, descriptive test names
4. **Single Responsibility**: Each test should test one specific behavior
5. **Mock External Dependencies**: Mock databases, APIs, and external services
6. **Use Fixtures**: Leverage pytest fixtures for setup and teardown
7. **Assert Meaningfully**: Write assertions that clearly indicate success/failure

### Performance Testing Guidelines

1. **Set Realistic Thresholds**: Base performance thresholds on realistic requirements
2. **Test Under Load**: Include concurrent and high-load scenarios
3. **Monitor Resources**: Track memory, CPU, and I/O usage
4. **Baseline Comparisons**: Compare against historical performance data
5. **Environment Consistency**: Use consistent test environments

### Maintenance

1. **Regular Updates**: Keep test dependencies updated
2. **Flaky Test Detection**: Monitor and fix flaky tests
3. **Coverage Monitoring**: Maintain high test coverage
4. **Performance Monitoring**: Track performance test trends
5. **Test Review**: Include test code in code reviews

## Troubleshooting

### Common Issues

1. **Database Connection Failures**
   ```bash
   # Check database is running
   pg_isready -h localhost -p 5432
   
   # Verify connection string
   echo $TEST_DATABASE_URL
   ```

2. **Redis Connection Failures**
   ```bash
   # Check Redis is running
   redis-cli ping
   
   # Verify Redis URL
   echo $TEST_REDIS_URL
   ```

3. **Import Errors**
   ```bash
   # Check PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   
   # Install in development mode
   pip install -e .
   ```

4. **Async Test Issues**
   ```python
   # Ensure async tests use async/await properly
   async def test_async_function():
       result = await async_function()
       assert result is not None
   ```

5. **Mock Configuration Issues**
   ```python
   # Ensure mocks are configured before use
   mock_object.return_value = expected_value
   # Then call the function that uses the mock
   ```

### Getting Help

- **Check Documentation**: Review test documentation and examples
- **Run Verbose Tests**: Use `-v` flag for detailed test output
- **Check Logs**: Review test logs and error messages
- **Isolate Issues**: Run individual tests to isolate problems
- **Review Fixtures**: Ensure fixtures are working correctly

## Future Enhancements

### Planned Improvements

1. **Contract Testing**: Add contract tests for API interfaces
2. **Property-Based Testing**: Implement hypothesis-based testing
3. **Visual Testing**: Add screenshot comparison tests for UI components
4. **Chaos Engineering**: Implement chaos testing for resilience validation
5. **Security Testing**: Add automated security scanning and penetration testing
6. **Load Testing at Scale**: Implement distributed load testing
7. **Test Data Management**: Implement sophisticated test data management
8. **AI-Powered Testing**: Use AI to generate test cases and identify gaps

This testing strategy ensures the Optimus Council of Minds system maintains high quality, performance, and reliability across all components and use cases.
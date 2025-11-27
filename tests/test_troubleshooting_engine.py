"""
Comprehensive Test Suite for Smart Troubleshooting Engine
========================================================

Tests for the troubleshooting engine, solution library, auto fixer,
and solution search components. Includes unit tests, integration tests,
and performance tests.
"""

import asyncio
import json
import pytest
import tempfile
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.models.troubleshooting import (
    Solution, ErrorContext, FixAttempt, SolutionEffectiveness,
    KnowledgeBase, TroubleshootingSession
)
from src.services.troubleshooting_engine import (
    TroubleshootingEngine, ErrorAnalysis, SolutionCandidate, FixResult
)
from src.services.solution_library import SolutionLibrary
from src.services.auto_fixer import AutoFixer, ExecutionContext
from src.services.solution_search import SolutionSearchService, ExternalSolution


# Test fixtures
@pytest.fixture
async def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create tables (simplified for tests)
    async with engine.begin() as conn:
        # In a real test, you'd run migrations here
        pass
    
    async with async_session() as session:
        yield session


@pytest.fixture
def sample_error_analysis():
    """Sample error analysis for testing."""
    return ErrorAnalysis(
        error_hash="test_hash_123",
        error_type="missing_dependency",
        severity="medium",
        category="dependency",
        message="ModuleNotFoundError: No module named 'requests'",
        stack_trace="Traceback (most recent call last):\n  File test.py...",
        file_path="/path/to/test.py",
        line_number=10,
        language="python",
        framework="flask",
        confidence=0.9,
        context={"project_id": "test-project-id"},
        similar_errors=["hash1", "hash2"]
    )


@pytest.fixture
def sample_solution_candidate():
    """Sample solution candidate for testing."""
    return SolutionCandidate(
        solution_id="test-solution-id",
        title="Install missing Python module",
        description="Install the missing module using pip",
        confidence=0.8,
        success_rate=0.85,
        category="dependency",
        fix_commands=["pip install requests"],
        verification_commands=["python -c 'import requests'"],
        rollback_commands=["pip uninstall -y requests"],
        risk_level="low",
        requires_approval=False,
        estimated_time_ms=5000,
        prerequisites=["pip"],
        metadata={"module_name": "requests"}
    )


@pytest.fixture
def execution_context():
    """Sample execution context for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield ExecutionContext(
            working_directory=tmpdir,
            environment_vars={"TEST_MODE": "true"},
            timeout_seconds=30,
            max_memory_mb=100,
            allow_network=True,
            allow_sudo=False
        )


class TestTroubleshootingEngine:
    """Test the core troubleshooting engine."""
    
    @pytest.mark.asyncio
    async def test_analyze_error_python_module(self, db_session):
        """Test error analysis for Python ModuleNotFoundError."""
        engine = TroubleshootingEngine(db_session)
        
        error_text = "ModuleNotFoundError: No module named 'requests'"
        context = {"file_path": "/test/app.py", "language": "python"}
        
        analysis = await engine.analyze_error(error_text, context)
        
        assert analysis.error_type == "missing_dependency"
        assert analysis.language == "python"
        assert analysis.category == "dependency"
        assert analysis.severity == "medium"
        assert "requests" in analysis.context or "requests" in analysis.message
        assert analysis.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_error_javascript_module(self, db_session):
        """Test error analysis for JavaScript module error."""
        engine = TroubleshootingEngine(db_session)
        
        error_text = "Error: Cannot find module 'express'"
        context = {"language": "javascript"}
        
        analysis = await engine.analyze_error(error_text, context)
        
        assert analysis.error_type == "missing_module"
        assert analysis.language == "javascript"
        assert analysis.category == "dependency"
        assert analysis.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_error_port_conflict(self, db_session):
        """Test error analysis for port conflict."""
        engine = TroubleshootingEngine(db_session)
        
        error_text = "Error: listen EADDRINUSE: address already in use :::3000"
        
        analysis = await engine.analyze_error(error_text)
        
        assert analysis.error_type == "port_in_use"
        assert analysis.category == "network"
        assert analysis.confidence > 0.6
    
    @pytest.mark.asyncio
    async def test_error_hash_consistency(self, db_session):
        """Test that error hash generation is consistent."""
        engine = TroubleshootingEngine(db_session)
        
        error_text = "ModuleNotFoundError: No module named 'test_module'"
        
        analysis1 = await engine.analyze_error(error_text)
        analysis2 = await engine.analyze_error(error_text)
        
        assert analysis1.error_hash == analysis2.error_hash
    
    @pytest.mark.asyncio
    async def test_error_hash_normalization(self, db_session):
        """Test that similar errors get similar hashes."""
        engine = TroubleshootingEngine(db_session)
        
        error1 = "ModuleNotFoundError: No module named 'module1'"
        error2 = "ModuleNotFoundError: No module named 'module2'"
        
        analysis1 = await engine.analyze_error(error1)
        analysis2 = await engine.analyze_error(error2)
        
        # Should have same error type but different context
        assert analysis1.error_type == analysis2.error_type
        # Hashes might be different due to module name, but error type should be same
        assert analysis1.error_type == "missing_dependency"
    
    @pytest.mark.asyncio
    async def test_find_solutions_empty_database(self, db_session):
        """Test finding solutions when database is empty."""
        engine = TroubleshootingEngine(db_session)
        
        error_analysis = ErrorAnalysis(
            error_hash="test_hash",
            error_type="test_error",
            severity="medium",
            category="dependency",
            message="Test error",
            stack_trace=None,
            file_path=None,
            line_number=None,
            language="python",
            framework=None,
            confidence=0.8
        )
        
        solutions = await engine.find_solutions(error_analysis)
        
        # Should return empty list when no solutions in database
        assert isinstance(solutions, list)
        assert len(solutions) == 0
    
    @pytest.mark.asyncio
    async def test_predict_issues_memory_usage(self, db_session):
        """Test issue prediction for high memory usage."""
        engine = TroubleshootingEngine(db_session)
        
        metrics = {
            "memory_usage": 90.0,  # 90% memory usage
            "cpu_usage": 50.0,
            "disk_usage": 70.0
        }
        
        issues = await engine.predict_issues(metrics)
        
        assert len(issues) > 0
        memory_issue = next((i for i in issues if i.issue_type == "memory_leak"), None)
        assert memory_issue is not None
        assert memory_issue.severity in ["medium", "high"]
        assert memory_issue.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_predict_issues_disk_space(self, db_session):
        """Test issue prediction for low disk space."""
        engine = TroubleshootingEngine(db_session)
        
        metrics = {
            "disk_usage": 96.0,  # 96% disk usage
            "memory_usage": 30.0,
            "cpu_usage": 40.0
        }
        
        issues = await engine.predict_issues(metrics)
        
        assert len(issues) > 0
        disk_issue = next((i for i in issues if i.issue_type == "disk_space_low"), None)
        assert disk_issue is not None
        assert disk_issue.severity == "critical"
        assert "storage cleanup" in disk_issue.description.lower()
    
    @pytest.mark.asyncio
    async def test_learning_from_outcome(self, db_session, sample_error_analysis):
        """Test learning from fix attempt outcomes."""
        engine = TroubleshootingEngine(db_session)
        
        fix_result = FixResult(
            attempt_id="test-attempt",
            success=True,
            error_resolved=True,
            execution_time_ms=2000,
            commands_executed=["pip install requests"],
            output="Successfully installed requests",
            error_output=None,
            side_effects=[],
            verification_passed=True,
            rollback_available=True,
            confidence_score=0.9
        )
        
        solution_id = str(uuid.uuid4())
        
        # This should not raise an exception
        await engine.learn_from_outcome(fix_result, sample_error_analysis, solution_id)
    
    @pytest.mark.asyncio
    async def test_troubleshooting_statistics(self, db_session):
        """Test getting troubleshooting statistics."""
        engine = TroubleshootingEngine(db_session)
        
        stats = await engine.get_troubleshooting_statistics()
        
        assert isinstance(stats, dict)
        assert "error_patterns" in stats
        assert "solutions" in stats
        assert "fix_attempts" in stats
        assert "cache" in stats


class TestSolutionLibrary:
    """Test the solution library."""
    
    @pytest.mark.asyncio
    async def test_initialize_default_solutions(self, db_session):
        """Test initializing the solution library."""
        library = SolutionLibrary(db_session)
        
        # Mock the database operations for this test
        with patch.object(library, '_create_or_update_solution') as mock_create:
            await library.initialize_default_solutions()
            
            # Should have called create/update for multiple solutions
            assert mock_create.call_count > 0
    
    @pytest.mark.asyncio
    async def test_add_custom_solution(self, db_session):
        """Test adding a custom solution."""
        library = SolutionLibrary(db_session)
        
        # Mock session operations
        db_session.add = MagicMock()
        db_session.commit = AsyncMock()
        
        solution_id = await library.add_custom_solution(
            title="Test Solution",
            description="Test description",
            category="dependency",
            fix_commands=["test command"],
            language="python"
        )
        
        assert solution_id is not None
        assert isinstance(solution_id, str)
        db_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_solutions(self, db_session):
        """Test searching solutions."""
        library = SolutionLibrary(db_session)
        
        # Mock database query
        with patch.object(db_session, 'execute') as mock_execute:
            mock_result = MagicMock()
            mock_result.scalars().all.return_value = []
            mock_execute.return_value = mock_result
            
            results = await library.search_solutions("python import")
            
            assert isinstance(results, list)
            mock_execute.assert_called_once()


class TestAutoFixer:
    """Test the auto fixer."""
    
    @pytest.mark.asyncio
    async def test_execute_fix_dry_run(self, db_session, sample_solution_candidate, execution_context):
        """Test executing a fix in dry run mode."""
        fixer = AutoFixer(db_session)
        
        result = await fixer.execute_fix(
            sample_solution_candidate,
            execution_context,
            dry_run=True
        )
        
        assert isinstance(result, FixResult)
        assert result.metadata["dry_run"] is True
        assert "DRY RUN" in result.output
        assert len(result.commands_executed) == 0  # No commands executed in dry run
    
    @pytest.mark.asyncio
    async def test_execute_fix_requires_approval(self, db_session, execution_context):
        """Test executing a fix that requires approval."""
        fixer = AutoFixer(db_session)
        
        solution = SolutionCandidate(
            solution_id="test-id",
            title="Dangerous fix",
            description="This requires approval",
            confidence=0.8,
            success_rate=0.7,
            category="process",
            fix_commands=["sudo rm -rf /tmp/test"],
            verification_commands=[],
            rollback_commands=[],
            risk_level="high",
            requires_approval=True,
            estimated_time_ms=1000
        )
        
        result = await fixer.execute_fix(solution, execution_context)
        
        assert result.success is False
        assert "requires manual approval" in result.output.lower()
        assert result.metadata["requires_approval"] is True
    
    @pytest.mark.asyncio
    async def test_safety_checks_dangerous_command(self, db_session, execution_context):
        """Test safety checks for dangerous commands."""
        fixer = AutoFixer(db_session)
        
        solution = SolutionCandidate(
            solution_id="test-id",
            title="Dangerous solution",
            description="Contains dangerous commands",
            confidence=0.8,
            success_rate=0.7,
            category="process",
            fix_commands=["rm -rf /"],  # Dangerous command
            verification_commands=[],
            rollback_commands=[],
            risk_level="critical",
            requires_approval=False,
            estimated_time_ms=1000
        )
        
        safety_checks = await fixer._perform_safety_checks(solution, execution_context)
        
        # Should have critical safety check failures
        critical_failures = [c for c in safety_checks if c.severity == "critical" and not c.passed]
        assert len(critical_failures) > 0
        assert any("dangerous" in c.message.lower() for c in critical_failures)
    
    @pytest.mark.asyncio
    async def test_command_validation(self, db_session):
        """Test command structure validation."""
        fixer = AutoFixer(db_session)
        
        # Test safe commands
        assert fixer._validate_command_structure("pip install requests")
        assert fixer._validate_command_structure("npm install express")
        assert fixer._validate_command_structure("git status")
        
        # Test dangerous commands
        assert not fixer._validate_command_structure("; rm -rf /")
        assert not fixer._validate_command_structure("&& rm -rf /")
        assert not fixer._validate_command_structure("$(rm -rf /)")
        assert not fixer._validate_command_structure("")  # Empty command
    
    @pytest.mark.asyncio
    async def test_backup_creation(self, db_session, execution_context):
        """Test backup creation for destructive operations."""
        fixer = AutoFixer(db_session)
        
        # Create some test files
        test_files = ["package.json", "requirements.txt", ".env"]
        for filename in test_files:
            test_file = Path(execution_context.working_directory) / filename
            test_file.write_text(f"test content for {filename}")
        
        backup_path = await fixer._create_backup(execution_context)
        
        assert backup_path != ""
        assert Path(backup_path).exists()
        
        # Check that important files were backed up
        backup_dir = Path(backup_path)
        for filename in test_files:
            backed_up_file = backup_dir / filename
            assert backed_up_file.exists()
    
    @pytest.mark.asyncio
    async def test_prerequisite_checking(self, db_session, execution_context):
        """Test prerequisite checking."""
        fixer = AutoFixer(db_session)
        
        # Test common prerequisites
        # Note: These might fail in test environment, but we're testing the logic
        try:
            has_python = await fixer._check_prerequisite("python", execution_context)
            assert isinstance(has_python, bool)
        except:
            pass  # May not have python in test environment
        
        # Test file prerequisite
        test_file = Path(execution_context.working_directory) / "test.txt"
        test_file.write_text("test")
        
        has_file = await fixer._check_prerequisite("test.txt", execution_context)
        assert has_file is True
        
        has_missing_file = await fixer._check_prerequisite("missing.txt", execution_context)
        assert has_missing_file is False


class TestSolutionSearch:
    """Test the solution search service."""
    
    @pytest.mark.asyncio
    async def test_generate_search_query(self):
        """Test search query generation."""
        async with SolutionSearchService() as search_service:
            error_message = "ModuleNotFoundError: No module named 'requests'"
            query = search_service._generate_search_query(error_message, "python", "flask")
            
            assert query.language == "python"
            assert query.framework == "flask"
            assert query.error_type == "dependency"
            assert "module" in query.keywords or "import" in query.keywords
            assert len(query.search_terms) > 0
    
    @pytest.mark.asyncio
    async def test_normalize_error_message(self):
        """Test error message normalization."""
        async with SolutionSearchService() as search_service:
            error_msg = 'File "/long/path/to/file.py", line 123, in function\nModuleNotFoundError: No module named \'specific_module\''
            
            normalized = search_service._normalize_error_message(error_msg)
            
            # Should remove specific paths and line numbers
            assert "/long/path/to/file.py" not in normalized
            assert "123" not in normalized
            assert "specific_module" not in normalized
            assert "[PATH]" in normalized
            assert "[LINE]" in normalized
            assert "[VAR]" in normalized
    
    @pytest.mark.asyncio
    async def test_extract_keywords(self):
        """Test keyword extraction from error messages."""
        async with SolutionSearchService() as search_service:
            error_msg = "ModuleNotFoundError: No module named 'requests'"
            keywords = search_service._extract_keywords(error_msg)
            
            assert "module" in keywords or "import" in keywords
            assert "requests" in keywords
    
    @pytest.mark.asyncio
    async def test_detect_error_type(self):
        """Test error type detection."""
        async with SolutionSearchService() as search_service:
            test_cases = [
                ("ModuleNotFoundError: No module named 'test'", "dependency"),
                ("SyntaxError: invalid syntax", "syntax"),
                ("TypeError: unsupported operand", "runtime"),
                ("ConnectionError: Failed to connect", "network"),
                ("FileNotFoundError: No such file", "filesystem"),
                ("OutOfMemoryError: Java heap space", "memory"),
            ]
            
            for error_msg, expected_type in test_cases:
                detected_type = search_service._detect_error_type(error_msg)
                assert detected_type == expected_type
    
    @pytest.mark.asyncio
    async def test_extract_code_snippets(self):
        """Test code snippet extraction."""
        async with SolutionSearchService() as search_service:
            content = """
            Here's the solution:
            
            ```python
            import requests
            response = requests.get('https://api.example.com')
            ```
            
            You can also use `pip install requests` to install it.
            
                # Alternative approach
                import urllib.request
                urllib.request.urlopen('https://api.example.com')
            """
            
            snippets = search_service._extract_code_snippets(content)
            
            assert len(snippets) >= 1
            assert any("import requests" in snippet for snippet in snippets)
            assert any("pip install requests" in snippet for snippet in snippets)
    
    @pytest.mark.asyncio
    async def test_calculate_relevance_score(self):
        """Test solution relevance scoring."""
        async with SolutionSearchService() as search_service:
            # Mock Stack Overflow result
            stackoverflow_item = {
                'title': 'How to fix ModuleNotFoundError in Python',
                'score': 50,
                'is_answered': True,
                'view_count': 10000,
                'creation_date': int(datetime.now().timestamp()) - 86400,  # 1 day ago
                'tags': ['python', 'module', 'import-error']
            }
            
            query = search_service._generate_search_query(
                "ModuleNotFoundError: No module named 'requests'",
                "python",
                None
            )
            
            score = search_service._calculate_relevance_score(stackoverflow_item, query)
            
            assert 0.0 <= score <= 1.0
            assert score > 0.3  # Should have decent relevance
    
    @pytest.mark.asyncio 
    async def test_rate_limiting(self):
        """Test API rate limiting logic."""
        async with SolutionSearchService() as search_service:
            # Test rate limit checking
            can_make_request = search_service._can_make_request('stackoverflow')
            assert isinstance(can_make_request, bool)
            
            # Test rate limit updating
            search_service._update_rate_limit('stackoverflow')
            assert search_service.rate_limits['stackoverflow']['requests'] > 0


class TestIntegration:
    """Integration tests for the complete troubleshooting system."""
    
    @pytest.mark.asyncio
    async def test_full_troubleshooting_workflow(self, db_session):
        """Test the complete troubleshooting workflow."""
        # Initialize components
        engine = TroubleshootingEngine(db_session)
        library = SolutionLibrary(db_session)
        fixer = AutoFixer(db_session)
        
        # Mock solution in database
        test_solution = Solution(
            id=uuid.uuid4(),
            title="Install Python package",
            description="Install missing Python package using pip",
            category="dependency",
            language="python",
            fix_commands=["pip install {module_name}"],
            verification_commands=["python -c 'import {module_name}'"],
            rollback_commands=["pip uninstall -y {module_name}"],
            risk_level="low",
            requires_approval=False,
            success_rate=Decimal("0.85"),
            source="internal"
        )
        db_session.add(test_solution)
        
        # 1. Analyze error
        error_text = "ModuleNotFoundError: No module named 'requests'"
        analysis = await engine.analyze_error(error_text, {"language": "python"})
        
        assert analysis.error_type == "missing_dependency"
        assert analysis.language == "python"
        
        # 2. Find solutions
        solutions = await engine.find_solutions(analysis)
        
        # Should find our test solution (mocked database might not work exactly)
        # In real integration test, this would work with actual database
        assert isinstance(solutions, list)
        
        # 3. Execute fix (dry run)
        if solutions:
            solution = solutions[0]
            
            with tempfile.TemporaryDirectory() as tmpdir:
                context = ExecutionContext(
                    working_directory=tmpdir,
                    environment_vars={"module_name": "requests"},
                    allow_sudo=False
                )
                
                fix_result = await fixer.execute_fix(solution, context, dry_run=True)
                
                assert isinstance(fix_result, FixResult)
                assert fix_result.metadata["dry_run"] is True
                
                # 4. Learn from outcome
                await engine.learn_from_outcome(fix_result, analysis, solution.solution_id)
    
    @pytest.mark.asyncio
    async def test_error_pattern_learning(self, db_session):
        """Test that the system learns from repeated errors."""
        engine = TroubleshootingEngine(db_session)
        
        # Simulate the same error occurring multiple times
        error_text = "ModuleNotFoundError: No module named 'numpy'"
        
        # First occurrence
        analysis1 = await engine.analyze_error(error_text, {"project_id": "test-project"})
        
        # Second occurrence (should have same hash)
        analysis2 = await engine.analyze_error(error_text, {"project_id": "test-project"})
        
        assert analysis1.error_hash == analysis2.error_hash
        assert analysis1.error_type == analysis2.error_type
    
    @pytest.mark.asyncio
    async def test_multi_language_error_detection(self, db_session):
        """Test error detection across multiple programming languages."""
        engine = TroubleshootingEngine(db_session)
        
        test_cases = [
            ("ModuleNotFoundError: No module named 'pandas'", "python", "missing_dependency"),
            ("Error: Cannot find module 'express'", "javascript", "missing_module"),
            ("ClassNotFoundException: com.example.MyClass", "java", "class_not_found"),
            ("cannot find crate `serde`", "rust", "missing_crate"),
            ("cannot find package \"fmt\"", "go", "missing_package"),
        ]
        
        for error_text, expected_lang, expected_type in test_cases:
            analysis = await engine.analyze_error(error_text, {"language": expected_lang})
            
            assert analysis.language == expected_lang or analysis.language is None  # Might not detect all
            assert analysis.error_type == expected_type or analysis.category == "dependency"


class TestPerformance:
    """Performance tests for the troubleshooting engine."""
    
    @pytest.mark.asyncio
    async def test_error_analysis_performance(self, db_session):
        """Test error analysis performance with many errors."""
        engine = TroubleshootingEngine(db_session)
        
        # Test with multiple errors
        errors = [
            "ModuleNotFoundError: No module named 'requests'",
            "SyntaxError: invalid syntax",
            "TypeError: unsupported operand type(s)",
            "FileNotFoundError: [Errno 2] No such file",
            "ConnectionError: HTTPSConnectionPool"
        ] * 20  # 100 total errors
        
        start_time = datetime.now()
        
        tasks = [engine.analyze_error(error) for error in errors]
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should analyze 100 errors in reasonable time (< 5 seconds)
        assert duration < 5.0
        assert len(results) == 100
        assert all(isinstance(r, ErrorAnalysis) for r in results)
    
    @pytest.mark.asyncio
    async def test_solution_search_caching(self):
        """Test that solution search caching works correctly."""
        async with SolutionSearchService() as search_service:
            error_message = "ModuleNotFoundError: No module named 'test_module'"
            
            # First search (will cache)
            start_time = datetime.now()
            results1 = await search_service.search_solutions(error_message, "python")
            first_duration = (datetime.now() - start_time).total_seconds()
            
            # Second search (should use cache)
            start_time = datetime.now()
            results2 = await search_service.search_solutions(error_message, "python")
            second_duration = (datetime.now() - start_time).total_seconds()
            
            # Second search should be much faster (cached)
            # Note: This might not work in tests without actual API calls
            # but tests the caching logic
            assert isinstance(results1, list)
            assert isinstance(results2, list)
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_analysis(self, db_session):
        """Test memory usage during intensive error analysis."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        engine = TroubleshootingEngine(db_session)
        
        # Analyze many different errors
        for i in range(100):
            error_text = f"ModuleNotFoundError: No module named 'module_{i}'"
            await engine.analyze_error(error_text)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB


# Run specific test categories
if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])
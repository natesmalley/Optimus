"""
Integration tests for tool execution and permissions system
Tests the tool integration framework with persona permissions and rate limiting
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch

from src.council.tool_integration import (
    ToolExecutor, ToolPermission, ToolResult, ToolError,
    RateLimitExceededError, PermissionDeniedError
)
from src.council.orchestrator import Orchestrator, DeliberationRequest
from src.council.persona import PersonaResponse, PersonaPriority


class TestToolPermissionSystem:
    """Test tool permission and access control"""
    
    @pytest.fixture
    def sample_permissions(self):
        """Sample tool permissions configuration"""
        return {
            "file_operations": ToolPermission(
                allowed_personas=["analyst", "strategist"],
                rate_limit_per_minute=10,
                requires_approval=False,
                risk_level="medium"
            ),
            "web_search": ToolPermission(
                allowed_personas=["analyst", "explorer", "scholar"],
                rate_limit_per_minute=5,
                requires_approval=True,
                risk_level="low"
            ),
            "code_execution": ToolPermission(
                allowed_personas=["pragmatist", "innovator"],
                rate_limit_per_minute=3,
                requires_approval=True,
                risk_level="high"
            ),
            "database_query": ToolPermission(
                allowed_personas=["analyst", "strategist", "pragmatist"],
                rate_limit_per_minute=15,
                requires_approval=False,
                risk_level="medium"
            )
        }
    
    @pytest.fixture
    async def tool_executor(self, sample_permissions):
        """Create tool executor with sample permissions"""
        executor = ToolExecutor(permissions=sample_permissions)
        await executor.initialize()
        return executor
    
    def test_permission_creation(self, sample_permissions):
        """Test tool permission objects are created correctly"""
        file_perm = sample_permissions["file_operations"]
        
        assert "analyst" in file_perm.allowed_personas
        assert "strategist" in file_perm.allowed_personas
        assert file_perm.rate_limit_per_minute == 10
        assert file_perm.requires_approval is False
        assert file_perm.risk_level == "medium"
    
    async def test_permission_check_allowed(self, tool_executor):
        """Test permission check for allowed persona"""
        # Analyst should have file operations permission
        allowed = await tool_executor.check_permission("analyst", "file_operations")
        assert allowed is True
        
        # Explorer should have web search permission
        allowed = await tool_executor.check_permission("explorer", "web_search")
        assert allowed is True
    
    async def test_permission_check_denied(self, tool_executor):
        """Test permission check for denied persona"""
        # Guardian should not have code execution permission
        allowed = await tool_executor.check_permission("guardian", "code_execution")
        assert allowed is False
        
        # Philosopher should not have database query permission
        allowed = await tool_executor.check_permission("philosopher", "database_query")
        assert allowed is False
    
    async def test_nonexistent_tool_permission(self, tool_executor):
        """Test permission check for nonexistent tool"""
        allowed = await tool_executor.check_permission("analyst", "nonexistent_tool")
        assert allowed is False
    
    async def test_rate_limit_enforcement(self, tool_executor):
        """Test rate limiting enforcement"""
        persona_id = "analyst"
        tool_name = "file_operations"
        
        # Should allow initial requests up to limit
        for i in range(10):  # Limit is 10 per minute
            allowed = await tool_executor.check_rate_limit(persona_id, tool_name)
            assert allowed is True
            await tool_executor.record_tool_usage(persona_id, tool_name)
        
        # 11th request should be rate limited
        allowed = await tool_executor.check_rate_limit(persona_id, tool_name)
        assert allowed is False
    
    async def test_rate_limit_reset(self, tool_executor):
        """Test rate limit reset after time window"""
        persona_id = "analyst" 
        tool_name = "file_operations"
        
        # Use up rate limit
        for i in range(10):
            await tool_executor.record_tool_usage(persona_id, tool_name)
        
        # Should be rate limited
        allowed = await tool_executor.check_rate_limit(persona_id, tool_name)
        assert allowed is False
        
        # Mock time passage (rate limits reset after 1 minute)
        with patch('src.council.tool_integration.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(minutes=2)
            
            # Should be allowed again
            allowed = await tool_executor.check_rate_limit(persona_id, tool_name)
            assert allowed is True


class TestToolExecution:
    """Test actual tool execution functionality"""
    
    @pytest.fixture
    async def tool_executor_with_mocks(self, sample_permissions):
        """Create tool executor with mocked external tools"""
        executor = ToolExecutor(permissions=sample_permissions)
        
        # Mock external tool functions
        executor.tools = {
            "file_operations": {
                "read_file": AsyncMock(return_value="File content here"),
                "write_file": AsyncMock(return_value="File written successfully"),
                "list_files": AsyncMock(return_value=["file1.txt", "file2.py", "file3.md"])
            },
            "web_search": {
                "search": AsyncMock(return_value={
                    "results": [
                        {"title": "Result 1", "url": "https://example.com/1"},
                        {"title": "Result 2", "url": "https://example.com/2"}
                    ]
                })
            },
            "database_query": {
                "execute_query": AsyncMock(return_value={
                    "rows": [{"id": 1, "name": "test"}],
                    "count": 1
                })
            }
        }
        
        await executor.initialize()
        return executor
    
    async def test_successful_tool_execution(self, tool_executor_with_mocks):
        """Test successful tool execution"""
        executor = tool_executor_with_mocks
        
        # Execute file read operation
        result = await executor.execute_tool(
            persona_id="analyst",
            tool_name="file_operations",
            operation="read_file",
            parameters={"filename": "test.txt"}
        )
        
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == "File content here"
        assert result.tool_name == "file_operations"
        assert result.operation == "read_file"
        assert result.persona_id == "analyst"
        assert result.execution_time > 0
    
    async def test_tool_execution_permission_denied(self, tool_executor_with_mocks):
        """Test tool execution with insufficient permissions"""
        executor = tool_executor_with_mocks
        
        with pytest.raises(PermissionDeniedError):
            await executor.execute_tool(
                persona_id="guardian",  # Guardian doesn't have file operations permission
                tool_name="file_operations",
                operation="read_file",
                parameters={"filename": "test.txt"}
            )
    
    async def test_tool_execution_rate_limited(self, tool_executor_with_mocks):
        """Test tool execution when rate limited"""
        executor = tool_executor_with_mocks
        
        # Use up rate limit for web search (5 per minute)
        for i in range(5):
            await executor.execute_tool(
                persona_id="explorer",
                tool_name="web_search",
                operation="search",
                parameters={"query": f"test query {i}"}
            )
        
        # 6th request should fail with rate limit
        with pytest.raises(RateLimitExceededError):
            await executor.execute_tool(
                persona_id="explorer",
                tool_name="web_search", 
                operation="search",
                parameters={"query": "rate limited query"}
            )
    
    async def test_tool_execution_error_handling(self, tool_executor_with_mocks):
        """Test tool execution error handling"""
        executor = tool_executor_with_mocks
        
        # Mock tool failure
        executor.tools["file_operations"]["read_file"] = AsyncMock(
            side_effect=Exception("File not found")
        )
        
        result = await executor.execute_tool(
            persona_id="analyst",
            tool_name="file_operations",
            operation="read_file", 
            parameters={"filename": "nonexistent.txt"}
        )
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "File not found" in result.error_message
        assert result.data is None
    
    async def test_parallel_tool_execution(self, tool_executor_with_mocks):
        """Test concurrent tool execution"""
        executor = tool_executor_with_mocks
        
        # Execute multiple tools in parallel
        tasks = [
            executor.execute_tool(
                persona_id="analyst",
                tool_name="file_operations",
                operation="read_file",
                parameters={"filename": f"file{i}.txt"}
            )
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 5
        assert all(r.success for r in results)
        assert all(isinstance(r, ToolResult) for r in results)
        
        # Should have different execution times
        execution_times = [r.execution_time for r in results]
        assert all(t > 0 for t in execution_times)


class TestToolIntegrationWithDeliberation:
    """Test tool integration within deliberation process"""
    
    @pytest.fixture
    async def orchestrator_with_tools(self, sample_permissions):
        """Create orchestrator with tool capabilities"""
        orchestrator = Orchestrator(use_all_personas=False)
        
        # Mock tool executor
        tool_executor = MagicMock(spec=ToolExecutor)
        tool_executor.permissions = sample_permissions
        tool_executor.check_permission = AsyncMock(return_value=True)
        tool_executor.execute_tool = AsyncMock()
        
        orchestrator.tool_executor = tool_executor
        
        with patch('src.database.memory_optimized.OptimizedMemoryManager'):
            with patch('src.database.knowledge_graph_optimized.OptimizedKnowledgeGraph'):
                await orchestrator.initialize()
        
        return orchestrator, tool_executor
    
    async def test_persona_tool_usage_in_deliberation(self, orchestrator_with_tools):
        """Test personas using tools during deliberation"""
        orchestrator, tool_executor = orchestrator_with_tools
        
        # Mock tool execution results
        tool_executor.execute_tool.return_value = ToolResult(
            success=True,
            data={"query_results": [{"table": "users", "count": 1000}]},
            tool_name="database_query",
            operation="execute_query",
            persona_id="analyst"
        )
        
        # Mock analyst persona to use tools
        async def analyst_deliberate_with_tools(topic, query, context):
            # Simulate tool usage during deliberation
            if "database" in query.lower():
                tool_result = await tool_executor.execute_tool(
                    persona_id="analyst",
                    tool_name="database_query",
                    operation="execute_query",
                    parameters={"query": "SELECT COUNT(*) FROM users"}
                )
                
                data_points = [f"Database contains {tool_result.data['query_results'][0]['count']} users"]
            else:
                data_points = []
            
            return PersonaResponse(
                persona_id="analyst",
                recommendation="Use PostgreSQL with proper indexing",
                reasoning="Database analysis shows current user load patterns",
                confidence=0.9,
                priority=PersonaPriority.HIGH,
                data_points=data_points
            )
        
        orchestrator.personas["analyst"].deliberate = analyst_deliberate_with_tools
        
        request = DeliberationRequest(
            query="What database optimizations do we need for our user table?",
            context={"current_performance": "slow_queries"},
            topic="database_optimization"
        )
        
        result = await orchestrator.deliberate(request)
        
        # Verify tool was used
        tool_executor.execute_tool.assert_called_once()
        
        # Verify tool result influenced decision
        analyst_response = next(r for r in result.persona_responses if r.persona_id == "analyst")
        assert any("1000 users" in dp for dp in analyst_response.data_points)
    
    async def test_tool_failure_graceful_degradation(self, orchestrator_with_tools):
        """Test graceful handling of tool failures during deliberation"""
        orchestrator, tool_executor = orchestrator_with_tools
        
        # Mock tool failure
        tool_executor.execute_tool.side_effect = ToolError("Database connection failed")
        
        # Mock analyst persona to handle tool failures
        async def analyst_deliberate_with_fallback(topic, query, context):
            try:
                tool_result = await tool_executor.execute_tool(
                    persona_id="analyst",
                    tool_name="database_query",
                    operation="execute_query",
                    parameters={"query": "SELECT COUNT(*) FROM users"}
                )
                data_points = [f"Tool result: {tool_result.data}"]
            except ToolError:
                data_points = ["Tool unavailable, using cached analysis"]
            
            return PersonaResponse(
                persona_id="analyst",
                recommendation="Use cached analysis for database recommendations",
                reasoning="Primary analysis tools unavailable, falling back to previous insights",
                confidence=0.7,  # Lower confidence due to tool failure
                priority=PersonaPriority.MEDIUM,
                data_points=data_points
            )
        
        orchestrator.personas["analyst"].deliberate = analyst_deliberate_with_fallback
        
        request = DeliberationRequest(
            query="Analyze our database performance metrics",
            context={"urgency": "high"},
            topic="performance_analysis"
        )
        
        result = await orchestrator.deliberate(request)
        
        # Should handle gracefully
        assert isinstance(result, DeliberationResult)
        analyst_response = next(r for r in result.persona_responses if r.persona_id == "analyst")
        
        # Should indicate fallback was used
        assert "cached analysis" in analyst_response.data_points[0]
        assert analyst_response.confidence < 0.8  # Reduced confidence
    
    async def test_tool_approval_workflow(self, orchestrator_with_tools):
        """Test tool approval workflow for high-risk operations"""
        orchestrator, tool_executor = orchestrator_with_tools
        
        # Mock approval requirement
        tool_executor.check_permission.return_value = True
        tool_executor.requires_approval.return_value = True
        
        # Mock approval process
        approval_queue = []
        
        async def mock_request_approval(persona_id, tool_name, operation, parameters):
            approval_request = {
                "persona_id": persona_id,
                "tool_name": tool_name,
                "operation": operation,
                "parameters": parameters,
                "timestamp": datetime.now(),
                "status": "pending"
            }
            approval_queue.append(approval_request)
            return approval_request["id"] if "id" in approval_request else "approval_123"
        
        async def mock_check_approval(approval_id):
            return "approved"  # Simulate approval
        
        tool_executor.request_approval = mock_request_approval
        tool_executor.check_approval_status = mock_check_approval
        
        # Mock persona requesting high-risk operation
        async def innovator_deliberate_with_approval(topic, query, context):
            approval_id = await tool_executor.request_approval(
                persona_id="innovator",
                tool_name="code_execution",
                operation="run_script",
                parameters={"script": "analysis.py"}
            )
            
            approval_status = await tool_executor.check_approval_status(approval_id)
            
            if approval_status == "approved":
                confidence = 0.9
                reasoning = "Code execution approved and completed successfully"
            else:
                confidence = 0.6
                reasoning = "Code execution pending approval, using alternative analysis"
            
            return PersonaResponse(
                persona_id="innovator",
                recommendation="Implement automated analysis pipeline",
                reasoning=reasoning,
                confidence=confidence,
                priority=PersonaPriority.HIGH
            )
        
        orchestrator.personas["innovator"].deliberate = innovator_deliberate_with_approval
        
        request = DeliberationRequest(
            query="How can we automate our data analysis pipeline?",
            context={"automation_level": "high"},
            topic="automation_pipeline",
            required_personas=["innovator"]
        )
        
        result = await orchestrator.deliberate(request)
        
        # Verify approval workflow was triggered
        assert len(approval_queue) == 1
        assert approval_queue[0]["tool_name"] == "code_execution"
        
        # Verify result reflects approval
        innovator_response = next(r for r in result.persona_responses if r.persona_id == "innovator")
        assert "approved" in innovator_response.reasoning


class TestToolExecutionMetrics:
    """Test tool execution metrics and monitoring"""
    
    @pytest.fixture
    async def tool_executor_with_metrics(self, sample_permissions):
        """Create tool executor with metrics tracking"""
        executor = ToolExecutor(permissions=sample_permissions, enable_metrics=True)
        
        # Mock external tools
        executor.tools = {
            "file_operations": {
                "read_file": AsyncMock(return_value="File content")
            },
            "web_search": {
                "search": AsyncMock(return_value={"results": []})
            }
        }
        
        await executor.initialize()
        return executor
    
    async def test_tool_usage_metrics_collection(self, tool_executor_with_metrics):
        """Test collection of tool usage metrics"""
        executor = tool_executor_with_metrics
        
        # Execute various tools
        await executor.execute_tool("analyst", "file_operations", "read_file", {"filename": "test.txt"})
        await executor.execute_tool("explorer", "web_search", "search", {"query": "test"})
        await executor.execute_tool("analyst", "file_operations", "read_file", {"filename": "test2.txt"})
        
        # Get metrics
        metrics = await executor.get_usage_metrics()
        
        assert "total_executions" in metrics
        assert "executions_by_persona" in metrics
        assert "executions_by_tool" in metrics
        assert "success_rate" in metrics
        
        assert metrics["total_executions"] == 3
        assert metrics["executions_by_persona"]["analyst"] == 2
        assert metrics["executions_by_persona"]["explorer"] == 1
        assert metrics["executions_by_tool"]["file_operations"] == 2
        assert metrics["executions_by_tool"]["web_search"] == 1
    
    async def test_tool_performance_metrics(self, tool_executor_with_metrics):
        """Test tool performance metrics tracking"""
        executor = tool_executor_with_metrics
        
        # Execute tools multiple times
        for i in range(5):
            await executor.execute_tool("analyst", "file_operations", "read_file", {"filename": f"test{i}.txt"})
        
        # Get performance metrics
        performance = await executor.get_performance_metrics("file_operations")
        
        assert "avg_execution_time" in performance
        assert "total_executions" in performance
        assert "success_rate" in performance
        assert "error_rate" in performance
        
        assert performance["total_executions"] == 5
        assert performance["success_rate"] == 1.0  # All should succeed
        assert performance["avg_execution_time"] > 0
    
    async def test_rate_limit_metrics(self, tool_executor_with_metrics):
        """Test rate limit violation metrics"""
        executor = tool_executor_with_metrics
        
        # Hit rate limit for web search (5 per minute)
        successful_executions = 0
        rate_limited_count = 0
        
        for i in range(7):  # Attempt 7 executions (limit is 5)
            try:
                await executor.execute_tool("explorer", "web_search", "search", {"query": f"query {i}"})
                successful_executions += 1
            except RateLimitExceededError:
                rate_limited_count += 1
        
        assert successful_executions == 5
        assert rate_limited_count == 2
        
        # Check rate limit metrics
        rate_limit_stats = await executor.get_rate_limit_statistics()
        
        assert "violations_by_persona" in rate_limit_stats
        assert "violations_by_tool" in rate_limit_stats
        assert rate_limit_stats["violations_by_persona"]["explorer"] >= 2
        assert rate_limit_stats["violations_by_tool"]["web_search"] >= 2
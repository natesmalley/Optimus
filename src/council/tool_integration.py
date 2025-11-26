"""
Comprehensive Tool Integration Layer for Optimus Council of Minds

This module provides a unified interface for personas to interact with external tools,
MCP services, and CoralCollective agents. It enables parallel tool execution,
result storage in memory, and intelligent tool usage patterns.
"""

import asyncio
import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Union, Tuple, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
import hashlib

# Import MCP client (optional)
import sys
mcp_path = str(Path(__file__).parent.parent.parent / '.coral/mcp')
if Path(mcp_path).exists():
    sys.path.append(mcp_path)

# Import existing components (using TYPE_CHECKING to avoid circular imports)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .memory import MemorySystem, Memory
    from .knowledge_graph import KnowledgeGraph, Node, Edge, NodeType, EdgeType
    from .blackboard import Blackboard, BlackboardEntry, EntryType

# Try to import MCP client components
try:
    from mcp_client import MCPClient, AgentMCPInterface
    MCP_AVAILABLE = True
except ImportError:
    # Create mock classes if MCP is not available
    class MCPClient:
        def __init__(self, *args, **kwargs):
            pass
        async def initialize(self):
            pass
        async def shutdown(self):
            pass
        def get_available_servers(self):
            return []
        def get_metrics(self):
            return {}
    
    class AgentMCPInterface:
        def __init__(self, *args, **kwargs):
            pass
        async def filesystem_read(self, path):
            return None
        async def filesystem_write(self, path, content):
            return False
        async def filesystem_list(self, path):
            return []
        async def search_web(self, query, max_results=10):
            return []
        async def database_query(self, query, params=None):
            return []
        async def docker_run(self, image, command=None, env=None):
            return None
        async def e2b_execute(self, code, language="python"):
            return None
        async def github_create_issue(self, title, body, labels=None):
            return None
        async def github_create_pr(self, title, body, head, base="main"):
            return None
        async def close(self):
            pass
    
    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


class ToolCapabilityLevel(Enum):
    """Levels of tool capability access"""
    READ_ONLY = "read_only"
    LIMITED_WRITE = "limited_write" 
    FULL_ACCESS = "full_access"
    ADMIN = "admin"


class ToolCategory(Enum):
    """Categories of tools for organization"""
    FILE_SYSTEM = "filesystem"
    VERSION_CONTROL = "git"
    WEB_SEARCH = "search"
    DATABASE = "database"
    CONTAINER = "container"
    CODE_EXECUTION = "execution"
    API_CALL = "api"
    AI_AGENT = "agent"
    COMMUNICATION = "communication"
    MONITORING = "monitoring"


@dataclass
class ToolPermission:
    """Defines permission for a tool"""
    tool_name: str
    category: ToolCategory
    capability_level: ToolCapabilityLevel
    rate_limit_per_minute: int = 60
    requires_approval: bool = False
    approved_params: Set[str] = field(default_factory=set)
    restricted_params: Set[str] = field(default_factory=set)


@dataclass
class ToolResult:
    """Standardized tool execution result"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tool_name': self.tool_name,
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ToolUsageMetrics:
    """Track tool usage statistics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_used: Optional[datetime] = None
    rate_limit_violations: int = 0
    
    def update(self, result: ToolResult):
        """Update metrics with a new result"""
        self.total_calls += 1
        self.total_execution_time += result.execution_time
        self.average_execution_time = self.total_execution_time / self.total_calls
        self.last_used = result.timestamp
        
        if result.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1


class ToolCapability(ABC):
    """
    Base class that personas can inherit to gain tool capabilities.
    Provides standardized interface for tool execution and result handling.
    """
    
    def __init__(self, persona_id: str, persona_name: str):
        self.persona_id = persona_id
        self.persona_name = persona_name
        self.tool_permissions: Dict[str, ToolPermission] = {}
        self.tool_metrics: Dict[str, ToolUsageMetrics] = {}
        self.rate_limits: Dict[str, List[datetime]] = {}
        self.tool_integration: Optional['PersonaToolIntegration'] = None
        self._setup_default_permissions()
        
    def _setup_default_permissions(self):
        """Setup default tool permissions based on persona type"""
        # Base permissions that all personas get
        base_permissions = [
            ToolPermission("filesystem_read", ToolCategory.FILE_SYSTEM, ToolCapabilityLevel.READ_ONLY),
            ToolPermission("web_search", ToolCategory.WEB_SEARCH, ToolCapabilityLevel.READ_ONLY),
            ToolPermission("knowledge_query", ToolCategory.DATABASE, ToolCapabilityLevel.READ_ONLY),
        ]
        
        for perm in base_permissions:
            self.tool_permissions[perm.tool_name] = perm
    
    def set_tool_integration(self, integration: 'PersonaToolIntegration'):
        """Set the tool integration system"""
        self.tool_integration = integration
    
    def add_tool_permission(self, permission: ToolPermission):
        """Add a tool permission"""
        self.tool_permissions[permission.tool_name] = permission
        
    def check_rate_limit(self, tool_name: str) -> bool:
        """Check if tool is within rate limits"""
        if tool_name not in self.tool_permissions:
            return False
            
        permission = self.tool_permissions[tool_name]
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(seconds=60)
        
        # Clean old entries
        if tool_name in self.rate_limits:
            self.rate_limits[tool_name] = [
                ts for ts in self.rate_limits[tool_name] 
                if ts > minute_ago
            ]
        else:
            self.rate_limits[tool_name] = []
        
        # Check limit
        if len(self.rate_limits[tool_name]) >= permission.rate_limit_per_minute:
            if tool_name in self.tool_metrics:
                self.tool_metrics[tool_name].rate_limit_violations += 1
            return False
            
        return True
    
    def record_tool_usage(self, tool_name: str, timestamp: Optional[datetime] = None):
        """Record tool usage for rate limiting"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        if tool_name not in self.rate_limits:
            self.rate_limits[tool_name] = []
            
        self.rate_limits[tool_name].append(timestamp)
    
    def update_tool_metrics(self, result: ToolResult):
        """Update metrics for a tool"""
        if result.tool_name not in self.tool_metrics:
            self.tool_metrics[result.tool_name] = ToolUsageMetrics()
            
        self.tool_metrics[result.tool_name].update(result)
    
    async def execute_tool(self, 
                          tool_name: str, 
                          arguments: Dict[str, Any],
                          store_result: bool = True,
                          share_on_blackboard: bool = False) -> ToolResult:
        """Execute a single tool with permission checks"""
        if not self.tool_integration:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error="Tool integration not initialized"
            )
        
        return await self.tool_integration.execute_tool(
            tool_name=tool_name,
            arguments=arguments,
            requesting_persona=self,
            store_result=store_result,
            share_on_blackboard=share_on_blackboard
        )
    
    async def execute_tools_parallel(self,
                                   tool_requests: List[Tuple[str, Dict[str, Any]]],
                                   max_concurrent: int = 5) -> List[ToolResult]:
        """Execute multiple tools in parallel"""
        if not self.tool_integration:
            return [
                ToolResult(tool_name=req[0], success=False, error="Tool integration not initialized")
                for req in tool_requests
            ]
        
        return await self.tool_integration.execute_tools_parallel(
            tool_requests=tool_requests,
            requesting_persona=self,
            max_concurrent=max_concurrent
        )
    
    async def delegate_to_agent(self,
                               agent_type: str,
                               task_description: str,
                               context: Dict[str, Any]) -> ToolResult:
        """Delegate a complex task to a CoralCollective agent"""
        if not self.tool_integration:
            return ToolResult(
                tool_name=f"agent_{agent_type}",
                success=False,
                error="Tool integration not initialized"
            )
        
        return await self.tool_integration.delegate_to_coral_agent(
            agent_type=agent_type,
            task_description=task_description,
            context=context,
            requesting_persona=self
        )
    
    def get_tool_metrics(self) -> Dict[str, ToolUsageMetrics]:
        """Get tool usage metrics"""
        return self.tool_metrics.copy()


class PersonaToolIntegration:
    """
    Main tool integration system for personas.
    Manages MCP connections, agent delegation, and result storage.
    """
    
    def __init__(self,
                 memory_system: Any,  # MemorySystem type
                 knowledge_graph: Any,  # KnowledgeGraph type
                 blackboard: Optional[Any] = None,  # Blackboard type
                 mcp_config_path: Optional[str] = None):
        
        self.memory_system = memory_system
        self.knowledge_graph = knowledge_graph
        self.blackboard = blackboard
        self.mcp_client: Optional[MCPClient] = None
        self.agent_interfaces: Dict[str, AgentMCPInterface] = {}
        self.coral_agents_map: Dict[str, str] = self._load_coral_agents_map()
        self.tool_execution_cache: Dict[str, ToolResult] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize MCP client if available
        if MCP_AVAILABLE:
            if mcp_config_path:
                self.mcp_client = MCPClient(mcp_config_path)
            else:
                # Try default paths
                for path in [".coral/mcp/configs/mcp_config.yaml", "mcp_config.yaml"]:
                    if Path(path).exists():
                        self.mcp_client = MCPClient(path)
                        break
        else:
            logger.warning("MCP client not available - using mock client")
            
        if not self.mcp_client:
            self.mcp_client = MCPClient()  # Use mock client
        
        logger.info("PersonaToolIntegration initialized")
    
    def _load_coral_agents_map(self) -> Dict[str, str]:
        """Load mapping of task types to CoralCollective agents"""
        return {
            # Development tasks
            "backend_development": "backend_developer",
            "frontend_development": "frontend_developer", 
            "api_design": "api_designer",
            "database_design": "database_specialist",
            "full_stack": "full_stack_engineer",
            
            # Specialized tasks
            "ai_ml": "ai_ml_specialist",
            "security_audit": "security_specialist",
            "performance_optimization": "performance_engineer",
            "accessibility_review": "accessibility_specialist",
            "devops": "devops_deployment",
            "qa_testing": "qa_testing",
            
            # Architecture and strategy
            "system_architecture": "project_architect",
            "technical_writing": "technical_writer",
            "compliance": "compliance_specialist",
            
            # Data and analytics
            "data_engineering": "data_engineer",
            "analytics": "analytics_engineer",
            "data_strategy": "model_strategy_specialist",
            
            # Operations
            "site_reliability": "site_reliability_engineer",
            "monitoring": "site_reliability_engineer",
            
            # Design
            "ui_design": "ui_designer",
            "mobile_development": "mobile_developer"
        }
    
    async def initialize(self):
        """Initialize the tool integration system"""
        if self.mcp_client:
            await self.mcp_client.initialize()
            logger.info("MCP client initialized")
        else:
            logger.warning("No MCP client available - some tools will be unavailable")
    
    async def execute_tool(self,
                          tool_name: str,
                          arguments: Dict[str, Any],
                          requesting_persona: ToolCapability,
                          store_result: bool = True,
                          share_on_blackboard: bool = False) -> ToolResult:
        """Execute a single tool with comprehensive error handling"""
        
        start_time = datetime.now(timezone.utc)
        
        # Check permissions
        if tool_name not in requesting_persona.tool_permissions:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Permission denied: {requesting_persona.persona_name} cannot use {tool_name}"
            )
        
        # Check rate limits
        if not requesting_persona.check_rate_limit(tool_name):
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error="Rate limit exceeded"
            )
        
        # Check cache first
        cache_key = self._generate_cache_key(tool_name, arguments)
        if cache_key in self.tool_execution_cache:
            cached_result = self.tool_execution_cache[cache_key]
            age = (start_time - cached_result.timestamp).total_seconds()
            if age < self.cache_ttl:
                logger.debug(f"Using cached result for {tool_name}")
                return cached_result
        
        try:
            # Record usage
            requesting_persona.record_tool_usage(tool_name, start_time)
            
            # Execute tool
            result = await self._execute_tool_internal(tool_name, arguments, requesting_persona)
            
            # Calculate execution time
            end_time = datetime.now(timezone.utc)
            result.execution_time = (end_time - start_time).total_seconds()
            
            # Cache successful results
            if result.success:
                self.tool_execution_cache[cache_key] = result
            
            # Update metrics
            requesting_persona.update_tool_metrics(result)
            
            # Store result in memory system
            if store_result and result.success:
                await self._store_tool_result_in_memory(result, requesting_persona)
            
            # Share on blackboard if requested
            if share_on_blackboard and self.blackboard and result.success:
                await self._share_result_on_blackboard(result, requesting_persona)
            
            # Update knowledge graph
            await self._update_knowledge_graph(tool_name, arguments, result, requesting_persona)
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            logger.debug(traceback.format_exc())
            
            end_time = datetime.now(timezone.utc)
            result = ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=(end_time - start_time).total_seconds()
            )
            
            requesting_persona.update_tool_metrics(result)
            return result
    
    async def _execute_tool_internal(self,
                                   tool_name: str,
                                   arguments: Dict[str, Any],
                                   requesting_persona: ToolCapability) -> ToolResult:
        """Internal tool execution logic"""
        
        # Handle different tool categories
        if tool_name.startswith("filesystem_"):
            return await self._execute_filesystem_tool(tool_name, arguments, requesting_persona)
        elif tool_name.startswith("git_"):
            return await self._execute_git_tool(tool_name, arguments, requesting_persona)
        elif tool_name.startswith("web_"):
            return await self._execute_web_tool(tool_name, arguments, requesting_persona)
        elif tool_name.startswith("database_"):
            return await self._execute_database_tool(tool_name, arguments, requesting_persona)
        elif tool_name.startswith("docker_"):
            return await self._execute_docker_tool(tool_name, arguments, requesting_persona)
        elif tool_name.startswith("code_"):
            return await self._execute_code_tool(tool_name, arguments, requesting_persona)
        elif tool_name.startswith("knowledge_"):
            return await self._execute_knowledge_tool(tool_name, arguments, requesting_persona)
        else:
            # Try MCP tools
            return await self._execute_mcp_tool(tool_name, arguments, requesting_persona)
    
    async def _execute_filesystem_tool(self,
                                     tool_name: str,
                                     arguments: Dict[str, Any],
                                     requesting_persona: ToolCapability) -> ToolResult:
        """Execute filesystem tools"""
        if not self.mcp_client:
            return ToolResult(tool_name=tool_name, success=False, error="MCP client not available")
        
        try:
            interface = await self._get_agent_interface("filesystem", requesting_persona.persona_id)
            
            if tool_name == "filesystem_read":
                result = await interface.filesystem_read(arguments["path"])
                return ToolResult(
                    tool_name=tool_name,
                    success=result is not None,
                    result=result,
                    error=None if result else "File not found or permission denied"
                )
            
            elif tool_name == "filesystem_write":
                success = await interface.filesystem_write(arguments["path"], arguments["content"])
                return ToolResult(
                    tool_name=tool_name,
                    success=success,
                    result={"path": arguments["path"], "bytes_written": len(arguments["content"])} if success else None,
                    error=None if success else "Write failed"
                )
            
            elif tool_name == "filesystem_list":
                files = await interface.filesystem_list(arguments["path"])
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result={"files": files, "count": len(files)}
                )
            
            else:
                return ToolResult(tool_name=tool_name, success=False, error=f"Unknown filesystem tool: {tool_name}")
                
        except Exception as e:
            return ToolResult(tool_name=tool_name, success=False, error=str(e))
    
    async def _execute_git_tool(self,
                              tool_name: str,
                              arguments: Dict[str, Any],
                              requesting_persona: ToolCapability) -> ToolResult:
        """Execute git tools via GitHub MCP"""
        if not self.mcp_client:
            return ToolResult(tool_name=tool_name, success=False, error="MCP client not available")
        
        try:
            interface = await self._get_agent_interface("github", requesting_persona.persona_id)
            
            if tool_name == "git_create_issue":
                result = await interface.github_create_issue(
                    title=arguments["title"],
                    body=arguments["body"],
                    labels=arguments.get("labels", [])
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=result is not None,
                    result=result,
                    error=None if result else "Failed to create issue"
                )
            
            elif tool_name == "git_create_pr":
                result = await interface.github_create_pr(
                    title=arguments["title"],
                    body=arguments["body"],
                    head=arguments["head"],
                    base=arguments.get("base", "main")
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=result is not None,
                    result=result,
                    error=None if result else "Failed to create PR"
                )
            
            else:
                return ToolResult(tool_name=tool_name, success=False, error=f"Unknown git tool: {tool_name}")
                
        except Exception as e:
            return ToolResult(tool_name=tool_name, success=False, error=str(e))
    
    async def _execute_web_tool(self,
                              tool_name: str,
                              arguments: Dict[str, Any],
                              requesting_persona: ToolCapability) -> ToolResult:
        """Execute web search tools"""
        if not self.mcp_client:
            return ToolResult(tool_name=tool_name, success=False, error="MCP client not available")
        
        try:
            interface = await self._get_agent_interface("web", requesting_persona.persona_id)
            
            if tool_name == "web_search":
                results = await interface.search_web(
                    query=arguments["query"],
                    max_results=arguments.get("max_results", 10)
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result={"query": arguments["query"], "results": results, "count": len(results)}
                )
            
            else:
                return ToolResult(tool_name=tool_name, success=False, error=f"Unknown web tool: {tool_name}")
                
        except Exception as e:
            return ToolResult(tool_name=tool_name, success=False, error=str(e))
    
    async def _execute_database_tool(self,
                                   tool_name: str,
                                   arguments: Dict[str, Any],
                                   requesting_persona: ToolCapability) -> ToolResult:
        """Execute database tools"""
        if not self.mcp_client:
            return ToolResult(tool_name=tool_name, success=False, error="MCP client not available")
        
        try:
            interface = await self._get_agent_interface("database", requesting_persona.persona_id)
            
            if tool_name == "database_query":
                rows = await interface.database_query(
                    query=arguments["query"],
                    params=arguments.get("params", [])
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result={"rows": rows, "count": len(rows)}
                )
            
            else:
                return ToolResult(tool_name=tool_name, success=False, error=f"Unknown database tool: {tool_name}")
                
        except Exception as e:
            return ToolResult(tool_name=tool_name, success=False, error=str(e))
    
    async def _execute_docker_tool(self,
                                 tool_name: str,
                                 arguments: Dict[str, Any],
                                 requesting_persona: ToolCapability) -> ToolResult:
        """Execute Docker tools"""
        if not self.mcp_client:
            return ToolResult(tool_name=tool_name, success=False, error="MCP client not available")
        
        try:
            interface = await self._get_agent_interface("docker", requesting_persona.persona_id)
            
            if tool_name == "docker_run":
                output = await interface.docker_run(
                    image=arguments["image"],
                    command=arguments.get("command"),
                    env=arguments.get("env", {})
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=output is not None,
                    result={"output": output} if output else None,
                    error=None if output else "Docker run failed"
                )
            
            else:
                return ToolResult(tool_name=tool_name, success=False, error=f"Unknown docker tool: {tool_name}")
                
        except Exception as e:
            return ToolResult(tool_name=tool_name, success=False, error=str(e))
    
    async def _execute_code_tool(self,
                               tool_name: str,
                               arguments: Dict[str, Any],
                               requesting_persona: ToolCapability) -> ToolResult:
        """Execute code execution tools"""
        if not self.mcp_client:
            return ToolResult(tool_name=tool_name, success=False, error="MCP client not available")
        
        try:
            interface = await self._get_agent_interface("code", requesting_persona.persona_id)
            
            if tool_name == "code_execute":
                result = await interface.e2b_execute(
                    code=arguments["code"],
                    language=arguments.get("language", "python")
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=result is not None,
                    result=result,
                    error=None if result else "Code execution failed"
                )
            
            else:
                return ToolResult(tool_name=tool_name, success=False, error=f"Unknown code tool: {tool_name}")
                
        except Exception as e:
            return ToolResult(tool_name=tool_name, success=False, error=str(e))
    
    async def _execute_knowledge_tool(self,
                                    tool_name: str,
                                    arguments: Dict[str, Any],
                                    requesting_persona: ToolCapability) -> ToolResult:
        """Execute knowledge graph tools"""
        try:
            if tool_name == "knowledge_query":
                query = arguments["query"]
                # Simple keyword search in knowledge graph
                results = await self._query_knowledge_graph(query)
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result={"query": query, "results": results}
                )
            
            elif tool_name == "knowledge_add_node":
                node = await self.knowledge_graph.add_node(
                    name=arguments["name"],
                    node_type=arguments["node_type"],
                    attributes=arguments.get("attributes", {}),
                    importance=arguments.get("importance", 0.5)
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result=node.to_dict()
                )
            
            elif tool_name == "knowledge_add_edge":
                edge = await self.knowledge_graph.add_edge(
                    source_id=arguments["source_id"],
                    target_id=arguments["target_id"],
                    edge_type=arguments["edge_type"],
                    weight=arguments.get("weight", 1.0),
                    confidence=arguments.get("confidence", 0.5)
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result=edge.to_dict()
                )
            
            else:
                return ToolResult(tool_name=tool_name, success=False, error=f"Unknown knowledge tool: {tool_name}")
                
        except Exception as e:
            return ToolResult(tool_name=tool_name, success=False, error=str(e))
    
    async def _execute_mcp_tool(self,
                              tool_name: str,
                              arguments: Dict[str, Any],
                              requesting_persona: ToolCapability) -> ToolResult:
        """Execute tools via MCP client"""
        if not self.mcp_client:
            return ToolResult(tool_name=tool_name, success=False, error="MCP client not available")
        
        try:
            # Try to find the tool in available servers
            servers = self.mcp_client.get_available_servers()
            
            for server_name in servers:
                tools = await self.mcp_client.list_tools(server_name)
                if any(tool["name"] == tool_name for tool in tools):
                    result = await self.mcp_client.call_tool(server_name, tool_name, arguments)
                    return ToolResult(
                        tool_name=tool_name,
                        success=True,
                        result=result,
                        metadata={"server": server_name}
                    )
            
            return ToolResult(tool_name=tool_name, success=False, error=f"Tool {tool_name} not found in any MCP server")
            
        except Exception as e:
            return ToolResult(tool_name=tool_name, success=False, error=str(e))
    
    async def execute_tools_parallel(self,
                                   tool_requests: List[Tuple[str, Dict[str, Any]]],
                                   requesting_persona: ToolCapability,
                                   max_concurrent: int = 5) -> List[ToolResult]:
        """Execute multiple tools in parallel with concurrency control"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single(tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
            async with semaphore:
                return await self.execute_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    requesting_persona=requesting_persona,
                    store_result=True,
                    share_on_blackboard=False
                )
        
        tasks = [
            execute_single(tool_name, arguments) 
            for tool_name, arguments in tool_requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ToolResult(
                    tool_name=tool_requests[i][0],
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def delegate_to_coral_agent(self,
                                    agent_type: str,
                                    task_description: str,
                                    context: Dict[str, Any],
                                    requesting_persona: ToolCapability) -> ToolResult:
        """Delegate a complex task to a CoralCollective agent"""
        
        try:
            # Map task type to agent
            if agent_type not in self.coral_agents_map:
                return ToolResult(
                    tool_name=f"agent_{agent_type}",
                    success=False,
                    error=f"No agent mapping found for task type: {agent_type}"
                )
            
            agent_name = self.coral_agents_map[agent_type]
            
            # Create delegation record
            delegation = {
                "requesting_persona": requesting_persona.persona_name,
                "agent_type": agent_name,
                "task_description": task_description,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "delegation_id": str(uuid.uuid4())
            }
            
            # In a real implementation, this would trigger the CoralCollective agent
            # For now, we'll simulate the delegation
            logger.info(f"Delegating {agent_type} task to {agent_name} from {requesting_persona.persona_name}")
            
            # Store delegation in memory for tracking
            await self.memory_system.store_memory(
                persona_id=requesting_persona.persona_id,
                content=f"Delegated {agent_type} task: {task_description[:100]}...",
                context=delegation,
                importance=0.7,
                tags={"delegation", "coral_agent", agent_type}
            )
            
            # Update knowledge graph
            try:
                from .knowledge_graph import NodeType, EdgeType
                
                agent_node = await self.knowledge_graph.add_node(
                    name=f"CoralAgent_{agent_name}",
                    node_type=NodeType.PERSON,
                    attributes={"type": "coral_agent", "specialty": agent_type}
                )
                
                persona_node = await self.knowledge_graph.add_node(
                    name=requesting_persona.persona_name,
                    node_type=NodeType.PERSON,
                    attributes={"type": "persona"}
                )
                
                await self.knowledge_graph.add_edge(
                    source_id=persona_node.id,
                    target_id=agent_node.id,
                    edge_type=EdgeType.REQUIRES,
                    weight=1.0,
                    confidence=0.8,
                    attributes={"task": task_description}
                )
            except ImportError:
                # If knowledge graph types not available, skip graph update
                pass
            
            return ToolResult(
                tool_name=f"agent_{agent_type}",
                success=True,
                result={
                    "delegation_id": delegation["delegation_id"],
                    "agent_name": agent_name,
                    "status": "delegated",
                    "message": f"Task successfully delegated to {agent_name}"
                },
                metadata=delegation
            )
            
        except Exception as e:
            logger.error(f"Agent delegation failed: {e}")
            return ToolResult(
                tool_name=f"agent_{agent_type}",
                success=False,
                error=str(e)
            )
    
    async def _get_agent_interface(self, server_type: str, persona_id: str) -> AgentMCPInterface:
        """Get or create an agent interface for MCP communication"""
        interface_key = f"{server_type}_{persona_id}"
        
        if interface_key not in self.agent_interfaces:
            self.agent_interfaces[interface_key] = AgentMCPInterface(
                agent_type=f"persona_{persona_id}",
                client=self.mcp_client
            )
        
        return self.agent_interfaces[interface_key]
    
    def _generate_cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Generate cache key for tool execution"""
        key_data = {
            "tool": tool_name,
            "args": arguments
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    async def _store_tool_result_in_memory(self, 
                                         result: ToolResult, 
                                         requesting_persona: ToolCapability):
        """Store tool result in persona's memory"""
        try:
            content = f"Used tool {result.tool_name}: {result.result}"
            if isinstance(result.result, dict):
                content = f"Used tool {result.tool_name}: {json.dumps(result.result)[:200]}..."
            elif isinstance(result.result, str):
                content = f"Used tool {result.tool_name}: {result.result[:200]}..."
            
            await self.memory_system.store_memory(
                persona_id=requesting_persona.persona_id,
                content=content,
                context=result.to_dict(),
                importance=0.6 if result.success else 0.4,
                emotional_valence=0.2 if result.success else -0.2,
                tags={result.tool_name, "tool_usage", "success" if result.success else "failure"}
            )
            
        except Exception as e:
            logger.error(f"Failed to store tool result in memory: {e}")
    
    async def _share_result_on_blackboard(self,
                                        result: ToolResult,
                                        requesting_persona: ToolCapability):
        """Share tool result on the blackboard"""
        try:
            entry = BlackboardEntry(
                persona_id=requesting_persona.persona_id,
                entry_type=EntryType.INSIGHT,
                content=f"Tool result from {result.tool_name}: {json.dumps(result.result)[:300]}...",
                confidence=0.8 if result.success else 0.3,
                tags={result.tool_name, "tool_result"},
                metadata={
                    "tool_name": result.tool_name,
                    "execution_time": result.execution_time,
                    "success": result.success,
                    "persona_name": requesting_persona.persona_name
                }
            )
            
            await self.blackboard.post("tool_results", entry)
            
        except Exception as e:
            logger.error(f"Failed to share result on blackboard: {e}")
    
    async def _update_knowledge_graph(self,
                                    tool_name: str,
                                    arguments: Dict[str, Any],
                                    result: ToolResult,
                                    requesting_persona: ToolCapability):
        """Update knowledge graph with tool usage patterns"""
        try:
            # Import at runtime to avoid circular imports
            from .knowledge_graph import NodeType, EdgeType
            
            # Add tool node
            tool_node = await self.knowledge_graph.add_node(
                name=tool_name,
                node_type=NodeType.ACTIVITY,
                attributes={
                    "category": "tool",
                    "success_rate": requesting_persona.tool_metrics.get(tool_name, ToolUsageMetrics()).successful_calls / max(1, requesting_persona.tool_metrics.get(tool_name, ToolUsageMetrics()).total_calls),
                    "last_used": result.timestamp.isoformat()
                }
            )
            
            # Add persona node
            persona_node = await self.knowledge_graph.add_node(
                name=requesting_persona.persona_name,
                node_type=NodeType.PERSON,
                attributes={"type": "persona"}
            )
            
            # Add usage edge
            await self.knowledge_graph.add_edge(
                source_id=persona_node.id,
                target_id=tool_node.id,
                edge_type=EdgeType.INFLUENCES,
                weight=1.0 if result.success else 0.5,
                confidence=0.7,
                attributes={
                    "usage_count": requesting_persona.tool_metrics.get(tool_name, ToolUsageMetrics()).total_calls,
                    "last_result": "success" if result.success else "failure"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to update knowledge graph: {e}")
    
    async def _query_knowledge_graph(self, query: str) -> List[Dict[str, Any]]:
        """Simple keyword search in knowledge graph"""
        try:
            results = []
            query_lower = query.lower()
            
            for node_id, node in self.knowledge_graph.nodes.items():
                if (query_lower in node.name.lower() or 
                    any(query_lower in str(v).lower() for v in node.attributes.values())):
                    
                    # Get related nodes
                    related = await self.knowledge_graph.find_related(node_id, max_depth=1)
                    
                    results.append({
                        "node": node.to_dict(),
                        "related_count": len(related.get("nodes", [])),
                        "relevance": 1.0  # Simple relevance score
                    })
            
            return sorted(results, key=lambda x: x["relevance"], reverse=True)[:10]
            
        except Exception as e:
            logger.error(f"Knowledge graph query failed: {e}")
            return []
    
    async def get_tool_usage_analytics(self) -> Dict[str, Any]:
        """Get comprehensive tool usage analytics"""
        analytics = {
            "total_cached_results": len(self.tool_execution_cache),
            "active_agent_interfaces": len(self.agent_interfaces),
            "coral_agents_available": len(self.coral_agents_map),
            "mcp_client_status": self.mcp_client is not None,
            "cache_hit_rate": 0.0,  # Would track in real implementation
            "most_used_tools": [],  # Would aggregate from persona metrics
            "error_rates": {}  # Would track error patterns
        }
        
        if self.mcp_client:
            analytics["mcp_servers"] = self.mcp_client.get_available_servers()
            analytics["mcp_metrics"] = self.mcp_client.get_metrics()
        
        return analytics
    
    async def cleanup(self):
        """Clean up resources"""
        if self.mcp_client:
            await self.mcp_client.shutdown()
        
        for interface in self.agent_interfaces.values():
            await interface.close()
        
        self.agent_interfaces.clear()
        self.tool_execution_cache.clear()
        
        logger.info("PersonaToolIntegration cleaned up")


# Example enhanced persona that uses tool capabilities
class EnhancedPersona(ToolCapability):
    """Example of a persona enhanced with tool capabilities"""
    
    def __init__(self, persona_id: str, persona_name: str, expertise_domains: List[str]):
        super().__init__(persona_id, persona_name)
        self.expertise_domains = expertise_domains
        self._setup_specialized_permissions()
    
    def _setup_specialized_permissions(self):
        """Setup specialized tool permissions based on expertise"""
        # Add domain-specific permissions
        if "development" in self.expertise_domains:
            self.add_tool_permission(ToolPermission(
                "filesystem_write", 
                ToolCategory.FILE_SYSTEM, 
                ToolCapabilityLevel.FULL_ACCESS,
                rate_limit_per_minute=30
            ))
            self.add_tool_permission(ToolPermission(
                "git_create_pr",
                ToolCategory.VERSION_CONTROL,
                ToolCapabilityLevel.FULL_ACCESS,
                rate_limit_per_minute=10
            ))
            self.add_tool_permission(ToolPermission(
                "code_execute",
                ToolCategory.CODE_EXECUTION,
                ToolCapabilityLevel.LIMITED_WRITE,
                rate_limit_per_minute=20,
                requires_approval=True
            ))
        
        if "analysis" in self.expertise_domains:
            self.add_tool_permission(ToolPermission(
                "database_query",
                ToolCategory.DATABASE,
                ToolCapabilityLevel.READ_ONLY,
                rate_limit_per_minute=50
            ))
            self.add_tool_permission(ToolPermission(
                "web_search",
                ToolCategory.WEB_SEARCH,
                ToolCapabilityLevel.READ_ONLY,
                rate_limit_per_minute=30
            ))
    
    async def research_topic(self, topic: str) -> Dict[str, Any]:
        """Example method that uses multiple tools for research"""
        research_results = {
            "topic": topic,
            "web_results": [],
            "knowledge_results": [],
            "related_files": []
        }
        
        # Parallel tool execution for research
        tool_requests = [
            ("web_search", {"query": topic, "max_results": 5}),
            ("knowledge_query", {"query": topic}),
            ("filesystem_list", {"path": "."})  # Find related files
        ]
        
        results = await self.execute_tools_parallel(tool_requests, max_concurrent=3)
        
        for result in results:
            if result.success:
                if result.tool_name == "web_search":
                    research_results["web_results"] = result.result.get("results", [])
                elif result.tool_name == "knowledge_query":
                    research_results["knowledge_results"] = result.result.get("results", [])
                elif result.tool_name == "filesystem_list":
                    research_results["related_files"] = result.result.get("files", [])
        
        return research_results
    
    async def implement_feature(self, feature_description: str) -> ToolResult:
        """Example method that delegates complex development to CoralCollective"""
        return await self.delegate_to_agent(
            agent_type="backend_development",
            task_description=feature_description,
            context={
                "requesting_persona": self.persona_name,
                "expertise_context": self.expertise_domains,
                "priority": "medium"
            }
        )


# Factory function to create tool-enabled personas
def create_tool_enabled_persona(persona_id: str, 
                               persona_name: str, 
                               expertise_domains: List[str],
                               tool_integration: PersonaToolIntegration) -> EnhancedPersona:
    """Factory function to create a persona with tool capabilities"""
    # Create the enhanced persona (which is a ToolCapability)
    tool_capability = EnhancedPersona(persona_id, persona_name, expertise_domains)
    tool_capability.set_tool_integration(tool_integration)
    return tool_capability
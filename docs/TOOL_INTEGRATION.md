# Tool Integration Layer Documentation

## Overview

The Tool Integration Layer provides a comprehensive framework for Optimus Council of Minds personas to interact with external tools, MCP services, and CoralCollective agents. This system enables sophisticated tool usage patterns including parallel execution, intelligent caching, memory integration, and collaborative workflows.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│                  Persona Layer                      │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │   Base Persona   │  │    ToolCapability        │ │
│  │   (Enhanced)     │  │    (Mixin)               │ │
│  └──────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────┐
│               Tool Integration                      │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ PersonaToolInteg │  │   Permission System      │ │
│  │ration           │  │   Rate Limiting          │ │
│  └──────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────┐
│                  Tool Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │ MCP Tools   │ │ Knowledge   │ │ CoralCollective│ │
│  │ (External)  │ │ Graph Tools │ │ Agents         │ │
│  └─────────────┘ └─────────────┘ └────────────────┘ │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────┐
│               Storage Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │ Memory      │ │ Knowledge   │ │ Blackboard     │ │
│  │ System      │ │ Graph       │ │ Sharing        │ │
│  └─────────────┘ └─────────────┘ └────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Key Features

### 1. ToolCapability Base Class

All personas inherit from `ToolCapability`, providing:

- **Permission Management**: Fine-grained control over tool access
- **Rate Limiting**: Automatic rate limit enforcement per tool
- **Metrics Tracking**: Comprehensive usage analytics
- **Parallel Execution**: Concurrent tool execution with semaphore control
- **Result Caching**: Intelligent caching with TTL

### 2. Tool Categories

Tools are organized into logical categories:

- `FILE_SYSTEM`: File operations (read, write, list)
- `VERSION_CONTROL`: Git operations (create PR, issues)
- `WEB_SEARCH`: Web search and content retrieval
- `DATABASE`: Database queries and operations
- `CONTAINER`: Docker and containerized operations
- `CODE_EXECUTION`: Code execution in sandboxes
- `API_CALL`: External API interactions
- `AI_AGENT`: CoralCollective agent delegation
- `COMMUNICATION`: Messaging and notifications
- `MONITORING`: System monitoring and metrics

### 3. Permission System

```python
@dataclass
class ToolPermission:
    tool_name: str
    category: ToolCategory
    capability_level: ToolCapabilityLevel  # READ_ONLY, LIMITED_WRITE, FULL_ACCESS, ADMIN
    rate_limit_per_minute: int = 60
    requires_approval: bool = False
    approved_params: Set[str] = field(default_factory=set)
    restricted_params: Set[str] = field(default_factory=set)
```

### 4. Tool Result Handling

```python
@dataclass
class ToolResult:
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

## Usage Examples

### Basic Tool Execution

```python
# Create persona with tool capabilities
persona = create_tool_enabled_persona(
    persona_id="analyst",
    persona_name="Data Analyst", 
    expertise_domains=["analysis", "data_science"],
    tool_integration=tool_integration_system
)

# Execute a single tool
result = await persona.execute_tool(
    "filesystem_read",
    {"path": "data/metrics.json"},
    store_result=True,
    share_on_blackboard=True
)

if result.success:
    data = result.result
    print(f"Loaded {len(data)} characters from file")
```

### Parallel Tool Execution

```python
# Execute multiple tools concurrently
tool_requests = [
    ("web_search", {"query": "AI best practices", "max_results": 5}),
    ("database_query", {"query": "SELECT * FROM projects WHERE status='active'"}),
    ("filesystem_list", {"path": "src/models"}),
    ("knowledge_query", {"query": "machine learning"})
]

results = await persona.execute_tools_parallel(
    tool_requests=tool_requests,
    max_concurrent=3
)

successful_results = [r for r in results if r.success]
print(f"Completed {len(successful_results)}/{len(results)} tools successfully")
```

### CoralCollective Agent Delegation

```python
# Delegate complex tasks to specialized agents
backend_task = await persona.delegate_to_agent(
    agent_type="backend_development",
    task_description="Create REST API with authentication",
    context={
        "framework": "FastAPI",
        "database": "PostgreSQL",
        "requirements": ["secure", "scalable", "documented"]
    }
)

if backend_task.success:
    print(f"Task delegated to {backend_task.result['agent_name']}")
    print(f"Delegation ID: {backend_task.result['delegation_id']}")
```

### Enhanced Research Workflow

```python
class ResearchPersona(ToolCapability):
    async def research_topic(self, topic: str) -> Dict[str, Any]:
        """Comprehensive research using multiple tools"""
        
        # Parallel research across multiple sources
        research_tools = [
            ("web_search", {"query": topic, "max_results": 10}),
            ("knowledge_query", {"query": topic}),
            ("database_query", {"query": f"SELECT * FROM research WHERE topic LIKE '%{topic}%'"}),
        ]
        
        results = await self.execute_tools_parallel(research_tools)
        
        # Combine results
        research_data = {
            "topic": topic,
            "web_results": [],
            "knowledge_results": [],
            "database_results": [],
            "synthesis": None
        }
        
        for result in results:
            if result.success:
                if result.tool_name == "web_search":
                    research_data["web_results"] = result.result["results"]
                elif result.tool_name == "knowledge_query": 
                    research_data["knowledge_results"] = result.result["results"]
                elif result.tool_name == "database_query":
                    research_data["database_results"] = result.result["rows"]
        
        # Delegate synthesis to AI agent
        synthesis_task = await self.delegate_to_agent(
            agent_type="ai_ml",
            task_description=f"Synthesize research findings on {topic}",
            context=research_data
        )
        
        if synthesis_task.success:
            research_data["synthesis"] = synthesis_task.result
        
        return research_data
```

## MCP Integration

The system integrates with Model Context Protocol (MCP) servers for external tool access:

### Available MCP Tools

- **GitHub**: Repository operations, issue/PR management
- **Filesystem**: File system operations with security controls
- **Database**: PostgreSQL query execution
- **Docker**: Container management and execution
- **E2B**: Code execution in secure sandboxes
- **Brave Search**: Web search capabilities

### MCP Configuration

```yaml
# .coral/mcp/configs/mcp_config.yaml
mcp_servers:
  github:
    command: "npx"
    args: ["@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
    enabled: true
    permissions: ["read", "write"]
    
  filesystem:
    command: "npx" 
    args: ["@modelcontextprotocol/server-filesystem", "/allowed/path"]
    enabled: true
    permissions: ["read", "write"]
    
  brave-search:
    command: "npx"
    args: ["@modelcontextprotocol/server-brave-search"]
    env:
      BRAVE_API_KEY: "${BRAVE_API_KEY}"
    enabled: true
    permissions: ["read"]

agent_permissions:
  strategist:
    servers: ["filesystem", "brave-search", "github"]
  analyst:
    servers: ["filesystem", "brave-search", "postgres"]
  pragmatist:
    servers: ["all"]
```

## Memory Integration

Tool results are automatically stored in the persona's memory system:

```python
# Automatic memory storage
await self.memory_system.store_memory(
    persona_id=requesting_persona.persona_id,
    content=f"Used tool {result.tool_name}: {summary}",
    context=result.to_dict(),
    importance=0.6 if result.success else 0.4,
    emotional_valence=0.2 if result.success else -0.2,
    tags={result.tool_name, "tool_usage", "success" if result.success else "failure"}
)
```

### Memory Recall

```python
# Recall relevant tool usage history
memories = await memory_system.recall(
    persona_id="analyst",
    query="filesystem operations data analysis",
    context={"category": "tool_usage"},
    limit=10
)

for memory in memories:
    print(f"Previous: {memory.content}")
    if "tool_usage" in memory.tags:
        tool_context = memory.context
        print(f"  Tool: {tool_context.get('tool_name')}")
        print(f"  Success: {tool_context.get('success')}")
```

## Knowledge Graph Integration

Tool usage patterns are tracked in the knowledge graph:

```python
# Automatic knowledge graph updates
tool_node = await knowledge_graph.add_node(
    name=tool_name,
    node_type=NodeType.ACTIVITY,
    attributes={
        "category": "tool",
        "success_rate": metrics.success_rate,
        "last_used": timestamp
    }
)

persona_node = await knowledge_graph.add_node(
    name=persona.name,
    node_type=NodeType.PERSON,
    attributes={"type": "persona"}
)

# Track usage relationship
await knowledge_graph.add_edge(
    source_id=persona_node.id,
    target_id=tool_node.id,
    edge_type=EdgeType.INFLUENCES,
    weight=1.0 if success else 0.5,
    attributes={"usage_count": total_calls}
)
```

## Security and Compliance

### Permission Enforcement

```python
def check_permission(self, tool_name: str) -> bool:
    """Check if persona has permission to use tool"""
    if tool_name not in self.tool_permissions:
        return False
    
    permission = self.tool_permissions[tool_name]
    
    # Check rate limits
    if not self.check_rate_limit(tool_name):
        return False
    
    # Check approval requirements
    if permission.requires_approval:
        return self.has_approval(tool_name)
    
    return True
```

### Rate Limiting

```python
def check_rate_limit(self, tool_name: str) -> bool:
    """Enforce rate limits per tool"""
    permission = self.tool_permissions[tool_name]
    now = datetime.now(timezone.utc)
    minute_ago = now.replace(second=now.second - 60)
    
    # Clean old entries
    recent_usage = [
        ts for ts in self.rate_limits.get(tool_name, [])
        if ts > minute_ago
    ]
    
    return len(recent_usage) < permission.rate_limit_per_minute
```

### Audit Logging

All tool usage is comprehensively logged:

```python
audit_logger.info(
    f"Tool call: {server_name}/{tool_name} "
    f"by {persona.name} with args: {json.dumps(arguments)}"
)
```

## Performance Optimization

### Caching Strategy

```python
# Intelligent result caching
cache_key = self._generate_cache_key(tool_name, arguments)
if cache_key in self.tool_execution_cache:
    cached_result = self.tool_execution_cache[cache_key]
    age = (now - cached_result.timestamp).total_seconds()
    if age < self.cache_ttl:
        return cached_result
```

### Parallel Execution

```python
async def execute_tools_parallel(self, tool_requests, max_concurrent=5):
    """Execute multiple tools with concurrency control"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_single(tool_name, arguments):
        async with semaphore:
            return await self.execute_tool(tool_name, arguments)
    
    tasks = [execute_single(name, args) for name, args in tool_requests]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

## Error Handling

### Comprehensive Error Recovery

```python
async def execute_tool(self, tool_name, arguments, **kwargs):
    """Execute tool with comprehensive error handling"""
    try:
        # Permission checks
        if not self.check_permission(tool_name):
            return ToolResult(tool_name=tool_name, success=False, 
                            error="Permission denied")
        
        # Rate limit checks
        if not self.check_rate_limit(tool_name):
            return ToolResult(tool_name=tool_name, success=False,
                            error="Rate limit exceeded")
        
        # Execute tool
        result = await self._execute_tool_internal(tool_name, arguments)
        
        # Update metrics and cache
        self.update_metrics(result)
        if result.success:
            self.cache_result(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return ToolResult(tool_name=tool_name, success=False, error=str(e))
```

## Monitoring and Analytics

### Tool Usage Metrics

```python
@dataclass 
class ToolUsageMetrics:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_used: Optional[datetime] = None
    rate_limit_violations: int = 0
```

### Analytics Dashboard

```python
async def get_tool_usage_analytics(self) -> Dict[str, Any]:
    """Comprehensive analytics for monitoring"""
    return {
        "total_cached_results": len(self.tool_execution_cache),
        "active_agent_interfaces": len(self.agent_interfaces),
        "coral_agents_available": len(self.coral_agents_map),
        "mcp_client_status": self.mcp_client is not None,
        "cache_hit_rate": self.calculate_cache_hit_rate(),
        "most_used_tools": self.get_most_used_tools(),
        "error_patterns": self.analyze_error_patterns()
    }
```

## Testing and Demo

Run the comprehensive demo:

```bash
python examples/tool_integration_demo.py
```

The demo demonstrates:
- Basic tool execution
- Parallel tool execution
- CoralCollective agent delegation
- Memory system integration
- Knowledge graph updates
- Collaborative research workflows
- Analytics and monitoring

## Configuration

### Tool Permissions

```python
# Configure persona-specific permissions
persona.add_tool_permission(ToolPermission(
    tool_name="database_query",
    category=ToolCategory.DATABASE,
    capability_level=ToolCapabilityLevel.READ_ONLY,
    rate_limit_per_minute=50,
    requires_approval=False
))
```

### Integration Setup

```python
# Initialize tool integration system
tool_integration = PersonaToolIntegration(
    memory_system=memory_system,
    knowledge_graph=knowledge_graph,
    blackboard=blackboard,
    mcp_config_path=".coral/mcp/configs/mcp_config.yaml"
)

await tool_integration.initialize()

# Create enhanced persona
persona = create_tool_enabled_persona(
    persona_id="analyst",
    persona_name="Data Analyst",
    expertise_domains=["analysis", "research"],
    tool_integration=tool_integration
)
```

## Best Practices

1. **Permission Management**: Always configure least-privilege access
2. **Rate Limiting**: Set appropriate limits based on tool requirements
3. **Error Handling**: Implement comprehensive error recovery
4. **Caching**: Use caching for expensive or slow operations
5. **Monitoring**: Track tool usage patterns and performance
6. **Security**: Validate all tool inputs and outputs
7. **Documentation**: Document tool usage patterns and workflows

## Future Enhancements

- **Tool Recommendation**: AI-powered tool suggestion based on context
- **Workflow Orchestration**: Complex multi-tool workflows
- **Cross-Persona Collaboration**: Tool result sharing and collaboration
- **Dynamic Permission**: Context-aware permission adjustment
- **Performance Optimization**: Advanced caching and optimization strategies
- **Integration Expansion**: Additional MCP servers and tool categories

## File Locations

- **Core Integration**: `/src/council/tool_integration.py`
- **Enhanced Persona**: `/src/council/persona.py` (updated)
- **Demo Script**: `/examples/tool_integration_demo.py`
- **Documentation**: `/docs/TOOL_INTEGRATION.md`
- **MCP Configuration**: `/.coral/mcp/configs/mcp_config.yaml`

## Dependencies

- **Core**: `asyncio`, `logging`, `datetime`, `typing`
- **MCP**: Custom MCP client in `.coral/mcp/mcp_client.py`
- **Storage**: SQLite for memory and knowledge graph
- **Optional**: PyYAML for configuration, networkx for graphs
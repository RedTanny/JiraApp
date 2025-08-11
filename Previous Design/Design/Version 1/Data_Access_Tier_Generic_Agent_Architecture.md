# Data Access Tier - Generic Agent Architecture

## Overview

The Data Access Tier implements a **Generic Agent Architecture** that provides a unified interface for accessing data from multiple sources through Model Context Protocol (MCP) servers. The architecture is designed to be scalable, flexible, and intelligent, using LlamaStack for tool selection and MCP registration for dynamic capability discovery.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA ACCESS TIER                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                GenericAgent                             │ │
│  │                                                         │ │
│  │ • Queue consumer (receives string input)                │ │
│  │ • LlamaStack agent (no tool knowledge)                  │ │
│  │ • MCP registration management                           │ │
│  │ • Execution thread                                      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              MCP Registry                               │ │
│  │                                                         │ │
│  │ • Register MCPs with LlamaStack                         │ │
│  │ • Manage MCP endpoints                                  │ │
│  │ • Tool discovery via MCPs                               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   JIRA MCP      │  │ Confluence MCP  │  │  Other MCPs  │ │
│  │  (Port 8003)    │  │  (Port 8004)    │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. GenericAgent

The main component that orchestrates all data access operations.

**Key Responsibilities:**
- Queue-based input processing
- LlamaStack agent management
- MCP registration coordination
- Execution thread management
- Request/response handling

**Key Methods:**
```python
class GenericAgent:
    def start() -> bool                    # Start the agent
    def stop() -> None                     # Stop the agent
    def submit_input(input_string: str) -> str    # Submit input to queue
    def get_output(request_id: str) -> Optional[str]  # Get processed output
    def register_mcp(toolgroup_id: str, mcp_endpoint: str) -> bool
    def unregister_mcp(toolgroup_id: str) -> bool
    def get_status() -> Dict[str, Any]     # Get agent status
```

### 2. MCPRegistry

Manages MCP registration with LlamaStack server.

**Key Responsibilities:**
- Register/unregister MCPs with LlamaStack
- Manage MCP endpoint configurations
- Health checking and connection management
- Tool discovery and availability tracking

**Key Methods:**
```python
class MCPRegistry:
    def register_mcp(toolgroup_id: str, mcp_endpoint: str) -> bool
    def unregister_mcp(toolgroup_id: str) -> bool
    def list_registered_mcps() -> Dict[str, str]
    def health_check() -> bool
```

## Design Principles

### 1. Queue-Based Processing
- **Input Queue**: Receives string inputs for processing
- **Output Queue**: Stores processed results with request IDs
- **Asynchronous Processing**: Non-blocking execution thread
- **Request Tracking**: Unique IDs for input/output correlation

### 2. Generic Agent with No Tool Knowledge
- **Intelligent Routing**: LlamaStack decides which tools to use
- **Dynamic Capabilities**: Tools discovered through MCP registration
- **Flexible Input**: Natural language or structured commands
- **Extensible**: New capabilities added via MCP registration

### 3. MCP-Centric Architecture
- **Multiple MCP Support**: Can connect to multiple MCP servers
- **Dynamic Registration**: MCPs can be added/removed at runtime
- **Tool Discovery**: Automatic tool availability through MCPs
- **Standardized Interface**: All data access through MCP protocol

## Data Flow

### 1. Input Processing Flow
```
User Input → Input Queue → Execution Thread → LlamaStack Agent → MCP Tools → Output Queue → User
```

### 2. MCP Registration Flow
```
MCP Server → MCPRegistry → LlamaStack → Agent Configuration → Tool Availability
```

### 3. Request Processing Flow
```
1. submit_input("Search JIRA issues") → Request ID
2. Execution thread processes input
3. LlamaStack selects appropriate MCP tool
4. Tool executes and returns result
5. get_output(Request ID) → Processed result
```

## Configuration

### MCP Registration Examples

**JIRA MCP Registration:**
```bash
curl -X POST http://localhost:8321/v1/toolgroups \
  -H "Content-Type: application/json" \
  -d '{
    "toolgroup_id": "jira_mcp_group",
    "provider_id": "model-context-protocol",
    "mcp_endpoint": {
      "uri": "http://localhost:8003/sse"
    }
  }'
```

**Confluence MCP Registration:**
```bash
curl -X POST http://localhost:8321/v1/toolgroups \
  -H "Content-Type: application/json" \
  -d '{
    "toolgroup_id": "confluence_mcp_group",
    "provider_id": "model-context-protocol",
    "mcp_endpoint": {
      "uri": "http://localhost:8004/sse"
    }
  }'
```

### Agent Configuration

**Default Settings:**
- LlamaStack URL: `http://localhost:8321`
- Model: Auto-selected from available LLM models
- Temperature: 0.7
- Top-p: 0.9
- Tool choice: Auto

## Usage Examples

### Basic Usage

```python
from data_access import GenericAgent

# Create and start agent
agent = GenericAgent()
agent.start()

# Register MCPs
agent.register_mcp("jira_mcp_group", "http://localhost:8003/sse")
agent.register_mcp("confluence_mcp_group", "http://localhost:8004/sse")

# Submit input for processing
request_id = agent.submit_input("Search for JIRA issues assigned to user 'john'")

# Get output
output = agent.get_output(request_id, timeout=30.0)
print(output)

# Stop agent
agent.stop()
```

### Advanced Usage

```python
# Submit multiple inputs
inputs = [
    "Get JIRA project list",
    "Find Confluence pages about 'documentation'",
    "Search for high priority issues"
]

request_ids = []
for input_text in inputs:
    request_id = agent.submit_input(input_text)
    request_ids.append(request_id)

# Process outputs
for request_id in request_ids:
    output = agent.get_output(request_id)
    print(f"Output: {output}")

# Get agent status
status = agent.get_status()
print(f"Registered MCPs: {status['registered_mcps']}")
print(f"Queue sizes: {status['queue_size']} input, {status['output_queue_size']} output")
```

## Benefits

### 1. Scalability
- **Horizontal Scaling**: Multiple MCP servers can be registered
- **Dynamic Capabilities**: New tools added without code changes
- **Load Distribution**: Requests distributed across available MCPs

### 2. Flexibility
- **Input Flexibility**: Natural language or structured commands
- **Tool Flexibility**: Any MCP-compliant server can be integrated
- **Processing Flexibility**: Asynchronous, synchronous, or batch processing

### 3. Intelligence
- **Smart Tool Selection**: LlamaStack intelligently chooses appropriate tools
- **Context Awareness**: Agent maintains conversation context
- **Error Handling**: Intelligent error recovery and fallback

### 4. Maintainability
- **Separation of Concerns**: Clear boundaries between components
- **Modular Design**: Easy to add/remove/modify components
- **Testability**: Each component can be tested independently

## Error Handling

### 1. Connection Errors
- **LlamaStack Unavailable**: Graceful degradation with error messages
- **MCP Server Unavailable**: Registration fails, agent continues with available MCPs
- **Network Issues**: Retry logic with exponential backoff

### 2. Processing Errors
- **Input Queue Full**: Reject new inputs with appropriate error
- **Processing Timeout**: Return timeout error to client
- **Tool Execution Errors**: Return error details from MCP server

### 3. Recovery Strategies
- **Automatic Reconnection**: Attempt to reconnect to failed services
- **Queue Recovery**: Preserve queued requests during reconnection
- **State Recovery**: Restore agent state after restart

## Performance Considerations

### 1. Queue Management
- **Queue Size Limits**: Prevent memory exhaustion
- **Processing Rate**: Control processing speed to match MCP capacity
- **Timeout Handling**: Prevent indefinite waiting

### 2. Resource Management
- **Connection Pooling**: Reuse connections to LlamaStack and MCPs
- **Memory Management**: Efficient queue and response storage
- **Thread Management**: Proper thread lifecycle management

### 3. Monitoring
- **Queue Metrics**: Monitor input/output queue sizes
- **Processing Metrics**: Track processing times and success rates
- **MCP Metrics**: Monitor MCP availability and performance

## Future Enhancements

### 1. Caching Layer
- **Response Caching**: Cache frequently requested data
- **Tool Result Caching**: Cache MCP tool results
- **Intelligent Caching**: Cache based on usage patterns

### 2. Advanced Features
- **Priority Queuing**: Handle high-priority requests first
- **Batch Processing**: Process multiple related requests together
- **Streaming Responses**: Support for streaming MCP responses

### 3. Integration Features
- **Event-Driven Architecture**: Support for event-based processing
- **Webhook Integration**: Support for webhook-based MCPs
- **API Gateway**: REST API wrapper for the Generic Agent

## Dependencies

### Required Dependencies
- `llama-stack-client`: LlamaStack client library
- `httpx`: HTTP client for MCP registration
- `threading`: Thread management for execution loop
- `queue`: Queue management for input/output
- `logging`: Logging and debugging support

### Optional Dependencies
- `asyncio`: For future async support
- `pydantic`: For data validation (future)
- `redis`: For distributed caching (future)

## Testing Strategy

### 1. Unit Testing
- **Component Testing**: Test each component independently
- **Mock Testing**: Use mocks for external dependencies
- **Edge Case Testing**: Test error conditions and edge cases

### 2. Integration Testing
- **End-to-End Testing**: Test complete data flow
- **MCP Integration**: Test with real MCP servers
- **LlamaStack Integration**: Test with real LlamaStack server

### 3. Performance Testing
- **Load Testing**: Test with high request volumes
- **Stress Testing**: Test under resource constraints
- **Scalability Testing**: Test with multiple MCPs

## Conclusion

The Generic Agent Architecture provides a robust, scalable, and intelligent foundation for data access in the 3-tier system. By leveraging LlamaStack for intelligent tool selection and MCP registration for dynamic capability discovery, the architecture achieves the goals of flexibility, maintainability, and extensibility while maintaining clean separation of concerns.

The queue-based processing model ensures reliable handling of concurrent requests, while the MCP-centric approach allows for easy integration of new data sources and capabilities. The architecture is designed to evolve with future requirements while maintaining backward compatibility and performance. 
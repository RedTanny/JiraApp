# Data Access Tier - Technical Specification

## Implementation Details

### File Structure

```
Client/data_access/
├── __init__.py              # Package exports
├── generic_agent.py         # Main GenericAgent implementation
├── demo_generic_agent.py    # Demo and testing script
└── __pycache__/            # Python cache files
```

### Core Classes

#### GenericAgent Class

**Purpose**: Main orchestrator for data access operations

**Key Attributes**:
```python
class GenericAgent:
    llama_stack_url: str                    # LlamaStack server URL
    mcp_registry: MCPRegistry               # MCP registration manager
    llama_client: Optional[LlamaStackClient] # LlamaStack client
    agent: Optional[Agent]                  # LlamaStack agent
    session_id: Optional[str]               # Agent session ID
    input_queue: queue.Queue               # Input processing queue
    output_queue: queue.Queue              # Output storage queue
    execution_thread: Optional[Thread]     # Processing thread
    running: bool                          # Agent running state
    logger: Logger                         # Logging instance
```

**Key Methods**:

1. **Lifecycle Management**:
   ```python
   def start() -> bool                    # Initialize and start agent
   def stop() -> None                     # Gracefully stop agent
   def is_connected() -> bool             # Check connection status
   ```

2. **Input/Output Processing**:
   ```python
   def submit_input(input_string: str) -> str    # Submit input to queue
   def get_output(request_id: str, timeout: float = 30.0) -> Optional[str]
   ```

3. **MCP Management**:
   ```python
   def register_mcp(toolgroup_id: str, mcp_endpoint: str) -> bool
   def unregister_mcp(toolgroup_id: str) -> bool
   ```

4. **Status and Monitoring**:
   ```python
   def get_status() -> Dict[str, Any]     # Get comprehensive status
   ```

#### MCPRegistry Class

**Purpose**: Manages MCP registration with LlamaStack

**Key Attributes**:
```python
class MCPRegistry:
    llama_stack_url: str                  # LlamaStack server URL
    client: httpx.Client                  # HTTP client for API calls
    registered_mcps: Dict[str, str]       # Registered MCP mappings
    logger: Logger                        # Logging instance
```

**Key Methods**:
```python
def register_mcp(toolgroup_id: str, mcp_endpoint: str) -> bool
def unregister_mcp(toolgroup_id: str) -> bool
def list_registered_mcps() -> Dict[str, str]
def health_check() -> bool
```

## Implementation Details

### Queue Management

**Input Queue Processing**:
```python
def submit_input(self, input_string: str) -> str:
    request_id = f"req_{int(time.time() * 1000)}"
    self.input_queue.put((request_id, input_string))
    return request_id
```

**Output Queue Processing**:
```python
def get_output(self, request_id: str, timeout: float = 30.0) -> Optional[str]:
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not self.output_queue.empty():
            output_id, output = self.output_queue.get_nowait()
            if output_id == request_id:
                return output
            else:
                self.output_queue.put((output_id, output))
        time.sleep(0.1)
    return None
```

### Execution Thread

**Main Processing Loop**:
```python
def _execution_loop(self) -> None:
    while self.running:
        try:
            request_id, input_string = self.input_queue.get(timeout=1.0)
            output = self._process_input(input_string)
            self.output_queue.put((request_id, output))
        except queue.Empty:
            continue
        except Exception as e:
            self.logger.error(f"Error in execution loop: {e}")
            time.sleep(1.0)
```

### LlamaStack Integration

**Agent Initialization**:
```python
def _initialize_agent(self) -> bool:
    # Get available models
    available_models = [
        model.identifier for model in self.llama_client.models.list() 
        if model.model_type == "llm"
    ]
    
    # Get registered MCP toolgroups
    registered_mcps = self.mcp_registry.list_registered_mcps()
    toolgroups = list(registered_mcps.keys())
    
    # Create agent configuration
    agent_config = AgentConfig(
        model=selected_model,
        instructions="""You are a helpful assistant with access to various tools through MCPs.
        Use the appropriate tools to fetch and process data as requested.
        You don't need to know about specific tools - they are provided by MCPs.""",
        sampling_params={
            "strategy": {"type": "top_p", "temperature": 0.7, "top_p": 0.9},
        },
        toolgroups=toolgroups,
        tool_choice="auto",
        enable_session_persistence=True,
    )
    
    # Create agent and session
    self.agent = Agent(self.llama_client, agent_config)
    self.session_id = self.agent.create_session("generic-agent-session")
```

### MCP Registration

**Registration Process**:
```python
def register_mcp(self, toolgroup_id: str, mcp_endpoint: str) -> bool:
    payload = {
        "toolgroup_id": toolgroup_id,
        "provider_id": "model-context-protocol",
        "mcp_endpoint": {
            "uri": mcp_endpoint
        }
    }
    
    response = self.client.post("/v1/toolgroups", json=payload)
    
    if response.status_code == 200:
        self.registered_mcps[toolgroup_id] = mcp_endpoint
        return True
    return False
```

## Configuration

### Environment Variables

```bash
# LlamaStack Configuration
LLAMA_STACK_URL=http://localhost:8321
LLAMA_STACK_TIMEOUT=30

# MCP Configuration
JIRA_MCP_ENDPOINT=http://localhost:8003/sse
CONFLUENCE_MCP_ENDPOINT=http://localhost:8004/sse

# Agent Configuration
AGENT_TEMPERATURE=0.7
AGENT_TOP_P=0.9
AGENT_SESSION_NAME=generic-agent-session

# Queue Configuration
INPUT_QUEUE_TIMEOUT=1.0
OUTPUT_QUEUE_TIMEOUT=30.0
EXECUTION_LOOP_DELAY=0.1
```

### Configuration Class

```python
@dataclass
class AgentConfig:
    llama_stack_url: str = "http://localhost:8321"
    llama_stack_timeout: int = 30
    agent_temperature: float = 0.7
    agent_top_p: float = 0.9
    agent_session_name: str = "generic-agent-session"
    input_queue_timeout: float = 1.0
    output_queue_timeout: float = 30.0
    execution_loop_delay: float = 0.1
```

## Error Handling

### Exception Types

1. **ConnectionError**: LlamaStack or MCP server unavailable
2. **TimeoutError**: Request processing timeout
3. **QueueFullError**: Input queue capacity exceeded
4. **MCPRegistrationError**: MCP registration failed
5. **AgentInitializationError**: Agent initialization failed

### Error Recovery Strategies

**Connection Recovery**:
```python
def _reconnect_with_backoff(self, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            if self._connect_to_llama_stack():
                return True
        except Exception as e:
            self.logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
    return False
```

**Queue Recovery**:
```python
def _recover_queue_state(self) -> None:
    # Preserve queued requests during reconnection
    preserved_requests = []
    while not self.input_queue.empty():
        try:
            preserved_requests.append(self.input_queue.get_nowait())
        except queue.Empty:
            break
    
    # Restore requests after reconnection
    for request in preserved_requests:
        self.input_queue.put(request)
```

## Performance Optimizations

### 1. Connection Pooling

```python
class ConnectionPool:
    def __init__(self, max_connections: int = 10):
        self.pool = {}
        self.max_connections = max_connections
    
    def get_connection(self, url: str) -> httpx.Client:
        if url not in self.pool:
            if len(self.pool) >= self.max_connections:
                self._evict_oldest()
            self.pool[url] = httpx.Client(base_url=url, timeout=30.0)
        return self.pool[url]
```

### 2. Request Batching

```python
def submit_batch(self, inputs: List[str]) -> List[str]:
    request_ids = []
    for input_text in inputs:
        request_id = self.submit_input(input_text)
        request_ids.append(request_id)
    return request_ids
```

### 3. Response Caching

```python
class ResponseCache:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[str]:
        return self.cache.get(key)
    
    def put(self, key: str, value: str) -> None:
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
```

## Monitoring and Metrics

### Metrics Collection

```python
class AgentMetrics:
    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.avg_processing_time = 0.0
        self.queue_size_history = []
    
    def record_request(self, processing_time: float, success: bool):
        self.request_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        # Update average processing time
        self.avg_processing_time = (
            (self.avg_processing_time * (self.request_count - 1) + processing_time) 
            / self.request_count
        )
    
    def get_success_rate(self) -> float:
        return self.success_count / self.request_count if self.request_count > 0 else 0.0
```

### Health Checks

```python
def health_check(self) -> Dict[str, Any]:
    return {
        "status": "healthy" if self.running else "stopped",
        "llama_stack_connected": self.llama_client is not None,
        "agent_initialized": self.agent is not None,
        "registered_mcps_count": len(self.mcp_registry.list_registered_mcps()),
        "input_queue_size": self.input_queue.qsize(),
        "output_queue_size": self.output_queue.qsize(),
        "execution_thread_alive": self.execution_thread.is_alive() if self.execution_thread else False
    }
```

## Testing

### Unit Tests

```python
def test_agent_initialization():
    agent = GenericAgent()
    assert agent.running == False
    assert agent.llama_client is None
    assert agent.agent is None

def test_input_submission():
    agent = GenericAgent()
    request_id = agent.submit_input("test input")
    assert request_id.startswith("req_")
    assert agent.input_queue.qsize() == 1

def test_mcp_registration():
    agent = GenericAgent()
    success = agent.register_mcp("test_mcp", "http://localhost:8000/sse")
    assert success == True
    assert "test_mcp" in agent.mcp_registry.list_registered_mcps()
```

### Integration Tests

```python
def test_end_to_end_processing():
    agent = GenericAgent()
    agent.start()
    
    # Register test MCP
    agent.register_mcp("test_mcp", "http://localhost:8000/sse")
    
    # Submit input
    request_id = agent.submit_input("test query")
    
    # Get output
    output = agent.get_output(request_id, timeout=10.0)
    assert output is not None
    
    agent.stop()
```

### Performance Tests

```python
def test_concurrent_requests():
    agent = GenericAgent()
    agent.start()
    
    # Submit multiple concurrent requests
    request_ids = []
    for i in range(10):
        request_id = agent.submit_input(f"test input {i}")
        request_ids.append(request_id)
    
    # Measure processing time
    start_time = time.time()
    outputs = []
    for request_id in request_ids:
        output = agent.get_output(request_id, timeout=30.0)
        outputs.append(output)
    
    processing_time = time.time() - start_time
    assert processing_time < 30.0  # Should complete within 30 seconds
    assert len(outputs) == 10
    
    agent.stop()
```

## Deployment

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY Client/ ./Client/

# Set environment variables
ENV LLAMA_STACK_URL=http://localhost:8321
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "Client/demo_generic_agent.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  generic-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LLAMA_STACK_URL=http://llama-stack:8321
      - JIRA_MCP_ENDPOINT=http://jira-mcp:8003/sse
    depends_on:
      - llama-stack
      - jira-mcp
  
  llama-stack:
    image: llama-stack:latest
    ports:
      - "8321:8321"
  
  jira-mcp:
    build: ./MCP
    ports:
      - "8003:8003"
```

## Security Considerations

### 1. Input Validation

```python
def validate_input(self, input_string: str) -> bool:
    # Check for malicious content
    if len(input_string) > 10000:  # Max input length
        return False
    
    # Check for SQL injection patterns
    sql_patterns = ["'", ";", "--", "/*", "*/"]
    if any(pattern in input_string.lower() for pattern in sql_patterns):
        return False
    
    return True
```

### 2. Authentication

```python
def authenticate_request(self, api_key: str) -> bool:
    # Validate API key
    valid_keys = os.getenv("VALID_API_KEYS", "").split(",")
    return api_key in valid_keys
```

### 3. Rate Limiting

```python
class RateLimiter:
    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests = []
    
    def is_allowed(self) -> bool:
        now = time.time()
        # Remove old requests
        self.requests = [req for req in self.requests if now - req < self.window]
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(now)
        return True
```

## Conclusion

This technical specification provides a comprehensive guide for implementing and maintaining the Data Access Tier Generic Agent Architecture. The implementation focuses on reliability, performance, and maintainability while providing a flexible foundation for future enhancements.

The architecture successfully separates concerns, provides intelligent tool selection through LlamaStack, and maintains clean interfaces for integration with the Business Logic and Presentation tiers. 
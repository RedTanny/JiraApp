"""
Generic Agent for Data Access Tier
Receives input from queue, uses LlamaStack, manages MCP registration
"""

import asyncio
import logging
import queue
import threading
import time
import os
from typing import Dict, List, Optional, Any
import httpx
import json

try:
    from llama_stack_client import LlamaStackClient
    from llama_stack_client.lib.agents.agent import Agent
    from llama_stack_client.types.agent_create_params import AgentConfig
except ImportError as e:
    raise ImportError(f"llama-stack-client not available: {e}")


class MCPRegistry:
    """
    Manages MCP registration with LlamaStack
    """
    
    def __init__(self, llama_stack_url: str = "http://localhost:8321"):
        self.llama_stack_url = llama_stack_url
        self.client = httpx.Client(base_url=llama_stack_url, timeout=30.0)
        self.logger = logging.getLogger(__name__)
        self.registered_mcps = {}
    
    def register_mcp(self, toolgroup_id: str, mcp_endpoint: str) -> bool:
        """
        Register an MCP with LlamaStack
        
        Args:
            toolgroup_id: Unique identifier for the MCP toolgroup
            mcp_endpoint: MCP endpoint URI (e.g., "http://localhost:8003/sse")
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
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
                self.logger.info(f"Successfully registered MCP: {toolgroup_id} -> {mcp_endpoint}")
                return True
            else:
                self.logger.error(f"Failed to register MCP {toolgroup_id}: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error registering MCP {toolgroup_id}: {e}")
            return False
    
    def unregister_mcp(self, toolgroup_id: str) -> bool:
        """
        Unregister an MCP from LlamaStack
        
        Args:
            toolgroup_id: Toolgroup ID to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            response = self.client.delete(f"/v1/toolgroups/{toolgroup_id}")
            
            if response.status_code == 200:
                if toolgroup_id in self.registered_mcps:
                    del self.registered_mcps[toolgroup_id]
                self.logger.info(f"Successfully unregistered MCP: {toolgroup_id}")
                return True
            else:
                self.logger.error(f"Failed to unregister MCP {toolgroup_id}: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error unregistering MCP {toolgroup_id}: {e}")
            return False
    
    def list_registered_mcps(self) -> Dict[str, str]:
        """
        Get list of registered MCPs
        
        Returns:
            Dictionary of toolgroup_id -> endpoint mappings
        """
        return self.registered_mcps.copy()
    
    def health_check(self) -> bool:
        """
        Check if LlamaStack is available
        
        Returns:
            True if LlamaStack is healthy, False otherwise
        """
        try:
            response = self.client.get("/v1/models")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"LlamaStack health check failed: {e}")
            return False


class GenericAgent:
    """
    Generic Agent that processes input from queue using LlamaStack
    No tool knowledge - all capabilities come from registered MCPs
    """
    
    def __init__(self, llama_stack_url: str = None):
        """
        Initialize Generic Agent
        
        Args:
            llama_stack_url: LlamaStack server URL (optional, uses LLAMA_STACK_URL env var if not provided)
        """
        # Get configuration from environment variables with defaults
        self.llama_stack_url = llama_stack_url or os.getenv("LLAMA_STACK_URL", "http://localhost:8321")
        self.mcp_registry = MCPRegistry(self.llama_stack_url)
        self.llama_client: Optional[LlamaStackClient] = None
        self.agent: Optional[Agent] = None
        self.session_id: Optional[str] = None
        
        # Producer-consumer pattern with queues
        self.input_queue = queue.Queue()
        self.results_queue = queue.Queue()  # Single queue for all results
        self.execution_thread: Optional[threading.Thread] = None
        self.running = False
        
        self.logger = logging.getLogger(__name__)
    
    def start(self) -> bool:
        """
        Start the Generic Agent
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Connect to LlamaStack
            if not self._connect_to_llama_stack():
                return False
            
            # Initialize agent
            if not self._initialize_agent():
                return False
            
            # Start execution thread
            self.running = True
            self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
            self.execution_thread.start()
            
            self.logger.info("Generic Agent started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Generic Agent: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the Generic Agent"""
        self.running = False
        if self.execution_thread:
            self.execution_thread.join(timeout=5.0)
        
        if self.llama_client:
            self.llama_client = None
            self.agent = None
            self.session_id = None
        
        self.logger.info("Generic Agent stopped")
    
    def register_mcp(self, toolgroup_id: str, mcp_endpoint: str) -> bool:
        """
        Register an MCP with the agent
        
        Args:
            toolgroup_id: Unique identifier for the MCP
            mcp_endpoint: MCP endpoint URI
            
        Returns:
            True if registration successful, False otherwise
        """
        success = self.mcp_registry.register_mcp(toolgroup_id, mcp_endpoint)
        
        if success and self.agent:
            # Re-initialize agent to pick up new MCP
            self._initialize_agent()
        
        return success
    
    def unregister_mcp(self, toolgroup_id: str) -> bool:
        """
        Unregister an MCP from the agent
        
        Args:
            toolgroup_id: Toolgroup ID to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        success = self.mcp_registry.unregister_mcp(toolgroup_id)
        
        if success and self.agent:
            # Re-initialize agent to reflect MCP removal
            self._initialize_agent()
        
        return success
    
    def submit_input(self, input_string: str) -> str:
        """
        Submit input to the agent for processing
        
        Args:
            input_string: Input string to process
            
        Returns:
            Request ID for tracking the request
        """
        if not self.running:
            raise Exception("Agent is not running")
        
        # Generate unique request ID
        request_id = f"req_{int(time.time() * 1000)}_{threading.get_ident()}"
        
        # Submit to input queue
        self.input_queue.put((request_id, input_string))
        
        self.logger.info(f"Submitted input with request ID: {request_id}")
        return request_id
    
    def wait_for_output(self, request_id: str, timeout: float = None) -> Optional[str]:
        """
        Wait for output using producer-consumer pattern with queue
        
        Args:
            request_id: Request ID returned by submit_input
            timeout: Timeout in seconds (optional, uses LLAMA_STACK_OUTPUT_TIMEOUT env var if not provided)
            
        Returns:
            Output string or None if timeout/not found
        """
        # Get timeout from environment variable if not provided
        if timeout is None:
            timeout = float(os.getenv("LLAMA_STACK_OUTPUT_TIMEOUT", "30.0"))
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check results queue for the specific request
            try:
                result_id, result = self.results_queue.get(timeout=0.1)
                if result_id == request_id:
                    return result
                else:
                    # Put back if not our request
                    self.results_queue.put((result_id, result))
            except queue.Empty:
                continue
        
        # Timeout occurred
        self.logger.warning(f"Timeout waiting for output: {request_id}")
        return None
    
    def get_output(self, request_id: str, timeout: float = None) -> Optional[str]:
        """
        Get output for a specific request
        
        Args:
            request_id: Request ID returned by submit_input
            timeout: Timeout in seconds (optional, uses LLAMA_STACK_OUTPUT_TIMEOUT env var if not provided)
            
        Returns:
            Output string or None if timeout/not found
        """
        # Get timeout from environment variable if not provided
        if timeout is None:
            timeout = float(os.getenv("LLAMA_STACK_OUTPUT_TIMEOUT", "30.0"))
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check output queue for matching request
                if not self.input_queue.empty(): # Changed from output_queue to input_queue
                    request_id_from_queue, output = self.input_queue.get_nowait() # Changed from output_id to request_id_from_queue
                    if request_id_from_queue == request_id:
                        return output
                    else:
                        # Put back if not our request
                        self.input_queue.put((request_id_from_queue, output)) # Changed from output_id to request_id_from_queue
                
                time.sleep(0.1)  # Small delay to avoid busy waiting
                
            except queue.Empty:
                break
        
        self.logger.warning(f"Timeout waiting for output: {request_id}")
        return None
    
    def _connect_to_llama_stack(self) -> bool:
        """Connect to LlamaStack server"""
        try:
            self.llama_client = LlamaStackClient(base_url=self.llama_stack_url)
            
            # Test connection
            models = self.llama_client.models.list()
            if not models:
                raise Exception("No models available in LlamaStack")
            
            self.logger.info(f"Connected to LlamaStack at {self.llama_stack_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to LlamaStack: {e}")
            return False
    
    def _initialize_agent(self) -> bool:
        """Initialize LlamaStack agent with registered MCPs"""
        try:
            if not self.llama_client:
                raise Exception("LlamaStack client not connected")
            
            # Get available models
            available_models = [
                model.identifier for model in self.llama_client.models.list() 
                if model.model_type == "llm"
            ]
            
            if not available_models:
                raise Exception("No available LLM models")
            
            # Select model based on environment variable or default to first available
            preferred_model = os.getenv("LLAMA_STACK_MODEL")
            if preferred_model:
                if preferred_model in available_models:
                    selected_model = preferred_model
                    self.logger.info(f"Using preferred model from environment: {selected_model}")
                else:
                    self.logger.warning(f"Preferred model '{preferred_model}' not available. Available models: {available_models}")
                    selected_model = available_models[0]
                    self.logger.info(f"Falling back to first available model: {selected_model}")
            else:
                selected_model = available_models[0]
                self.logger.info(f"No preferred model specified, using first available: {selected_model}")
            
            # Get registered MCP toolgroups
            registered_mcps = self.mcp_registry.list_registered_mcps()
            toolgroups = list(registered_mcps.keys())
            
            # Get configuration from environment variables with defaults
            temperature = float(os.getenv("LLAMA_STACK_TEMPERATURE", "0.7"))
            top_p = float(os.getenv("LLAMA_STACK_TOP_P", "0.9"))
            session_name = os.getenv("LLAMA_STACK_SESSION_NAME", "generic-agent-session")
            
            # Create agent configuration
            agent_config = AgentConfig(
                model=selected_model,
                instructions="""You are a helpful assistant with access to various tools through MCPs.
                Use the appropriate tools to fetch and process data as requested.
                You don't need to know about specific tools - they are provided by MCPs.""",
                sampling_params={
                    "strategy": {"type": "top_p", "temperature": temperature, "top_p": top_p},
                },
                toolgroups=toolgroups,
                tool_choice="auto",
                enable_session_persistence=True,
                stream=False,  # Disable streaming for simpler response handling
            )
            
            # Create agent and session
            self.agent = Agent(self.llama_client, agent_config)
            self.session_id = self.agent.create_session(session_name)
            
            self.logger.info(f"Agent initialized with model: {selected_model}")
            self.logger.info(f"Registered MCPs: {toolgroups}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {e}")
            return False
    
    def _execution_loop(self) -> None:
        """Main execution loop for processing input queue"""
        self.logger.info("Starting execution loop")
        
        while self.running:
            try:
                # Get input from queue (non-blocking)
                try:
                    request_id, input_string = self.input_queue.get(timeout=1.0)
                except queue.Empty:
                    # Small delay to avoid busy waiting when queue is empty
                    time.sleep(0.1)
                    continue
                
                # Process input
                self.logger.info(f"Processing request: {request_id}")
                output = self._process_input(input_string)
                
                # Store result and signal completion
                self.results_queue.put((request_id, output))
                
            except Exception as e:
                self.logger.error(f"Error in execution loop: {e}")
                time.sleep(1.0)  # Avoid tight error loop
        
        self.logger.info("Execution loop stopped")
    
    def _process_input(self, input_string: str) -> str:
        """
        Process input string using LlamaStack agent
        
        Args:
            input_string: Input to process
            
        Returns:
            Processed output string
        """
        try:
            if not self.agent or not self.session_id:
                return "Error: Agent not initialized"
            
            # Create turn with input (non-streaming)
            response = self.agent.create_turn(
                messages=[
                    {
                        "role": "user",
                        "content": input_string
                    }
                ],
                session_id=self.session_id,
                stream=False,  # Explicitly disable streaming
            )
            
            # Handle response (streaming or non-streaming)
            if response:
                self.logger.debug(f"Response type: {type(response)}")
                
                # Check if it's a generator (streaming response)
                if hasattr(response, '__iter__') and not hasattr(response, 'content'):
                    self.logger.debug("Detected streaming response, consuming generator")
                    full_response = ""
                    
                    try:
                        # Consume the generator to get full response
                        for chunk in response:
                            self.logger.debug(f"Processing chunk: {type(chunk)}")
                            
                            # Extract content from chunk
                            if hasattr(chunk, 'content') and chunk.content:
                                full_response += chunk.content
                            elif hasattr(chunk, 'message') and chunk.message:
                                if hasattr(chunk.message, 'content'):
                                    full_response += chunk.message.content
                                else:
                                    full_response += str(chunk.message)
                            elif hasattr(chunk, 'choices') and chunk.choices:
                                for choice in chunk.choices:
                                    if hasattr(choice, 'message') and choice.message:
                                        if hasattr(choice.message, 'content'):
                                            full_response += choice.message.content
                                        else:
                                            full_response += str(choice.message)
                            elif hasattr(chunk, 'delta') and chunk.delta:
                                if hasattr(chunk.delta, 'content') and chunk.delta.content:
                                    full_response += chunk.delta.content
                            else:
                                # Fallback: convert chunk to string
                                full_response += str(chunk)

                        #self.logger.info(f"Full response: {full_response}")
                        return full_response if full_response else "Error: Empty response from generator"
                        
                    except Exception as stream_error:
                        self.logger.error(f"Error consuming streaming response: {stream_error}")
                        return f"Error: Failed to consume streaming response - {str(stream_error)}"
                
                # Handle non-streaming response
                else:
                    # Try different ways to extract content
                    if hasattr(response, 'content') and response.content:
                        return response.content
                    elif hasattr(response, 'message') and response.message:
                        if hasattr(response.message, 'content'):
                            return response.message.content
                        else:
                            return str(response.message)
                    elif hasattr(response, 'messages') and response.messages:
                        # Get the last assistant message
                        for msg in reversed(response.messages):
                            if msg.get('role') == 'assistant' and msg.get('content'):
                                return msg['content']
                    elif hasattr(response, 'choices') and response.choices:
                        # Handle choices format
                        for choice in response.choices:
                            if hasattr(choice, 'message') and choice.message:
                                if hasattr(choice.message, 'content'):
                                    return choice.message.content
                                else:
                                    return str(choice.message)
                    else:
                        # Fallback: convert to string
                        return str(response)
            else:
                return "Error: No response from agent"
                
        except Exception as e:
            self.logger.error(f"Error processing input: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status information
        
        Returns:
            Status dictionary
        """
        return {
            "running": self.running,
            "connected": self.llama_client is not None,
            "agent_initialized": self.agent is not None,
            "registered_mcps": self.mcp_registry.list_registered_mcps(),
            "queue_size": self.input_queue.qsize(),
            "output_queue_size": self.results_queue.qsize() # Changed from output_queue to results_queue
        } 

# Singleton instance
_agent_instance = None
_agent_lock = threading.Lock()

def get_agent_singleton(llama_stack_url: str = None) -> GenericAgent:
    """
    Get singleton GenericAgent instance
    
    Args:
        llama_stack_url: Optional LlamaStack URL (only used on first creation)
        
    Returns:
        GenericAgent instance (singleton)
    """
    global _agent_instance
    
    if _agent_instance is None:
        with _agent_lock:
            if _agent_instance is None:
                _agent_instance = GenericAgent(llama_stack_url)
    
    return _agent_instance 
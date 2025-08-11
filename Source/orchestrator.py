from __future__ import annotations

import subprocess
import time
import requests
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama

from protocol_parser import ProtocolParser, ParsedEvent, FailParser, CommandType
from mcp_layer import McpLayer


@dataclass
class LLMToolDescriptor:
    """Minimal descriptor for a tool exposed to the LLM planner."""

    name: str
    description: str


class OrchestratorLLM:
    """Planner that builds prompts and invokes ChatOllama.

    - Owns prompt construction (base template + dynamic tools + examples)
    - Invokes the LLM and returns raw text for the orchestrator to parse
    """

    def __init__(
        self,
        chat: ChatOllama,
        base_template: str,
        examples: Optional[List[str]] = None,
    ) -> None:
        self._chat = chat
        self._examples: List[str] = examples or []
        self._tools: List[LLMToolDescriptor] = []
        self._prompt_template: PromptTemplate = PromptTemplate.from_template(base_template)
        self._lock = RLock()
        self._last_prompt: Optional[str] = None

    @classmethod
    def from_template_file(
        cls,
        chat: ChatOllama,
        template_path: str | Path,
        examples: Optional[List[str]] = None,
    ) -> OrchestratorLLM:
        template_text = Path(template_path).read_text(encoding="utf-8")
        return cls(chat=chat, base_template=template_text, examples=examples)

    def set_tools(self, tools: List[Dict[str, Any]] | List[LLMToolDescriptor]) -> None:
        """Replace registered tools (name, description)."""
        with self._lock:
            normalized: List[LLMToolDescriptor] = []
            for t in tools:
                if isinstance(t, LLMToolDescriptor):
                    normalized.append(t)
                else:
                    normalized.append(
                        LLMToolDescriptor(
                            name=str(t.get("name", "")).strip(),
                            description=str(t.get("description", "")).strip(),
                        )
                    )
            self._tools = normalized

    # ----- Prompt building helpers -----
    def _render_tools_section(self) -> str:
        lines: List[str] = ["Your available tools are:"]
        if not self._tools:
            lines.append("- (no tools registered)")
            return "\n".join(lines)
        for tool in self._tools:
            lines.append(f"- `{tool.name}`: {tool.description}")
        return "\n".join(lines)

    def _render_examples_section(self) -> str:
        if not self._examples:
            return ""
        return "Here are examples of how to translate user requests:\n\n" + "\n\n".join(self._examples)

    def build_prompt(self, user_input: str) -> str:
        """Build the full prompt string."""
        tools_str=self._render_tools_section()
        examples_str=self._render_examples_section()
        prompt = self._prompt_template.format(
            user_input=user_input,
            tools_section=tools_str,
            examples_section=examples_str,
        )
        # cache the last built prompt for inspection
        self._last_prompt = prompt
        return prompt

    # ----- Public API -----
    def plan(self, user_input: str) -> str:
        """Invoke the LLM with the composed prompt and return raw text."""
        prompt = self.build_prompt(user_input=user_input)
        result = self._chat.invoke(prompt)
        return getattr(result, "content", str(result))

    def get_cached_prompt(self) -> Optional[str]:
        """Return the most recently built prompt (if any)."""
        return self._last_prompt
    
    def get_tools(self) -> List[LLMToolDescriptor]:
        """Return the tools registered with the LLM planner."""
        return self._tools


class Orchestrator:
    """Main orchestrator that coordinates LLM planning and tool execution."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._parser = ProtocolParser()
        self.mcp_layer = None
        self.llm_planner = None
        self.ollama_model = None
        
    def initialize(self) -> bool:
        """Initialize the orchestrator."""
        try:
            # Step 1: Start Ollama service if not running
            if not self._ensure_ollama_running():
                return False
                
            # Step 2: Initialize the MCP layer
            self.mcp_layer = McpLayer()
            self.mcp_layer.start(self.config.get("Application", {}).get("mcp_servers_config", ""))
            
            # Step 3: Build the LLM planner
            ollama_model = self.config.get("Application", {}).get("llm_model", "llama3.2:3b")
            ollama_base_url = self.config.get("Application", {}).get("llm_base_url", "http://localhost:11434")
            ollama_temperature = self.config.get("Application", {}).get("llm_temperature", 0.0)
            
            # Pre-load the model to avoid first-request delay
            if not self._preload_model(ollama_model):
                print("⚠️ Warning: Could not pre-load model, first request may be slower")
            
            # Build LLM client
            chat = ChatOllama(model=ollama_model, temperature=ollama_temperature, base_url=ollama_base_url)
            
            # Build planner
            examples_path = self.config.get("Application", {}).get("llm_examples", "")
            # Read examples from file
            examples = Path(examples_path).read_text(encoding="utf-8")
            examples_list = examples.split("\n\n")
            file_template_path = self.config.get("Application", {}).get("llm_template", "")

            self.llm_planner = OrchestratorLLM.from_template_file(chat=chat, template_path=file_template_path, examples=examples_list)

            # Step 4: Inject tools (local ping + any discovered remote tools)
            self.llm_planner.set_tools(self.mcp_layer.list_llm_tools())

            self.ollama_model = ollama_model

            return True
            
        except Exception as e:
            print(f"❌ Error initializing Orchestrator: {e}")
            return False
    
    def _ensure_ollama_running(self) -> bool:
        """Ensure Ollama service is running, start if needed."""
        try:
            # Check if Ollama is already running
            if self._check_ollama_health():
                print("✅ Ollama service already running")
                return True
                
            # Start Ollama service
            print("🚀 Starting Ollama service...")
            ollama_path = self.config.get("Application", {}).get("ollama_path", "ollama")
            
            # Start Ollama in background
            self._ollama_process = subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent process
            )
            
            # Wait for service to be ready
            max_wait = 30  # seconds
            for i in range(max_wait):
                if self._check_ollama_health():
                    print(f"✅ Ollama service started successfully in {i+1}s")
                    return True
                time.sleep(1)
                
            print("❌ Ollama service failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Error starting Ollama: {e}")
            return False
    
    def _check_ollama_health(self) -> bool:
        """Check if Ollama service is responding."""
        try:
            base_url = self.config.get("Application", {}).get("llm_base_url", "http://localhost:11434")
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _preload_model(self, model_name: str) -> bool:
        """Pre-load the model to avoid first-request delay."""
        try:
            print(f"📥 Pre-loading model: {model_name}")
            result = subprocess.run(
                ["ollama", "run", model_name],
                check=True,
                capture_output=True,
                text=True,
                timeout=10  #  timeout for model download
            )
            print(f"✅ Model {model_name} loaded successfully")
            return True
        except subprocess.TimeoutExpired:
            print(f"⚠️ Timeout loading model {model_name}")
            return False
        except Exception as e:
            print(f"⚠️ Warning: Could not pre-load model {model_name}: {e}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup the orchestrator."""
        try:
            # Stop Ollama service if we started it
            if hasattr(self, '_ollama_process') and self._ollama_process:
                print("🛑 Stopping Ollama service...")
                self._ollama_process.terminate()
                self._ollama_process.wait(timeout=10)
                print("✅ Ollama service stopped")
            
            # Stop MCP layer
            if self.mcp_layer:
                self.mcp_layer.stop()
                
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
        
            
    def process_user_request(self, user_input: str) -> List[ParsedEvent]:
        """
        Process a user request through the complete pipeline.
        
        Args:
            user_input: User's natural language request
            
        Returns:
            List of parsed events ready for execution
            
        Raises:
            FailParser: If LLM output cannot be parsed
        """
        try:
            # Step 1: Get LLM plan
            llm_output = self.llm_planner.plan(user_input)
            
            # Step 2: Parse into events
            events = self._parser.parse_llm_output(llm_output)
            
            # Step 3: Return events for processing
            return events
            
        except FailParser as e:
            # TODO: Define appropriate action for parsing failures
            # For now, just re-raise the exception
            raise
    def execute_loop(self,events: List[ParsedEvent]) -> None:
        """Execute the events."""
        for event in events:
            if event.command_type == CommandType.TASK or event.command_type == CommandType.QUERY:
                tool_arg_schema = self.mcp_layer.build_schema(event.tool_name, event.tool_args)
                result = self.mcp_layer.execute(event.tool_name, tool_arg_schema)
                event.result = result                            
            elif event.command_type == CommandType.ERROR:
                print(f"❌ Error: {event.message}")
                break
            else:
                print(f"❌ Unknown event type: {event.type}")
                break

    def get_llm_planner(self) -> OrchestratorLLM:
        """Get access to the LLM planner for tool registration."""
        return self.llm_planner
    
    def get_llm_model(self) -> str:
        """Get the LLM model."""
        return self.ollama_model
    
    def get_mcp_layer_status(self) -> str:
        """Get the status of the MCP layer."""
        return self.mcp_layer.get_status()


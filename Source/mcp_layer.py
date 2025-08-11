from __future__ import annotations

from dataclasses import dataclass
import asyncio
import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    # Optional YAML support (for config). We degrade gracefully if not installed.
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore


HandlerType = Callable[[Dict[str, Any]], Any]


@dataclass(frozen=True, slots=True)
class McpTool:
    """Descriptor for an MCP-executed tool.

    name: Stable identifier used by the LLM and orchestrator
    description: Human-readable usage description inserted into the prompt
    handler: Callable invoked to execute the tool
    """

    name: str
    description: str
    handler: HandlerType


class McpLayer:
    """MCP integration layer with sync facade and async internals.

    Responsibilities:
    - Provide a registry of tools discoverable by the LLM planner
    - Execute a tool by name with JSON-like arguments
    - Optionally manage MCP servers (child processes) per configuration
    - Maintain an internal asyncio loop on a background thread for async I/O

    Notes:
    - The public API is synchronous for easy integration with the orchestrator.
    - Remote MCP tools are discovered from configured servers and merged with
      local tools (e.g., built-in `ping`).
    - For simplicity and robustness, remote calls use short-lived sessions
      (connect → call → close). You can evolve this to persistent sessions later.
    """

    def __init__(self) -> None:
        self._name_to_tool: Dict[str, McpTool] = {}
        self._remote_tool_to_server: Dict[str, str] = {}
        self._remote_tool_descriptions: Dict[str, str] = {}
        self._remote_tool_schemas: Dict[str, Dict[str, Any]] = {}
        self._server_procs: Dict[str, subprocess.Popen] = {}
        self._server_configs: List[Dict[str, Any]] = []
        self._server_persistent: Dict[str, bool] = {}
        self._persistent_sessions: Dict[str, Dict[str, Any]] = {}
        self._server_locks: Dict[str, asyncio.Lock] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._loop_ready: threading.Event = threading.Event()
        self._lock = threading.RLock()
        self._started: bool = False

        # logging
        self._log = logging.getLogger(self.__class__.__name__)

        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        def ping_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
            # Always return a constant pong to keep semantics unambiguous
            return {"ok": True, "reply": "pong"}

        self.register_tool(
            McpTool(
                name="ping",
                description="Health-check; always returns 'pong'.",
                handler=ping_handler,
            )
        )

    # ----- Registration API -----
    def register_tool(self, tool: McpTool) -> None:
        name = tool.name.strip()
        if not name:
            raise ValueError("Tool name must be non-empty")
        if name in self._name_to_tool:
            raise ValueError(f"Tool already registered: {name}")
        self._name_to_tool[name] = tool

    # ----- LLM discovery API -----
    def list_llm_tools(self) -> List[Dict[str, str]]:
        """Return a list of {name, description} records for prompt injection."""
        tools: List[Dict[str, str]] = []
        # local tools
        for tool in self._name_to_tool.values():
            tools.append({"name": tool.name, "description": tool.description})
        # remote tools (discovered)
        with self._lock:
            for name, desc in self._remote_tool_descriptions.items():
                tools.append({"name": name, "description": desc})
        return tools

    # ----- Execution API -----
    def execute(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a registered tool by name.

        args should be JSON-serializable. The handler returns any JSON-serializable
        result which the orchestrator can turn back into a string for the LLM.
        """
        # Prefer local tools first
        tool = self._name_to_tool.get(tool_name)
        if tool is not None:
            return tool.handler(args or {})

        # Route to remote if known
        with self._lock:
            server_name = self._remote_tool_to_server.get(tool_name)
        if server_name is None:
            raise KeyError(f"Unknown tool: {tool_name}")

        if not self._started or self._loop is None:
            raise RuntimeError(
                "McpLayer is not started. Call start(config_path=...) before executing remote tools."
            )

        coro = self._async_call_remote_tool(server_name=server_name, tool_name=tool_name, arguments=args or {})
        return self._run_coro_sync(coro, timeout_seconds=60.0)

    # ----- Lifecycle API -----
    def start(self, config_path: str | os.PathLike[str]) -> None:
        """Start the MCP layer.

        - Loads server configuration from JSON or YAML file
        - Optionally launches MCP servers as child processes if 'command' specified
        - Spawns a dedicated asyncio loop on a background thread
        - Discovers remote tools and exposes them to the planner
        """
        if self._started:
            return

        cfg_path = Path(config_path)
        if not cfg_path.exists():
            raise FileNotFoundError(f"Config not found: {cfg_path}")

        self._server_configs = self._load_config(cfg_path)
        self._validate_server_configs(self._server_configs)
        self._log.debug("Loaded MCP config: %s", self._server_configs)

        # Launch child processes (optional per server)
        for server in self._server_configs:
            name = str(server.get("name"))
            cmd = server.get("command")
            if cmd:                
                proc = self._launch_process(name=name, cmd=cmd, cwd=server.get("cwd"), env=server.get("env"))
                self._server_procs[name] = proc
            # Persistency flag
            persistent_flag = bool(server.get("use_persistent_session") or server.get("persistent_session") or server.get("persistent_sessions"))
            self._server_persistent[name] = persistent_flag
            self._server_locks[name] = asyncio.Lock()

        # Start background loop thread
        self._start_loop_thread()
        # Ensure loop is actually running; otherwise clean up and fail fast
        if not self._is_loop_running():
            self._cleanup_processes()
            raise RuntimeError("Async loop failed to start")

        # Discover remote tools (sync; block briefly for initial snapshot)
        try:
            time.sleep(5)
            self._discover_all_tools()
        except Exception as e:
            # Log and continue; local tools still function
            self._log.warning("Tool discovery encountered an issue: %s", e)

        self._started = True

    def stop(self, terminate_processes: bool = True, kill_after_seconds: float = 3.0) -> None:
        """Stop the MCP layer and clean up resources."""
        # Stop loop thread
        if self._loop is not None:
            loop = self._loop
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=kill_after_seconds)
        self._loop = None
        self._loop_thread = None
        self._loop_ready.clear()

        # Terminate child processes
        # Close persistent sessions first (async)
        try:
            if self._is_loop_running():
                self._run_coro_sync(self._async_close_persistent_sessions(), timeout_seconds=kill_after_seconds)
        except Exception as e:
            self._log.warning("Error closing persistent sessions: %s", e)

        if terminate_processes and self._server_procs:
            for name, proc in list(self._server_procs.items()):
                try:
                    if proc.poll() is None:
                        proc.terminate()
                        t0 = time.time()
                        while proc.poll() is None and (time.time() - t0) < kill_after_seconds:
                            time.sleep(0.1)
                        if proc.poll() is None:
                            proc.kill()
                except Exception as e:
                    self._log.warning("Error stopping server '%s': %s", name, e)
                finally:
                    self._server_procs.pop(name, None)

        with self._lock:
            self._remote_tool_to_server.clear()
            self._remote_tool_descriptions.clear()
            self._server_configs.clear()
            self._server_persistent.clear()
            self._persistent_sessions.clear()
            self._server_locks.clear()
        self._started = False

    # ----- Internal: Config, Processes, Loop -----
    def _load_config(self, cfg_path: Path) -> List[Dict[str, Any]]:
        text = cfg_path.read_text(encoding="utf-8")
        # Try JSON first
        try:
            cfg = json.loads(text)
            servers = cfg.get("servers") if isinstance(cfg, dict) else None
            if isinstance(servers, list):
                return servers  # type: ignore[return-value]
        except Exception:
            pass

        # Try YAML (if available)
        if yaml is not None:
            try:
                cfg_yaml = yaml.safe_load(text)  # type: ignore[attr-defined]
                servers = cfg_yaml.get("servers") if isinstance(cfg_yaml, dict) else None
                if isinstance(servers, list):
                    return servers  # type: ignore[return-value]
            except Exception:
                pass

        raise ValueError("Config must be a JSON or YAML object with a top-level 'servers' list")

    def _launch_process(
        self,
        name: str,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        full_env = os.environ.copy()
        if env:
            full_env.update({str(k): str(v) for k, v in env.items()})
        self._log.info("Starting MCP server '%s': %s", name, " ".join(cmd))
        # Start in a new process group so we can terminate the subtree on stop()
        return subprocess.Popen(
            cmd,
            cwd=cwd or None,
            env=full_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def _start_loop_thread(self) -> None:
        if self._loop_thread is not None:
            return

        def _runner(evt: threading.Event) -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            evt.set()
            try:
                loop.run_forever()
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception as e:
                    self._log.debug("Error while draining loop tasks on shutdown: %s", e)
                loop.close()

        self._loop_thread = threading.Thread(target=_runner, args=(self._loop_ready,), name="McpLayerLoop", daemon=True)
        self._loop_thread.start()
        # Wait for loop to be created
        self._loop_ready.wait(timeout=5.0)
        # Additionally wait until loop is running
        t0 = time.time()
        while not self._is_loop_running() and (time.time() - t0) < 5.0:
            time.sleep(0.01)

    def _is_loop_running(self) -> bool:
        return self._loop is not None and self._loop.is_running()

    def _cleanup_processes(self) -> None:
        for name, proc in list(self._server_procs.items()):
            try:
                if proc.poll() is None:
                    proc.terminate()
                    time.sleep(0.2)
                    if proc.poll() is None:
                        proc.kill()
            except Exception as e:
                self._log.warning("Error cleaning up server '%s' after failure: %s", name, e)
            finally:
                self._server_procs.pop(name, None)

    def _run_coro_sync(self, coro: "asyncio.Future[Any] | asyncio.coroutines.Coroutine[Any, Any, Any]", timeout_seconds: float) -> Any:
        if self._loop is None:
            raise RuntimeError("Async loop is not running")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout_seconds)

    # ----- Internal: Remote calls & discovery (ephemeral sessions) -----
    async def _async_call_remote_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        server = self._find_server_config(server_name)
        if server is None:
            raise RuntimeError(f"Server config not found: {server_name}")
        sse_url = str(server.get("sse_url"))
        if not sse_url:
            raise RuntimeError(f"Missing sse_url for server: {server_name}")

        try:
            from mcp import ClientSession  # type: ignore
            from mcp.client.sse import sse_client  # type: ignore
        except Exception as e:  # pragma: no cover - optional dependency
            raise RuntimeError("mcp SDK is required for remote calls. Install 'mcp' package.") from e

        async with sse_client(url=sse_url) as (in_stream, out_stream):
            async with ClientSession(in_stream, out_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                # SDK returns structured content; try to coerce to simple JSON-serializable
                try:
                    # Common pattern: result.content is a list of TextContent
                    content = result.content[0].text if getattr(result, "content", None) else None
                    return content if content is not None else str(result)
                except Exception:
                    return str(result)

    def _discover_all_tools(self) -> None:
        """Synchronous tool discovery that updates the data structures directly."""
        for server in self._server_configs:
            name = str(server.get("name"))
            if not name:
                continue
            
            try:
                pairs = self._list_tools_for_server_sync(server)
            except Exception as e:
                self._log.warning("Tool discovery failed for server '%s': %s", name, e)
                continue
            
            with self._lock:
                for tool_info in pairs:
                    tool_name = tool_info.get("name")
                    tool_desc = tool_info.get("description", "")
                    tool_schema = tool_info.get("inputSchema", {})

                    if not tool_name or tool_name in self._name_to_tool:
                        # Local override wins; skip remote duplicate
                        continue
                    
                    # If duplicate across servers, warn and last one wins
                    prev = self._remote_tool_to_server.get(tool_name)
                    if prev and prev != name:
                        self._log.warning(
                            "Tool '%s' discovered on multiple servers: '%s' and '%s'. Using '%s'.",
                            tool_name,
                            prev,
                            name,
                            name,
                        )
                    
                    self._remote_tool_to_server[tool_name] = name
                    self._remote_tool_descriptions[tool_name] = tool_desc
                    self._remote_tool_schemas[tool_name] = tool_schema

    async def _async_discover_all_tools(self) -> None:
        """Async wrapper for backward compatibility - delegates to sync version."""
        # Run the sync version in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._discover_all_tools)

    def _list_tools_for_server_sync(self, server: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Synchronous tool listing with full schema information."""
        name = str(server.get("name"))
        sse_url = str(server.get("sse_url"))
        if not sse_url:
            return []

        try:
            from mcp import ClientSession  # type: ignore
            from mcp.client.sse import sse_client  # type: ignore
        except Exception as e:  # pragma: no cover - optional dependency
            raise RuntimeError("mcp SDK is required for remote discovery. Install 'mcp' package.") from e

        results: List[Dict[str, Any]] = []
        
        try:
            # Use the existing async method but run it synchronously
            async def _discover_tools():
                async with sse_client(url=sse_url) as (in_stream, out_stream):
                    async with ClientSession(in_stream, out_stream) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        return tools
            
            # Run the async function synchronously
            tools = self._run_coro_sync(_discover_tools(), timeout_seconds=30.0)
            
            if tools and hasattr(tools, 'tools'):
                for t in tools.tools:
                    t_name = getattr(t, "name", None) or ""
                    t_desc = getattr(t, "description", None) or ""
                    t_schema = getattr(t, "inputSchema", {}) or {}
                    
                    if t_name:
                        results.append({
                            "name": str(t_name),
                            "description": str(t_desc),
                            "inputSchema": t_schema,
                            "server": name
                        })
            
        except Exception as e:
            self._log.warning("Tool discovery failed for '%s': %s", name, e)
            
        return results

    async def _ensure_persistent_session(self, server_name: str, sse_url: str):  # type: ignore[no-untyped-def]
        try:
            from mcp import ClientSession  # type: ignore
            from mcp.client.sse import sse_client  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("mcp SDK is required for persistent sessions. Install 'mcp' package.") from e

        lock = self._server_locks[server_name]
        async with lock:
            existing = self._persistent_sessions.get(server_name)
            if existing and existing.get("session") and not existing.get("closed"):
                return existing["session"]

            # Manually enter async context managers to keep them open
            sse_cm = sse_client(url=sse_url)
            in_stream, out_stream = await sse_cm.__aenter__()
            session_cm = ClientSession(in_stream, out_stream)
            session = await session_cm.__aenter__()
            await session.initialize()
            self._persistent_sessions[server_name] = {
                "sse_cm": sse_cm,
                "session_cm": session_cm,
                "session": session,
                "closed": False,
            }
            return session

    async def _async_close_persistent_sessions(self) -> None:
        for name, bundle in list(self._persistent_sessions.items()):
            if not bundle or bundle.get("closed"):
                continue
            sse_cm = bundle.get("sse_cm")
            session_cm = bundle.get("session_cm")
            try:
                if session_cm:
                    await session_cm.__aexit__(None, None, None)
                if sse_cm:
                    await sse_cm.__aexit__(None, None, None)
            except Exception as e:
                self._log.warning("Error closing persistent session for '%s': %s", name, e)
            finally:
                bundle["closed"] = True
                self._persistent_sessions.pop(name, None)

    def _validate_server_configs(self, servers: List[Dict[str, Any]]) -> None:
        seen_names: set[str] = set()
        for idx, server in enumerate(servers):
            name = str(server.get("name", "")).strip()
            sse_url = str(server.get("sse_url", "")).strip()
            if not name:
                raise ValueError(f"Server at index {idx} missing required field 'name'")
            if not sse_url:
                raise ValueError(f"Server '{name}' missing required field 'sse_url'")
            if name in seen_names:
                raise ValueError(f"Duplicate server name '{name}' in config")
            seen_names.add(name)

    def _find_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        for s in self._server_configs:
            if str(s.get("name")) == server_name:
                return s
        return None
    
    def get_status(self) -> str:
        """Get the status of the MCP layer."""
        return "Active" if self._started else "Inactive"
    
    def build_schema(self, tool_name: str,list_of_args: List[str]) -> Dict[str, Any]:
        """Build the schema for a tool."""
        tool_schema = self._remote_tool_schemas[tool_name] 
        mcp_schema = {}
        #extract the inputSchema property of the tool
        #'inputSchema': {'properties': {'issue_key': {'title': 'Issue Key', 'type': 'string'}}, 'required': ['issue_key'], 'type': 'object'}
        schema_properties = tool_schema.get("properties")
        if schema_properties:
            #iterate over the properties
            list_of_args_schema = []
            for key, value in schema_properties.items():                
                list_of_args_schema.append(key)
            
            if len(list_of_args) <= len(list_of_args_schema):
                for index, value in enumerate(list_of_args):
                   mcp_schema[list_of_args_schema[index]] = value   
                
            #make sure that the required arguments are present in the schema
            required_args = tool_schema.get("required")
            if required_args:
                for arg in required_args:
                    if arg not in mcp_schema:
                        raise ValueError(f"Required argument '{arg}' not found in the schema")
                        
                        
        #default if no arguments are provided, return an empty dictionary
        return mcp_schema


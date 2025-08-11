from langchain_ollama import ChatOllama
import argparse
import os
import re
import sys
import time


# Ensure project root on path to import `Source` package
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Source.orchestrator import OrchestratorLLM
from Source.mcp_layer import McpLayer


def parse_plan(text: str):
    """Very small parser for BEGIN/{COMMAND}(tool(args))/END.
    Returns (command, tool_name, args_text) or raises ValueError.
    """
    m = re.search(r"BEGIN\s*(.*?)\s*END\s*\Z", text, re.DOTALL | re.IGNORECASE)
    if not m:
        raise ValueError("Plan output missing BEGIN/END block")
    body = m.group(1).strip()
    m2 = re.match(r"(QUERY|TASK|ERROR)\s*\((.*)\)\s*\Z", body, re.DOTALL | re.IGNORECASE)
    if not m2:
        raise ValueError("Plan body must be COMMAND(...) with QUERY/TASK/ERROR")
    command = m2.group(1).upper()
    call = m2.group(2).strip()
    m3 = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*\Z", call, re.DOTALL)
    if not m3:
        raise ValueError("Inner call must be toolName(...)")
    tool = m3.group(1)
    args_text = m3.group(2).strip()
    return command, tool, args_text


def args_text_to_dict(tool: str, args_text: str):
    """Translate a minimal args string to a dict. Supports ping("msg") or ping()."""
    if not args_text:
        return {}
    # Match a single quoted string argument
    m = re.match(r"^\s*\"(.*)\"\s*$", args_text)
    if m and tool == "ping":
        return {"message": m.group(1)}
    # Fallback: no-args dict
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="ChatOllama + OrchestratorLLM + MCP smoke test (with optional MCP lifecycle)")
    parser.add_argument("message", nargs="?", default="Please run a ping health check.", help="User request to send to the planner")
    parser.add_argument("--model", default="llama3.2:3b", help="Ollama model tag")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama server base URL")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--show-prompt", action="store_true", help="Print the composed planner prompt")
    parser.add_argument("--mcp-config", default=os.environ.get("MCP_CONFIG"), help="Path to MCP config (YAML/JSON). If provided, start/stop MCP layer and discover remote tools.")
    parser.add_argument("--print-tools", action="store_true", help="Print discovered tools from MCP layer")
    args = parser.parse_args()

    # Build LLM client
    chat = ChatOllama(model=args.model, temperature=args.temperature, base_url=args.base_url)

    # Build planner and MCP layer
    template_path = os.path.join(PROJECT_ROOT, "Source", "Prompts", "planner_prompt_template.txt")
    examples = [
        "1. **User Request:** \"Health check.\"\n   **Your Output:**\n   BEGIN\n   QUERY(ping())\n   END",
        "2. **User Request:** \"Ping hello.\"\n   **Your Output:**\n   BEGIN\n   QUERY(ping(\"hello\"))\n   END",
    ]
    planner = OrchestratorLLM.from_template_file(chat=chat, template_path=template_path, examples=examples)

    mcp = McpLayer()
    started = False
    try:
        # Optionally start MCP layer with config to test lifecycle and discovery
        if args.mcp_config:
            mcp.start(args.mcp_config)
            started = True
        else:
            mcp.start("/home/stanny/projects/mcp_jira/Source/mcp_servers.example.yaml")
            started = True
        # Inject tools (local ping + any discovered remote tools)
        planner.set_tools(mcp.list_llm_tools())
        if args.print_tools:
            tool_names = [t.get("name") for t in mcp.list_llm_tools()]
            print("Tools:", ", ".join(tool_names))

        # Plan using the LLM (measure time)
        t0 = time.perf_counter()
        raw = planner.plan(args.message)
        t1 = time.perf_counter()
        if args.show_prompt:
            print("\n--- Prompt ---\n" + (planner.get_cached_prompt() or "<none>") + "\n--- End Prompt ---\n")
        print(f"Plan time: {(t1 - t0)*1000:.1f} ms")
        print("\n--- LLM Output ---\n" + raw + "\n--- End LLM Output ---\n")

        # Try to parse and execute if it's a QUERY/TASK ping(...)
        try:
            command, tool, args_text = parse_plan(raw)
            if tool == "ping" and command in {"QUERY", "TASK"}:
                payload = args_text_to_dict(tool, args_text)
                result = mcp.execute(tool, payload)
                print("Execution Result:", result)
            else:
                print(f"Parsed command={command}, tool={tool}; skipping execution (only 'ping' supported)")
        except Exception as e:
            print("Could not parse/execute plan:", e)
    finally:
        if started:
            mcp.stop()


if __name__ == "__main__":
    main()
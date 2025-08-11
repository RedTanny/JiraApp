from __future__ import annotations

import argparse
import os
import statistics as stats
import sys
import time
import re
from typing import List, Tuple


# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from Source.orchestrator import OrchestratorLLM
from Source.mcp_layer import McpLayer


def parse_plan_minimal(text: str) -> Tuple[str, str, str]:
    """Parse BEGIN/COMMAND(tool(args))/END. Returns (command, tool, args_text).
    Raises ValueError if the structure is not as expected.
    """
    m = re.search(r"BEGIN\s*(.*?)\s*END\s*\Z", text, re.DOTALL | re.IGNORECASE)
    if not m:
        raise ValueError("Missing BEGIN/END block")
    body = m.group(1).strip()
    m2 = re.match(r"(QUERY|TASK|ERROR)\s*\((.*)\)\s*\Z", body, re.DOTALL | re.IGNORECASE)
    if not m2:
        raise ValueError("Body must be COMMAND(...)")
    command = m2.group(1).upper()
    call = m2.group(2).strip()
    m3 = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*\Z", call, re.DOTALL)
    if not m3:
        raise ValueError("Bad inner call: toolName(...)")
    tool = m3.group(1)
    args_text = m3.group(2).strip()
    return command, tool, args_text


def _summary(xs: List[float]) -> str:
    xs_sorted = sorted(xs)
    return (
        f"count={len(xs)} avg={sum(xs)/len(xs):.1f} ms "
        f"p50={stats.median(xs):.1f} ms p95={xs_sorted[int(0.95*len(xs_sorted))-1]:.1f} ms "
        f"min={xs_sorted[0]:.1f} ms max={xs_sorted[-1]:.1f} ms"
    )


def run_benchmark(
    model: str,
    iterations: int,
    warmup: int,
    base_url: str,
    temperature: float,
    scenario: str = "ping",
) -> None:
    chat = ChatOllama(model=model, base_url=base_url, temperature=temperature)

    template_path = os.path.join(PROJECT_ROOT, "Source", "Prompts", "planner_prompt_template.txt")

    # Define scenarios
    if scenario == "ping":
        examples = [
            "1. **User Request:** \"Health check.\"\n   **Your Output:**\n   BEGIN\n   QUERY(ping())\n   END",
        ]
        user_message = "Health check."
        # Tools from MCP (ping)
        mcp = McpLayer()
        tools_for_planner = mcp.list_llm_tools()
        def execute_local(tool_name: str, args_text: str) -> None:
            if tool_name == "ping":
                _ = mcp.execute("ping", {})
        parse_expected_tool = "ping"
    elif scenario == "multiply":
        # Standard LangChain tool
        @tool
        def multiply(a: int, b: int) -> int:
            """Multiply a and b."""
            return a * b

        examples = [
            "1. **User Request:** \"Multiply 3 and 4.\"\n   **Your Output:**\n   BEGIN\n   QUERY(multiply(3, 4))\n   END",
        ]
        user_message = "Multiply 3 and 4."
        # Use tool's own metadata for planner prompt
        tools_for_planner = [{"name": multiply.name, "description": multiply.description or "Multiply a and b."}]
        def execute_local(tool_name: str, args_text: str) -> None:
            pass  # no-op; we measure planning only
        parse_expected_tool = "multiply"
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    planner = OrchestratorLLM.from_template_file(chat=chat, template_path=template_path, examples=examples)
    planner.set_tools(tools_for_planner)

    # Warmup
    for _ in range(max(0, warmup)):
        _ = planner.plan(user_message)

    plan_times_ms: List[float] = []
    total_times_ms: List[float] = []
    parse_failures = 0

    for _ in range(iterations):
        t0 = time.perf_counter()
        raw = planner.plan(user_message)
        t1 = time.perf_counter()
        plan_ms = (t1 - t0) * 1000.0

        # Minimal validation and optional local execute
        try:
            command, tool_name, args_text = parse_plan_minimal(raw)
            if tool_name == parse_expected_tool and command in {"QUERY", "TASK"}:
                t2 = time.perf_counter()
                execute_local(tool_name, args_text)
                t3 = time.perf_counter()
                total_ms = (t3 - t0) * 1000.0
            else:
                total_ms = plan_ms
        except Exception:
            parse_failures += 1
            total_ms = plan_ms

        plan_times_ms.append(plan_ms)
        total_times_ms.append(total_ms)

    print(f"\n== Benchmark results [{scenario}] ==")
    print(f"model={model} base_url={base_url} temp={temperature}")
    print(f"plan:  {_summary(plan_times_ms)}")
    print(f"total: {_summary(total_times_ms)}")
    if parse_failures:
        print(f"parse failures: {parse_failures}/{iterations}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark OrchestratorLLM planning latency across models and scenarios")
    parser.add_argument("--models", default="phi3.5:3.8b,qwen3:4b,gemma3n:latest,llama3.2:3b", help="Comma-separated Ollama model tags")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--iterations", type=int, default=10, help="Number of measured iterations")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup iterations")
    parser.add_argument("--scenarios", default="ping,multiply", help="Comma-separated scenarios to run (ping,multiply)")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]

    for model in models:
        for scenario in scenarios:
            run_benchmark(
                model=model,
                iterations=args.iterations,
                warmup=args.warmup,
                base_url=args.base_url,
                temperature=args.temperature,
                scenario=scenario,
            )


if __name__ == "__main__":
    main()


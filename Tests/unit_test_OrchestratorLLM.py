from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os
import sys

# Ensure project root is on sys.path so `Source` package can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Source.orchestrator import OrchestratorLLM
from Source.mcp_layer import McpLayer


@dataclass
class _DummyResult:
    content: str


class _DummyChat:
    def __init__(self) -> None:
        self.last_prompt: str | None = None

    def invoke(self, prompt: str) -> _DummyResult:  # type: ignore[override]
        self.last_prompt = prompt
        # Return a deterministic stub response matching the expected CALL structure
        return _DummyResult("BEGIN\nCALL(get_jira_issue(\"ABC-123\"))\nEND")


def test_orchestrator_llm_prompt_building_and_invoke() -> None:
    # Arrange: load the shared planner template and register tools
    template_path = "/home/stanny/projects/mcp_jira/Source/Prompts/planner_prompt_template.txt"
    dummy_chat = _DummyChat()
    planner = OrchestratorLLM.from_template_file(chat=dummy_chat, template_path=template_path, examples=[
        "1. **User Request:** \"Get details for JIRA issue NCS-8540.\"\n   **Your Output:**\n   BEGIN\n   QUERY(get_jira_issue(\"NCS-8540\"))\n   END",
    ])
    planner.set_tools([
        {"name": "get_jira_issue", "description": "Retrieves details for a specific JIRA issue by key."},
        {"name": "search_jira_issues", "description": "Searches JIRA using a JQL string."},
    ])

    # Act: plan with a user request
    output = planner.plan("Get details for JIRA issue ABC-123.")

    # Assert: dummy response is returned and prompt contains the tool list and user request
    assert output.strip().startswith("BEGIN")
    assert dummy_chat.last_prompt is not None
    assert "get_jira_issue" in dummy_chat.last_prompt
    assert "search_jira_issues" in dummy_chat.last_prompt
    assert "User Request:" in dummy_chat.last_prompt
    print(dummy_chat.last_prompt)
    print("test_orchestrator_llm_prompt_building_and_invoke --> PASS")


def test_orchestrator_llm_wired_with_mcp_tools() -> None:
    # Use MCP layer to provide tools to the planner
    template_path = "/home/stanny/projects/mcp_jira/Source/Prompts/planner_prompt_template.txt"
    dummy_chat = _DummyChat()
    planner = OrchestratorLLM.from_template_file(chat=dummy_chat, template_path=template_path, examples=[])

    mcp = McpLayer()
    planner.set_tools(mcp.list_llm_tools())

    # Plan a trivial health-check request; we only verify prompt content and invocation path
    output = planner.plan("Please run a ping health check.")

    assert output.strip().startswith("BEGIN")
    cached = planner.get_cached_prompt()
    assert cached is not None and "ping" in cached
    assert "Your available tools are:" in cached
    print(cached)
    print("test_orchestrator_llm_wired_with_mcp_tools --> PASS")


if __name__ == "__main__":
    test_orchestrator_llm_prompt_building_and_invoke()
    test_orchestrator_llm_wired_with_mcp_tools()
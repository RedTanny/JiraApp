from __future__ import annotations

import os
import sys

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Source.mcp_layer import McpLayer
import tempfile
import json


def test_builtin_ping() -> None:
    mcp = McpLayer()
    result = mcp.execute("ping", {"message": "hello"})
    assert result["ok"] is True
    assert result["reply"] == "pong"


def test_list_llm_tools_contains_ping() -> None:
    mcp = McpLayer()
    tools = mcp.list_llm_tools()
    names = {t["name"] for t in tools}
    assert "ping" in names


def test_start_stop_with_minimal_config() -> None:
    # Minimal JSON config with no servers
    cfg = {"servers": []}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cfg, f)
        cfg_path = f.name

    mcp = McpLayer()
    try:
        mcp.start(cfg_path)
        # ping must still be present
        names = {t["name"] for t in mcp.list_llm_tools()}
        assert "ping" in names
    finally:
        mcp.stop()


def test_start_with_dummy_server_does_not_raise() -> None:
    # Dummy server entry; discovery may fail but start should not raise
    cfg = {
        "servers": [
            {
                "name": "dummy",
                "sse_url": "http://127.0.0.1:9/sse/",  # unlikely to be open
            }
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cfg, f)
        cfg_path = f.name

    mcp = McpLayer()
    try:
        mcp.start(cfg_path)
        # Still have local ping
        names = {t["name"] for t in mcp.list_llm_tools()}
        assert "ping" in names
    finally:
        mcp.stop()


def test_execute_unknown_tool_raises_keyerror() -> None:
    mcp = McpLayer()
    try:
        mcp.execute("nonexistent_tool", {})
        assert False, "Expected KeyError"
    except KeyError:
        pass

if __name__ == "__main__":
    test_builtin_ping()
    test_list_llm_tools_contains_ping()
    print("unit_test_McpLayer --> PASS")


#!/usr/bin/env python3
"""
MCP Client Test (official SDK) - uses ClientSession and sse_client
"""

import asyncio
import logging
import time

from mcp import ClientSession
from mcp.client.sse import sse_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SSE_URL = "http://localhost:8003/sse/"  # note trailing slash to avoid 307


async def run_client_test() -> None:
    print("🚀 MCP Client (SDK) Testing")
    print("=" * 48)

    # 1) Connect over SSE and create a ClientSession
    async with sse_client(url=SSE_URL) as (in_stream, out_stream):
        async with ClientSession(in_stream, out_stream) as session:
            # 2) Initialize handshake
            info = await session.initialize()
            logger.info(f"Connected to {info.serverInfo.name} v{info.serverInfo.version}")

            # 3) Optional: list tools
            tools = await session.list_tools()
            logger.info(f"Available tools: {[t.name for t in tools.tools]}")

            # 4) Call get_jira_issue
            print("\n🔧 Call: get_jira_issue")
            t0 = time.time()
            res_issue = await session.call_tool("get_jira_issue", arguments={"issue_key": "NCS-8540"})
            dt = time.time() - t0
            print(f"⏱️  {dt:.2f}s")
            # The SDK returns structured content; print a concise view
            try:
                content = res_issue.content[0].text if res_issue.content else str(res_issue)
            except Exception:
                content = str(res_issue)
            print(content)

            # 5) Call search_jira_issues
            print("\n🔧 Call: search_jira_issues")
            t0 = time.time()
            res_search = await session.call_tool(
                "search_jira_issues",
                arguments={"jql": "project='NCS' AND status!='Done'", "max_results": 5},
            )
            dt = time.time() - t0
            print(f"⏱️  {dt:.2f}s")
            try:
                content = res_search.content[0].text if res_search.content else str(res_search)
            except Exception:
                content = str(res_search)
            print(content)


if __name__ == "__main__":
    asyncio.run(run_client_test())
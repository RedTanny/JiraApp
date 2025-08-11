#!/usr/bin/env python3
"""
Simple JIRA MCP Performance Testing
Uses the existing GenericAgent to test JIRA MCP tools
"""

import sys
import os
import time
from pathlib import Path

# Add the Client directory to the path
sys.path.append(str(Path(__file__).parent.parent / "Client" / "data_access"))

from generic_agent import get_agent_singleton

def test_jira_tools_performance():
    """Test JIRA MCP tools performance using GenericAgent"""
    print("🚀 JIRA MCP Tools Performance Testing")
    print("=" * 60)
    
    # Get the singleton agent
    agent = get_agent_singleton()
    
    # Start the agent
    if not agent.start():
        print("❌ Failed to start agent")
        return
    
    # Register JIRA MCP
    print("\n🔧 Registering JIRA MCP...")
    if agent.register_mcp('jira_mcp_group', 'http://localhost:8003/sse'):
        print("✅ JIRA MCP registered successfully")
    else:
        print("❌ Failed to register JIRA MCP")
        agent.stop()
        return
    
    # Test cases
    test_cases = [
        {
            "name": "Get JIRA Issue",
            "query": f"Get details for JIRA issue NCS-8540",
            "description": "Single issue lookup"
        },
        {
            "name": "Search JIRA Issues", 
            "query": "Search for JIRA issues in project NCS with status not Closed, limit to 5 results",
            "description": "JQL search with results"
        },
        {
            "name": "Get JIRA Projects",
            "query": "List all available JIRA projects",
            "description": "Project metadata retrieval"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔧 Test {i}: {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        print(f"   Query: {test_case['query']}")
        
        # Submit request and measure time
        start_time = time.time()
        request_id = agent.submit_input(test_case['query'])
        print(f"   Request ID: {request_id}")
        
        # Wait for response
        print(f"   Waiting for response...")
        response = agent.wait_for_output(request_id, timeout=60.0)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        if response:
            print(f"   ✅ Success")
            print(f"   ⏱️  Response Time: {response_time:.3f}s")
            print(f"   📊 Response Size: {len(response)} bytes")
            print(f"   📄 Response Preview: {response[:200]}...")
            results.append((test_case['name'], response_time, len(response)))
        else:
            print(f"   ❌ No response received (timeout)")
            results.append((test_case['name'], None, 0))
    
    # Print summary
    print("\n📊 Performance Summary")
    print("=" * 60)
    print(f"{'Tool':<20} {'Time (s)':<10} {'Size (bytes)':<15} {'Status':<10}")
    print("-" * 60)
    
    for tool_name, response_time, response_size in results:
        status = "✅" if response_time and response_time < 60 else "❌"
        time_str = f"{response_time:.3f}" if response_time else "N/A"
        size_str = f"{response_size}" if response_size else "N/A"
        print(f"{tool_name:<20} {time_str:<10} {size_str:<15} {status:<10}")
    
    # Calculate averages
    valid_times = [t for t in [r[1] for r in results] if t and t < 60]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        print(f"\n📈 Average Response Time: {avg_time:.3f}s")
        print(f"📈 Fastest Tool: {min(valid_times):.3f}s")
        print(f"📈 Slowest Tool: {max(valid_times):.3f}s")
    
    # Stop agent
    agent.stop()
    print(f"\n🎉 Testing completed!")

def main():
    """Main function"""
    test_jira_tools_performance()

if __name__ == "__main__":
    main() 
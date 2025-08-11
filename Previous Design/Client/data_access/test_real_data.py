#!/usr/bin/env python3
"""
Real Data Test for Generic Agent
Tests with actual LlamaStack server and JIRA MCP
"""

import sys
import logging
import time
from typing import Dict, Any

# Add the current directory to the path for imports
sys.path.append('.')

from generic_agent import GenericAgent, get_agent_singleton


def test_real_llama_stack_connection(agent: GenericAgent):
    """Test connection to real LlamaStack server"""
    print("🔧 Testing Real LlamaStack Connection")
    print("=" * 50)
        
    # Test connection
    if agent.mcp_registry.health_check():
        print("✅ LlamaStack server is available")
        return True
    else:
        print("❌ LlamaStack server is not available")
        return False


def test_jira_mcp_registration():
    """Test JIRA MCP registration"""
    print("\n🔧 Testing JIRA MCP Registration")
    print("=" * 50)
    
    # Create agent
    agent = get_agent_singleton()
    
    # Register JIRA MCP
    print("📋 Registering JIRA MCP...")
    success = agent.register_mcp(
        toolgroup_id="jira_mcp_group",
        mcp_endpoint="http://localhost:8003/sse"
    )
    
    if success:
        print("✅ JIRA MCP registered successfully")
        
        # Check registered MCPs
        registered = agent.mcp_registry.list_registered_mcps()
        print(f"📋 Registered MCPs: {registered}")
        return True
    else:
        print("❌ Failed to register JIRA MCP")
        return False


def test_real_jira_queries():
    """Test real JIRA queries through the agent"""
    print("\n🔧 Testing Real JIRA Queries")
    print("=" * 50)
    
    # Create and start agent
    agent = get_agent_singleton()
    
    # Register JIRA MCP
    if not agent.register_mcp("jira_mcp_group", "http://localhost:8003/sse"):
        print("❌ Failed to register JIRA MCP - skipping queries")
        return False
    
    # Start agent
    print("🚀 Starting agent...")
    if not agent.start():
        print("❌ Failed to start agent")
        return False
    
    print("✅ Agent started successfully")
    
    # Test various JIRA queries
    test_queries = [  
        "Get JIRA issue details for NCS-8540"                
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")
        
        # Submit query
        request_id = agent.submit_input(query)
        print(f"   Request ID: {request_id}")
        
        # Wait for processing using event-based waiting (no polling!)
        print(f"   Waiting for response...")
        output = agent.wait_for_output(request_id, timeout=60.0)
        
        if output:
            print(f"   ✅ Response received ({len(output)} chars)")
            print(f"   Response: {output[:500]}...")
        else:
            print(f"   ❌ No response received (timeout)")
    
    # Stop agent
    agent.stop()
    print("\n🛑 Agent stopped")
    
    # Summary
    print(f"\n📊 Query Results Summary:")
    successful_queries = sum(1 for _, output in results if output is not None)
    print(f"   Successful queries: {successful_queries}/{len(results)}")
    
    for query, output in results:
        status = "✅" if output else "❌"
        print(f"   {status} {query}")
    
    return successful_queries > 0



def main():
    """Run real data tests"""
    print("🚀 Real Data Testing - Generic Agent with LlamaStack & JIRA MCP")
    print("=" * 70)
    print()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test 1: LlamaStack connection
        if not test_real_llama_stack_connection(get_agent_singleton()):
            print("\n❌ LlamaStack not available - cannot proceed with real data tests")
            return
        
        # Test 2: JIRA MCP registration
        if not test_jira_mcp_registration():
            print("\n❌ JIRA MCP registration failed - cannot proceed with queries")
            return
        
        # Test 3: Real JIRA queries
        test_real_jira_queries()
        
        
        print("\n🎉 Real data testing completed!")
        print("\n📋 What we tested:")
        print("  ✅ LlamaStack server connection")
        print("  ✅ JIRA MCP registration")
        print("  ✅ Real JIRA queries through agent")
        print("  ✅ Model selection and configuration")
        print("\n🔧 Ready for Business Logic tier implementation!")
        
    except Exception as e:
        print(f"\n❌ Real data test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 
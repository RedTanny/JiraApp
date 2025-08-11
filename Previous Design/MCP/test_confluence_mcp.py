#!/usr/bin/env python3
"""
Test script for Confluence MCP Server
Tests the MCP server functionality directly
"""

import os
import sys
import requests
import json
from typing import Dict, Any
from atlassian import Confluence

# Add the current directory to the path for imports
sys.path.append('.')

# Test configuration
MCP_ENDPOINT = "http://localhost:8004/sse"
TEST_QUERY = "documentation"


def test_mcp_connection():
    """Test connection to Confluence MCP server"""
    print("🔧 Testing Confluence MCP Connection")
    print("=" * 50)
    
    try:
        # Test SSE endpoint
        response = requests.get(MCP_ENDPOINT, timeout=5)
        if response.status_code == 200:
            print("✅ Confluence MCP server is running")
            return True
        else:
            print(f"❌ Confluence MCP server returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Confluence MCP server")
        print("   Make sure the server is running on port 8004")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def test_confluence_environment():
    """Test Confluence environment variables"""
    print("\n🔧 Testing Confluence Environment")
    print("=" * 50)
    
    required_vars = [
        "CONFLUENCE_URL",
        "CONFLUENCE_USERNAME", 
        "CONFLUENCE_API_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value and value not in ["your-domain.atlassian.net", "your-email@domain.com", "your-api-token"]:
            print(f"✅ {var}: {value[:20]}...")
        else:
            print(f"❌ {var}: Not set or using default value")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set these variables before testing")
        return False
    else:
        print("\n✅ All Confluence environment variables are set")
        return True


def test_confluence_api_connection():
    """Test direct Confluence API connection using atlassian package"""
    print("\n🔧 Testing Confluence API Connection")
    print("=" * 50)
    
    confluence_url = os.getenv("CONFLUENCE_URL")
    username = os.getenv("CONFLUENCE_USERNAME")
    api_token = os.getenv("CONFLUENCE_API_TOKEN",)
    
    if not all([confluence_url, username, api_token]):
        print("❌ Missing Confluence credentials")
        return False
    
    try:
        # Test Confluence API connection using atlassian package
        confluence = Confluence(
            url=confluence_url,
            token=api_token,
            #username=username,
            #password=api_token,
            cloud=True  # Set to False for Confluence Server
        )
        
        # Test by getting spaces
        spaces = confluence.get_all_spaces(limit=10)
        
        if spaces:
            print("✅ Confluence API connection successful")
            print(f"   Found {len(spaces)} spaces")
            
            # Show first few spaces (handle both list and dict formats)
            try:
                spaces_list = list(spaces) if hasattr(spaces, '__iter__') else [spaces]
                for i, space in enumerate(spaces_list[:3], 1):
                    if isinstance(space, dict):
                        name = space.get('name', 'Unknown')
                        key = space.get('key', 'Unknown')
                        print(f"   {i}. {name} ({key})")
                    else:
                        print(f"   {i}. {str(space)}")
            except Exception as e:
                print(f"   ⚠️  Could not display space details: {e}")
            
            return True
        else:
            print("⚠️  Confluence API connection successful but no spaces found")
            return True
            
    except Exception as e:
        print(f"❌ Confluence API connection error: {e}")
        return False


def test_mcp_tools():
    """Test MCP tools via HTTP requests"""
    print("\n🔧 Testing MCP Tools")
    print("=" * 50)
    
    # Test tools endpoint (if available)
    try:
        response = requests.get(f"{MCP_ENDPOINT.replace('/sse', '')}/tools", timeout=5)
        if response.status_code == 200:
            tools = response.json()
            print(f"✅ Found {len(tools)} MCP tools:")
            for tool in tools:
                print(f"   - {tool.get('name', 'Unknown')}")
        else:
            print("⚠️  Could not retrieve tools list")
    except Exception as e:
        print(f"⚠️  Tools test failed: {e}")


def main():
    """Run Confluence MCP tests"""
    print("🚀 Confluence MCP Testing")
    print("=" * 60)
    print()
    
    # Test 1: Environment variables
    if not test_confluence_environment():
        print("\n❌ Environment test failed - cannot proceed")
        return
    
    # Test 2: Confluence API connection
    if not test_confluence_api_connection():
        print("\n❌ Confluence API test failed - check credentials")
        return
    
    # Test 3: MCP server connection
    if not test_mcp_connection():
        print("\n❌ MCP server test failed - start the server first")
        return
    
    # Test 4: MCP tools
    test_mcp_tools()
    
    print("\n🎉 Confluence MCP tests completed!")
    print("\n📋 Next steps:")
    print("  1. Start the Confluence MCP server: python confluence_mcp_server.py")
    print("  2. Register with LlamaStack:")
    print("     curl -X POST http://localhost:8321/v1/toolgroups \\")
    print("       -d '{\"toolgroup_id\": \"confluence_mcp_group\", \"mcp_endpoint\": {\"uri\": \"http://localhost:8004/sse\"}}'")
    print("  3. Test with Generic Agent")


if __name__ == "__main__":
    main() 
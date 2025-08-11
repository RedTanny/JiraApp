#!/usr/bin/env python3
"""
Confluence MCP Server using FastMCP Framework
Provides Confluence API integration through MCP protocol
"""

import os
import logging
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from atlassian import Confluence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP app
app = FastMCP("confluence-mcp-server")

# Confluence configuration
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")

CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "")

# Global Confluence client instance
confluence_client = None


def get_confluence_client():
    """Get or create Confluence client with authentication"""
    global confluence_client
    
    if confluence_client is None:
        try:
            confluence_client = Confluence(
                url=CONFLUENCE_URL,                
                password=CONFLUENCE_API_TOKEN,
                cloud=True  # Set to False for Confluence Server
            )
            
            # Test connection
            spaces = confluence_client.get_all_spaces(limit=1)
            logger.info("Confluence connection successful")
            return confluence_client
            
        except Exception as e:
            logger.error(f"Error connecting to Confluence: {e}")
            return None
    
    return confluence_client


@app.tool()
def search_confluence_pages(
    query: str,
    space_key: Optional[str] = None,
    limit: int = 10,
    session_id: str = None
) -> str:
    """
    Search for Confluence pages using CQL (Confluence Query Language)
    
    Args:
        query: Search query string
        space_key: Optional space key to limit search
        limit: Maximum number of results to return (default: 10)
        session_id: Session identifier (provided by Llama Stack, ignored)
        
    Returns:
        Formatted string with search results
    """
    try:
        client = get_confluence_client()
        if not client:
            return "Error: Unable to connect to Confluence"
        
        # Build CQL query
        cql_query = f'text ~ "{query}"'
        if space_key:
            cql_query += f' AND space = "{space_key}"'
        
        logger.info(f"Searching Confluence with CQL: {cql_query}")
        
        # Use atlassian package search method
        results = client.cql(cql_query, limit=limit)
        
        if not results:
            return f"No Confluence pages found for query: '{query}'"
        
        # Format results
        formatted_results = []
        for page in results:
            page_info = {
                'title': page.get('title', 'No title'),
                'space': page.get('space', {}).get('name', 'Unknown space'),
                'space_key': page.get('space', {}).get('key', 'Unknown'),
                'url': f"{CONFLUENCE_URL}/wiki{page.get('_links', {}).get('webui', '')}",
                'last_modified': page.get('version', {}).get('when', 'Unknown'),
                'type': page.get('type', 'Unknown')
            }
            formatted_results.append(page_info)
        
        # Create formatted output
        output = f"Confluence Search Results ({len(formatted_results)} pages):\n"
        for i, page in enumerate(formatted_results, 1):
            output += f"{i}. {page['title']}\n"
            output += f"   Space: {page['space']} ({page['space_key']})\n"
            output += f"   URL: {page['url']}\n"
            output += f"   Last Modified: {page['last_modified']}\n"
            output += f"   Type: {page['type']}\n\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error searching Confluence: {e}")
        return f"Error: {str(e)}"


@app.tool()
def get_confluence_page(
    page_id: str,
    session_id: str = None
) -> str:
    """
    Get details of a specific Confluence page by ID
    
    Args:
        page_id: Confluence page ID
        session_id: Session identifier (provided by Llama Stack, ignored)
        
    Returns:
        Formatted string with page details
    """
    try:
        client = get_confluence_client()
        if not client:
            return "Error: Unable to connect to Confluence"
        
        logger.info(f"Getting Confluence page: {page_id}")
        
        # Use atlassian package to get page details
        page = client.get_page_by_id(page_id, expand='space,version,body.storage')
        
        if page:
            # Extract page information
            page_info = {
                'title': page.get('title', 'No title'),
                'space': page.get('space', {}).get('name', 'Unknown space'),
                'space_key': page.get('space', {}).get('key', 'Unknown'),
                'url': f"{CONFLUENCE_URL}/wiki{page.get('_links', {}).get('webui', '')}",
                'last_modified': page.get('version', {}).get('when', 'Unknown'),
                'version': page.get('version', {}).get('number', 'Unknown'),
                'content_length': len(page.get('body', {}).get('storage', {}).get('value', '')),
                'type': page.get('type', 'Unknown')
            }
            
            # Create formatted output
            output = f"Confluence Page Details:\n"
            output += f"Title: {page_info['title']}\n"
            output += f"Space: {page_info['space']} ({page_info['space_key']})\n"
            output += f"URL: {page_info['url']}\n"
            output += f"Last Modified: {page_info['last_modified']}\n"
            output += f"Version: {page_info['version']}\n"
            output += f"Content Length: {page_info['content_length']} characters\n"
            output += f"Type: {page_info['type']}\n"
            
            return output
        else:
            return f"Error: Confluence page not found with ID: {page_id}"
            
    except Exception as e:
        logger.error(f"Error getting Confluence page: {e}")
        return f"Error: {str(e)}"


@app.tool()
def get_confluence_spaces(
    session_id: str = None
) -> str:
    """
    Get list of available Confluence spaces
    
    Args:
        session_id: Session identifier (provided by Llama Stack, ignored)
        
    Returns:
        Formatted string with space list
    """
    try:
        client = get_confluence_client()
        if not client:
            return "Error: Unable to connect to Confluence"
        
        logger.info("Getting Confluence spaces")
        
        # Use atlassian package to get spaces
        spaces = client.get_all_spaces(limit=100)
        
        if not spaces:
            return "No Confluence spaces found"
        
        # Format results
        formatted_spaces = []
        for space in spaces:
            space_info = {
                'name': space.get('name', 'No name'),
                'key': space.get('key', 'No key'),
                'type': space.get('type', 'Unknown'),
                'description': space.get('description', {}).get('plain', {}).get('value', 'No description'),
                'url': f"{CONFLUENCE_URL}/wiki/spaces/{space.get('key', '')}"
            }
            formatted_spaces.append(space_info)
        
        # Create formatted output
        output = f"Confluence Spaces ({len(formatted_spaces)} spaces):\n"
        for i, space in enumerate(formatted_spaces, 1):
            output += f"{i}. {space['name']} ({space['key']})\n"
            output += f"   Type: {space['type']}\n"
            output += f"   Description: {space['description'][:100]}...\n"
            output += f"   URL: {space['url']}\n\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error getting Confluence spaces: {e}")
        return f"Error: {str(e)}"


@app.tool()
def search_confluence_content(
    query: str,
    space_key: Optional[str] = None,
    content_type: str = "page",
    limit: int = 10,
    session_id: str = None
) -> str:
    """
    Search for specific content types in Confluence
    
    Args:
        query: Search query string
        space_key: Optional space key to limit search
        content_type: Type of content to search (page, blogpost, comment)
        limit: Maximum number of results to return (default: 10)
        session_id: Session identifier (provided by Llama Stack, ignored)
        
    Returns:
        Formatted string with search results
    """
    try:
        client = get_confluence_client()
        if not client:
            return "Error: Unable to connect to Confluence"
        
        # Build CQL query
        cql_query = f'text ~ "{query}" AND type = "{content_type}"'
        if space_key:
            cql_query += f' AND space = "{space_key}"'
        
        logger.info(f"Searching Confluence content with CQL: {cql_query}")
        
        # Use atlassian package search method
        results = client.cql(cql_query, limit=limit)
        
        if not results:
            return f"No {content_type} content found for query: '{query}'"
        
        # Format results
        formatted_results = []
        for item in results:
            item_info = {
                'title': item.get('title', 'No title'),
                'space': item.get('space', {}).get('name', 'Unknown space'),
                'space_key': item.get('space', {}).get('key', 'Unknown'),
                'url': f"{CONFLUENCE_URL}/wiki{item.get('_links', {}).get('webui', '')}",
                'last_modified': item.get('version', {}).get('when', 'Unknown'),
                'type': item.get('type', 'Unknown')
            }
            formatted_results.append(item_info)
        
        # Create formatted output
        output = f"Confluence {content_type.title()} Search Results ({len(formatted_results)} items):\n"
        for i, item in enumerate(formatted_results, 1):
            output += f"{i}. {item['title']}\n"
            output += f"   Space: {item['space']} ({item['space_key']})\n"
            output += f"   URL: {item['url']}\n"
            output += f"   Last Modified: {item['last_modified']}\n"
            output += f"   Type: {item['type']}\n\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error searching Confluence content: {e}")
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Test connection on startup
    logger.info("Starting Confluence MCP Server...")
    
    if get_confluence_client():
        logger.info("Confluence connection test successful")
    else:
        logger.warning("Confluence connection test failed - check environment variables")
    
    # Run the FastMCP server with SSE transport
    app.run(transport="sse", port=8004) 
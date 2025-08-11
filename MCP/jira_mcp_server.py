#!/usr/bin/env python3
"""
JIRA MCP Server using FastMCP
Simple and robust implementation using fastmcp framework
"""

import os
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Any
from jira import JIRA

from fastmcp import FastMCP

# Set up detailed logging with timestamps
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('jira_mcp_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
JIRA_SERVER = os.environ.get("JIRA_SERVER", "YOUR_JIRA_SERVER_URL_HERE")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "YOUR_JIRA_API_TOKEN_HERE")

# Global JIRA client instance
_jira_client = None

def get_jira_client():
    """Get or create the JIRA client instance (singleton pattern)"""
    global _jira_client
    
    if _jira_client is None:
        logger.info(f"[JIRA] Creating JIRA client for server: {JIRA_SERVER}")
        headers = JIRA.DEFAULT_OPTIONS["headers"].copy()
        headers["Authorization"] = f"Bearer {JIRA_API_TOKEN}"  # Log only first 10 chars for security
        logger.debug(f"[JIRA] Using headers: {headers}")
        
        _jira_client = JIRA(server=JIRA_SERVER, options={"headers": headers})
        logger.info("[JIRA] JIRA client created successfully")
    
    return _jira_client

def create_jira_client():
    """Legacy function for backward compatibility - now returns the singleton client"""
    return get_jira_client()

# Create FastMCP instance
app = FastMCP("jira-mcp-server")

@app.tool()
async def get_jira_issue(issue_key: str) -> str:
    """
    Get details of a specific JIRA issue by key    
    Args:
        issue_key: JIRA issue key (e.g. NCS-8540)            
    Returns:
        Formatted string with issue details
    """
    logger.info(f"[JIRA] Fetching issue: {issue_key}")
    
    try:
        jira = get_jira_client()
        
        try:
            clean_issue_key = issue_key.strip('"')
            issue = jira.issue(clean_issue_key)
            logger.debug(f"[JIRA] Issue retrieved: {issue.key}")
        except Exception as e:
            logger.error(f"[JIRA] Failed to fetch issue {issue_key}: {e}")
            return f"Error: Failed to fetch issue {issue_key}: {str(e)}"
        
        result = {
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": issue.fields.status.name,
            "project": issue.fields.project.key,
            "priority": issue.fields.priority.name if issue.fields.priority else "None",
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
            "reporter": issue.fields.reporter.displayName if issue.fields.reporter else "Unknown",
            "created": str(issue.fields.created),
            "updated": str(issue.fields.updated),
            "description": issue.fields.description or "No description"
        }
        
        logger.info(f"[JIRA] Issue {issue_key} processed successfully")
        return f"JIRA Issue Details:\n{result}"
        
    except Exception as e:
        logger.error(f"[JIRA] Error fetching issue {issue_key}: {str(e)}")
        logger.error(f"[JIRA] Stack trace: {traceback.format_exc()}")
        return f"Error: {str(e)}"

@app.tool()
async def search_jira_issues(jql: str, max_results: int = 10) -> str:
    """
    Search for JIRA issues using JQL    
    Args:
        jql: JQL query string
        max_results: Maximum number of results to return (default: 10)            
    Returns:
        Formatted string with search results
    """
    logger.info(f"[JIRA] Searching with JQL: {jql}")
    logger.debug(f"[JIRA] Max results: {max_results}")
    
    try:
        jira = get_jira_client()
        
        try:
            issues = jira.search_issues(jql, maxResults=max_results)
            logger.info(f"[JIRA] Found {len(issues)} issues")
        except Exception as e:
            logger.error(f"[JIRA] Failed to search issues: {e}")
            return f"Error: Failed to search issues: {str(e)}"
        
        results = []
        for i, issue in enumerate(issues):
            logger.debug(f"[JIRA] Processing issue {i+1}/{len(issues)}: {issue.key}")
            results.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name if issue.fields.priority else "None",
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
            })
        
        logger.info(f"[JIRA] Search completed successfully")
        return f"JIRA Search Results ({len(results)} issues):\n{results}"
        
    except Exception as e:
        logger.error(f"[JIRA] Error searching issues: {str(e)}")
        logger.error(f"[JIRA] Stack trace: {traceback.format_exc()}")
        return f"Error: {str(e)}"


if __name__ == "__main__":
    logger.info(f"[STARTUP] JIRA MCP Server starting at {datetime.now()}")
    logger.info(f"[SERVER] JIRA Server: {JIRA_SERVER}")
    logger.info(f"[SERVER] Log level: {logger.getEffectiveLevel()}")
    logger.info("[SERVER] Starting FastMCP server...")
    
    # Initialize JIRA client at startup
    try:
        logger.info("[JIRA] Initializing JIRA client...")
        jira_client = get_jira_client()
        
        # Test the connection by getting user info
        try:
            user = jira_client.myself()
            user_name = getattr(user, 'displayName', getattr(user, 'name', 'Unknown'))
            logger.info(f"[JIRA] Successfully authenticated as: {user_name}")
        except Exception as e:
            logger.warning(f"[JIRA] Could not verify user authentication: {e}")
        
        logger.info("[JIRA] JIRA client initialization completed")
        
    except Exception as e:
        logger.error(f"[JIRA] Failed to initialize JIRA client: {e}")
        logger.error(f"[JIRA] Stack trace: {traceback.format_exc()}")
        logger.warning("[JIRA] Server will start but JIRA tools may fail")
    
    # Run the FastMCP server with SSE transport (for Llama Stack compatibility)
    app.run(transport="sse", port=8003) 
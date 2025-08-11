#!/usr/bin/env python3
"""
JIRA Table Client - Experimental
Interactive client with beautiful Unicode table formatting for JIRA results
"""

import os
import sys
import fire
from typing import Optional, List, Dict, Any

# Check for required dependencies
try:
    from llama_stack_client import LlamaStackClient
    from llama_stack_client.lib.agents.agent import Agent
    from llama_stack_client.lib.agents.event_logger import EventLogger
    from llama_stack_client.types.agent_create_params import AgentConfig
except ImportError as e:
    print(f"❌ Error: Required dependency not found: {e}")
    print("Please install llama-stack-client: pip install llama-stack-client")
    sys.exit(1)

try:
    from termcolor import colored
except ImportError as e:
    print(f"❌ Error: Required dependency not found: {e}")
    print("Please install termcolor: pip install termcolor")
    sys.exit(1)


def format_status_with_color(status: str) -> str:
    """Format status with appropriate color and emoji"""
    status_lower = status.lower()
    
    if 'closed' in status_lower or 'resolved' in status_lower:
        return colored("🟢 " + status, 'green')
    elif 'in progress' in status_lower or 'progress' in status_lower:
        return colored("🟡 " + status, 'yellow')
    elif 'blocked' in status_lower or 'critical' in status_lower:
        return colored("🔴 " + status, 'red')
    elif 'open' in status_lower or 'new' in status_lower:
        return colored("🔵 " + status, 'blue')
    elif 'obsolete' in status_lower:
        return colored("⚪ " + status, 'white')
    else:
        return colored("⚪ " + status, 'white')


def format_priority_with_color(priority: str) -> str:
    """Format priority with appropriate color and emoji"""
    priority_lower = priority.lower()
    
    if 'critical' in priority_lower:
        return colored("🔴 " + priority, 'red')
    elif 'high' in priority_lower or 'major' in priority_lower:
        return colored("🟠 " + priority, 'red')
    elif 'medium' in priority_lower:
        return colored("🟡 " + priority, 'yellow')
    elif 'low' in priority_lower or 'minor' in priority_lower:
        return colored("🟢 " + priority, 'green')
    else:
        return colored("⚪ " + priority, 'white')


def create_unicode_table(headers: List[str], rows: List[List[str]], title: str = "") -> str:
    """Create a beautiful Unicode box drawing table"""
    
    # Unicode box drawing characters
    TOP_LEFT = "┌"
    TOP_RIGHT = "┐"
    BOTTOM_LEFT = "└"
    BOTTOM_RIGHT = "┘"
    HORIZONTAL = "─"
    VERTICAL = "│"
    TOP_TEE = "┬"
    BOTTOM_TEE = "┴"
    LEFT_TEE = "├"
    RIGHT_TEE = "┤"
    CROSS = "┼"
    
    if not rows:
        return "No data to display"
    
    # Calculate column widths
    col_widths = []
    for i in range(len(headers)):
        max_width = len(headers[i])
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(row[i]))
        col_widths.append(max_width + 2)  # Add padding
    
    # Build the table
    table_lines = []
    
    # Title
    if title:
        table_lines.append(colored(f"\n📊 {title}", 'cyan', attrs=['bold']))
        table_lines.append("")
    
    # Top border
    top_line = TOP_LEFT
    for i, width in enumerate(col_widths):
        top_line += HORIZONTAL * width
        if i < len(col_widths) - 1:
            top_line += TOP_TEE
    top_line += TOP_RIGHT
    table_lines.append(top_line)
    
    # Header row
    header_line = VERTICAL
    for i, header in enumerate(headers):
        header_line += f" {colored(header, 'cyan', attrs=['bold']):<{col_widths[i]-1}}"
        header_line += VERTICAL
    table_lines.append(header_line)
    
    # Separator line
    separator_line = LEFT_TEE
    for i, width in enumerate(col_widths):
        separator_line += HORIZONTAL * width
        if i < len(col_widths) - 1:
            separator_line += CROSS
    separator_line += RIGHT_TEE
    table_lines.append(separator_line)
    
    # Data rows
    for row in rows:
        row_line = VERTICAL
        for i, cell in enumerate(row):
            if i < len(col_widths):
                row_line += f" {cell:<{col_widths[i]-1}}"
                row_line += VERTICAL
        table_lines.append(row_line)
    
    # Bottom border
    bottom_line = BOTTOM_LEFT
    for i, width in enumerate(col_widths):
        bottom_line += HORIZONTAL * width
        if i < len(col_widths) - 1:
            bottom_line += BOTTOM_TEE
    bottom_line += BOTTOM_RIGHT
    table_lines.append(bottom_line)
    
    return "\n".join(table_lines)


def parse_jira_search_results(text: str) -> Dict[str, Any]:
    """Parse JIRA search results from text response"""
    try:
        # Look for the list of issues in the response
        if "JIRA Search Results" in text and "[" in text:
            # Extract the list part
            start_idx = text.find("[")
            end_idx = text.rfind("]") + 1
            
            if start_idx != -1 and end_idx != -1:
                issues_text = text[start_idx:end_idx]
                
                # Parse the Python dictionary format
                issues = []
                
                # Split by individual issue entries
                # Remove the outer brackets and split by "}, {"
                clean_text = issues_text.strip("[]")
                issue_entries = clean_text.split("}, {")
                
                for entry in issue_entries:
                    # Clean up the entry
                    entry = entry.strip().strip("{}")
                    if not entry:
                        continue
                    
                    # Parse the key-value pairs
                    issue = {}
                    # Split by "', '" to get individual fields
                    parts = entry.split("', '")
                    
                    for part in parts:
                        if "': '" in part:
                            try:
                                key, value = part.split("': '", 1)
                                key = key.strip("'")
                                value = value.strip("'")
                                issue[key] = value
                            except ValueError:
                                continue
                    
                    if issue:
                        issues.append(issue)
                
                if issues:
                    return {
                        "type": "search_results",
                        "issues": issues,
                        "total_count": len(issues)
                    }
        
        return {"type": "text", "content": text}
        
    except Exception as e:
        print(f"Debug: Parsing error: {e}")
        print(f"Debug: Text to parse: {text[:200]}...")
        return {"type": "error", "content": f"Failed to parse results: {e}"}


def format_jira_issues_table(issues: List[Dict[str, str]]) -> str:
    """Format JIRA issues into a beautiful table"""
    if not issues:
        return "No issues found"
    
    # Define headers
    headers = ["Issue Key", "Summary", "Status", "Priority", "Assignee"]
    
    # Prepare rows
    rows = []
    for issue in issues:
        key = issue.get('key', 'N/A')
        summary = issue.get('summary', 'N/A')
        status = format_status_with_color(issue.get('status', 'N/A'))
        priority = format_priority_with_color(issue.get('priority', 'N/A'))
        assignee = issue.get('assignee', 'N/A')
        
        # Truncate summary if too long
        if len(summary) > 50:
            summary = summary[:47] + "..."
        
        rows.append([key, summary, status, priority, assignee])
    
    # Create table
    return create_unicode_table(headers, rows, f"JIRA Issues ({len(issues)} found)")


def main(host: str = "localhost", port: int = 8321):
    """
    Interactive JIRA Table Client with beautiful Unicode formatting
    
    Args:
        host: Llama Stack server host (default: localhost)
        port: Llama Stack server port (default: 8321)
    """
    
    print(colored("🚀 Starting JIRA Table Client", "green", attrs=['bold']))
    print(colored("📊 Beautiful Unicode table formatting enabled", "cyan"))
    print(f"Connecting to: http://{host}:{port}")
    
    try:
        client = LlamaStackClient(
            base_url=f"http://{host}:{port}",
        )
        print(colored("✅ Successfully connected to Llama Stack server", "green"))
    except Exception as e:
        print(colored(f"❌ Failed to connect to Llama Stack server: {e}", "red"))
        print(colored("Please ensure the Llama Stack server is running and accessible", "yellow"))
        return

    # Check available models
    try:
        available_models = [
            model.identifier for model in client.models.list() if model.model_type == "llm"
        ]

        if not available_models:
            print(colored("No available models. Exiting.", "red"))
            return
        else:
            selected_model = available_models[0]
            print(f"Using model: {colored(selected_model, 'cyan')}")
    except Exception as e:
        print(colored(f"❌ Failed to fetch available models: {e}", "red"))
        return

    # Check available toolgroups
    try:
        available_toolgroups = [tg.identifier for tg in client.toolgroups.list()]
        print(f"Available toolgroups: {colored(', '.join(available_toolgroups), 'magenta')}")
    except Exception as e:
        print(colored(f"❌ Failed to fetch toolgroups: {e}", "red"))
        return
    
    # Verify JIRA tools are available
    jira_toolgroup_name = "jira_mcp_group"
    if jira_toolgroup_name not in available_toolgroups:
        print(colored(f"⚠️  Warning: {jira_toolgroup_name} toolgroup not found!", "yellow"))
        print("Available toolgroups:", available_toolgroups)
        print(colored("Please ensure the JIRA MCP server is properly configured", "yellow"))
    else:
        print(colored("✅ JIRA tools found and ready!", "green"))

    # Create agent configuration with JIRA tools
    agent_config = AgentConfig(
        model=selected_model,
        instructions="""You are a helpful JIRA assistant with access to JIRA tools.
        
You can:
- Get information about specific JIRA issues (use get_jira_issue tool)
- Search for issues using JQL queries (use search_jira_issues tool)
- Provide insights and analysis about JIRA data

When a user asks about a JIRA issue or wants to search for issues, use the appropriate tools to fetch real data.
Always provide clear, helpful responses based on the actual JIRA data you retrieve.""",
        
        sampling_params={
            "strategy": {"type": "top_p", "temperature": 0.7, "top_p": 0.9},
        },
        
        toolgroups=[
            jira_toolgroup_name,        # Our JIRA MCP tools
        ],
        
        tool_choice="auto",
        enable_session_persistence=True,
    )
    
    print(colored("\n🤖 Creating JIRA-enabled agent...", "blue"))
    
    try:
        agent = Agent(client, agent_config)
        session_id = agent.create_session("jira-table-session")
        print(f"Session ID: {colored(session_id, 'cyan')}")
    except Exception as e:
        print(colored(f"❌ Failed to create agent: {e}", "red"))
        return

    print(colored("\n💡 Try asking about JIRA issues! Examples:", "yellow"))
    print("  - Search for issues assigned to me")
    print("  - Show me high priority bugs")
    print("  - Get details for issue NCS-8540")
    print("  - Find issues in the NCS project")
    print(colored("\nPress Enter with empty prompt to exit.\n", "yellow"))

    try:
        while True:
            try:
                prompt = input(colored("You: ", "green", attrs=["bold"])).strip()
                if not prompt:
                    print(colored("👋 Goodbye!", "green"))
                    break
                    
                print(colored("\n🤖 Assistant:", "blue", attrs=["bold"]))
                
                response = agent.create_turn(
                    messages=[
                        {
                            "role": "user", 
                            "content": prompt,
                        }
                    ],
                    session_id=session_id,
                )

                # Process the response and format tables
                for log in EventLogger().log(response):
                    if hasattr(log, 'content') and log.content:
                        # Check if this is a tool response with JIRA data
                        if hasattr(log, 'tool_name') and log.tool_name:
                            if log.tool_name == "search_jira_issues":
                                # Parse and format search results
                                parsed = parse_jira_search_results(log.content)
                                if parsed["type"] == "search_results":
                                    table = format_jira_issues_table(parsed["issues"])
                                    print(table)
                                else:
                                    print(log.content)
                            else:
                                print(log.content)
                        else:
                            # Check if the content contains JIRA search results even without tool_name
                            if "JIRA Search Results" in log.content:
                                parsed = parse_jira_search_results(log.content)
                                if parsed["type"] == "search_results":
                                    table = format_jira_issues_table(parsed["issues"])
                                    print(table)
                                else:
                                    print(log.content)
                            else:
                                print(log.content)
                    else:
                        log.print()
                    
                print("\n" + "="*80 + "\n")
                
            except KeyboardInterrupt:
                print(colored("\n👋 Goodbye!", "green"))
                break
            except Exception as e:
                print(colored(f"❌ Error during conversation: {e}", "red"))
                print(colored("Continuing with next prompt...", "yellow"))
                continue
    finally:
        # Cleanup
        try:
            print(colored("🧹 Cleaning up resources...", "blue"))
        except Exception as e:
            print(colored(f"⚠️  Warning: Error during cleanup: {e}", "yellow"))


if __name__ == "__main__":
    fire.Fire(main) 
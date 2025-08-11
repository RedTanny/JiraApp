#!/usr/bin/env python3
"""
JIRA + Llama Stack Client
Interactive client that uses JIRA tools via MCP integration
"""

import os
import sys
import fire
from typing import Optional

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


def main(host: str = "localhost", port: int = 8321):
    """
    Interactive JIRA + Llama Stack client
    
    Args:
        host: Llama Stack server host (default: localhost)
        port: Llama Stack server port (default: 8321)
    """
    
    print(colored("🚀 Starting JIRA + Llama Stack Client", "green"))
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

    # Check available shields
    try:
        available_shields = [shield.identifier for shield in client.shields.list()]
        if not available_shields:
            print(colored("No available shields. Disabling safety.", "yellow"))
        else:
            print(f"Available shields found: {available_shields}")
    except Exception as e:
        print(colored(f"⚠️  Warning: Could not fetch shields: {e}", "yellow"))
        available_shields = []

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
            "builtin::websearch",       # Keep web search for additional context
        ],
        
        tool_choice="auto",
        input_shields=available_shields if available_shields else [],
        output_shields=available_shields if available_shields else [],
        enable_session_persistence=True,
    )
    
    print(colored("\n🤖 Creating JIRA-enabled agent...", "blue"))
    
    try:
        agent = Agent(client, agent_config)
        session_id = agent.create_session("jira-session")
        print(f"Session ID: {colored(session_id, 'cyan')}")
    except Exception as e:
        print(colored(f"❌ Failed to create agent: {e}", "red"))
        return

    print(colored("\n💡 Try asking about JIRA issues! Examples:", "yellow"))
    print("  - Get issue NCS-8540")
    print("  - Search for high priority bugs")  
    print("  - Show me recent issues in the NCS project")
    print("  - What's the status of issue ABC-123?")
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

                # Log the response with nice formatting
                for log in EventLogger().log(response):
                    log.print()
                    
                print("\n" + "="*50 + "\n")
                
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
            # Note: Add cleanup code here if the API provides it
        except Exception as e:
            print(colored(f"⚠️  Warning: Error during cleanup: {e}", "yellow"))


if __name__ == "__main__":
    fire.Fire(main) 
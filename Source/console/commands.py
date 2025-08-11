"""
Built-in commands for console UI.

Handles system commands like /help, /tools, /status, etc.
"""

from typing import Dict, Callable, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class ConsoleCommands:
    """Handles built-in console commands."""
    
    def __init__(self, console: Console, orchestrator: Any = None):
        self.console = console
        self.orchestrator = orchestrator
        self.commands: Dict[str, Callable] = {}
        self._register_commands()
    
    def _register_commands(self) -> None:
        """Register all available commands."""
        self.commands = {
            'help': self._cmd_help,
            'tools': self._cmd_tools,
            'status': self._cmd_status,
            'clear': self._cmd_clear,
            'quit': self._cmd_quit,
            'exit': self._cmd_quit,
        }
    
    def execute_command(self, command: str, args: List[str] = None) -> bool:
        """
        Execute a built-in command.
        
        Args:
            command: Command name (without /)
            args: Optional command arguments
            
        Returns:
            True if command was executed, False if not found
        """
        if args is None:
            args = []
        
        if command in self.commands:
            try:
                self.commands[command](*args)
                return True
            except Exception as e:
                self.console.print(f"[red]Error executing command '{command}': {e}[/red]")
                return True  # Command was found but failed
        
        return False
    
    def get_available_commands(self) -> List[str]:
        """Get list of available command names."""
        return list(self.commands.keys())
    
    def _cmd_help(self, *args) -> None:
        """Show help information."""
        if args:
            # Show help for specific command
            command = args[0].lower()
            if command in self.commands:
                self._show_command_help(command)
            else:
                self.console.print(f"[red]Unknown command: {command}[/red]")
        else:
            # Show general help
            self._show_general_help()
    
    def _show_general_help(self) -> None:
        """Show general help information."""
        help_text = """
[bold cyan]MCP JIRA Console - Available Commands[/bold cyan]

[bold]Built-in Commands:[/bold]
  /help          - Show this help message
  /help <cmd>    - Show help for specific command
  /tools         - List available MCP tools
  /status        - Show system status
  /clear         - Clear console screen
  /quit          - Exit the application

[bold]Natural Language:[/bold]
  Type any natural language request and the system will:
  1. Plan the execution using LLM
  2. Execute appropriate tools via MCP
  3. Display results in formatted tables

[bold]Examples:[/bold]
  "Find all open JIRA tickets for project PROJ"
  "Update Confluence page with latest status"
  "Search for tickets assigned to john.doe"
        """
        
        panel = Panel(help_text.strip(), title="Help", border_style="cyan")
        self.console.print(panel)
    
    def _show_command_help(self, command: str) -> None:
        """Show help for a specific command."""
        command_help = {
            'help': "Show help information. Use '/help <command>' for specific help.",
            'tools': "List all available MCP tools and their descriptions.",
            'status': "Show current system status, active tools, and connection health.",
            'clear': "Clear the console screen for better readability.",
            'quit': "Exit the console application safely."
        }
        
        help_text = f"[bold cyan]Command: /{command}[/bold cyan]\n\n{command_help.get(command, 'No help available for this command.')}"
        panel = Panel(help_text, title=f"Help: /{command}", border_style="cyan")
        self.console.print(panel)
    
    def _cmd_tools(self, *args) -> None:
        """List available MCP tools."""
        if not self.orchestrator:
            self.console.print("[yellow]Orchestrator not available - cannot list tools[/yellow]")
            return
        
        try:
            # Get tools from orchestrator
            llm = self.orchestrator.get_llm_planner()
            tools = llm.get_tools()
            
            if not tools:
                self.console.print("[yellow]No tools available[/yellow]")
                return
            
            # Create tools table
            from .table_reporter import TableReporter
            reporter = TableReporter(self.console)
            
            tools_data = []
            for tool in tools:
                tools_data.append({
                    'Tool Name': tool.name,
                    'Description': tool.description
                })
            
            reporter.display_table(tools_data, title="Available MCP Tools")
            
        except Exception as e:
            self.console.print(f"[red]Error listing tools: {e}[/red]")
    
    def _cmd_status(self, *args) -> None:
        """Show system status."""
        status_data = {
            'Console': 'Active',
            'Orchestrator': 'Available' if self.orchestrator else 'Not Available',
            'MCP Layer': self.orchestrator.get_mcp_layer_status(),
            'LLM': self.orchestrator.get_llm_model()
        }
        
        from .table_reporter import TableReporter
        reporter = TableReporter(self.console)
        table = reporter.create_summary_table(status_data, title="System Status")
        self.console.print(table)
    
    def _cmd_clear(self, *args) -> None:
        """Clear console screen."""
        self.console.clear()
        self.console.print("[bold cyan]Console cleared[/bold cyan]")
    
    def _cmd_quit(self, *args) -> None:
        """Exit the application."""
        self.console.print("[yellow]Exiting MCP JIRA Console...[/yellow]")
        # The main loop should handle the actual exit
        raise SystemExit(0) 
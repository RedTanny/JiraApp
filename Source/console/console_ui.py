"""
Console UI for interactive user interface.

Provides an interactive console interface with command processing,
status display, and result formatting.
"""

import sys
from typing import Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from .commands import ConsoleCommands
from .status_indicator import StatusIndicator
from .table_reporter import TableReporter
from .view_manager import ViewManager
from .history_manager import HistoryManager
from .readline_input import ReadlineInput


class ConsoleUI:
    """Interactive console interface for the MCP JIRA application."""
    
    def __init__(self, orchestrator: Any = None):
        self.console = Console()
        self.orchestrator = orchestrator
        self.running = True
        
        # Initialize components
        self.table_reporter = TableReporter(self.console)
        self.status = StatusIndicator(self.console)
        self.commands = ConsoleCommands(self.console, self.orchestrator)
        
        # Initialize view system
        self.view_manager = ViewManager(self.console, self.table_reporter)
        self._register_specialized_views()
        
        # Initialize history system
        self.history_manager = HistoryManager()
        self.enhanced_input = ReadlineInput(self.console, self.history_manager)
        
        # Console settings
        self.prompt = "mcp_jira> "
        
        # Welcome message
        self._show_welcome()
    
    def _register_specialized_views(self) -> None:
        """Register specialized views for different tool types."""
        from .jira_issue_view import JiraIssueView
        from .jira_search_view import JiraSearchView
        
        # Register JIRA issue view
        jira_issue_view = JiraIssueView(self.console, self.table_reporter)
        self.view_manager.register_view("get_jira_issue", jira_issue_view)
        
        # Register JIRA search view
        jira_search_view = JiraSearchView(self.console, self.table_reporter)
        self.view_manager.register_view("search_jira_issues", jira_search_view)
        
        # TODO: Add more specialized views as they are implemented
        # self.view_manager.register_view("get_epic", JiraEpicView(self.console, self.table_reporter))
    
    def _show_welcome(self) -> None:
        """Display welcome message."""
        welcome_text = """
[bold cyan]Welcome to MCP JIRA Console![/bold cyan]

This console provides an interactive interface to:
• Query JIRA and Confluence via MCP servers
• Execute complex workflows using LLM planning
• View results in formatted tables
• Monitor system status and tools

Type [bold]/help[/bold] to see available commands, or type your request in natural language.
        """
        
        panel = Panel(welcome_text.strip(), title="MCP JIRA Console", border_style="cyan")
        self.console.print(panel)
        self.console.print()  # Empty line
    
    def start(self) -> None:
        """Start the console interactive loop."""
        self.running = True
        
        try:
            while self.running:
                try:
                    # Get user input with enhanced history support
                    user_input = self.enhanced_input.get_input(self.prompt)
                    
                    if not user_input.strip():
                        continue
                    
                    # Process input
                    self._process_input(user_input.strip())
                    
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Use /quit to exit the application[/yellow]")
                    continue
                except EOFError:
                    self.console.print("\n[yellow]End of input detected[/yellow]")
                    break
                    
        except SystemExit:
            self.console.print("[green]Goodbye![/green]")
            sys.exit(0)
        except Exception as e:
            self.console.print(f"[red]Unexpected error: {e}[/red]")
            self.console.print_exception()
        finally:
            self.running = False
    
    def _process_input(self, user_input: str) -> None:
        """Process user input and route to appropriate handler."""
        # Check if it's a built-in command
        if user_input.startswith('/'):
            self._handle_builtin_command(user_input)
        else:
            # Handle natural language request
            self._handle_natural_language_request(user_input)
    
    def _handle_builtin_command(self, command_input: str) -> None:
        """Handle built-in commands starting with /."""
        # Parse command and arguments
        parts = command_input[1:].split()  # Remove / and split
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Execute command
        if not self.commands.execute_command(command, args):
            self.console.print(f"[red]Unknown command: /{command}[/red]")
            self.console.print("Type /help to see available commands.")
    
    def _handle_natural_language_request(self, user_input: str) -> None:
        """Handle natural language requests through the orchestrator."""
        if not self.orchestrator:
            self.console.print("[red]Orchestrator not available - cannot process requests[/red]")
            return
        
        try:
            # Start operation with status indicator
            self.status.start_operation("Processing your request...", "processing")
            
            # Process through orchestrator
            self.status.update_status("Planning with LLM...", "processing")
            events = self.orchestrator.process_user_request(user_input)
            self.orchestrator.execute_loop(events)
            # Show results
            self.status.update_status("Displaying results...", "processing")
            self._display_results(events, user_input)
            
            # Complete operation
            self.status.complete_operation("Request completed successfully")
            
        except Exception as e:
            self.status.show_error(f"Error processing request: {e}")
            if hasattr(e, '__traceback__'):
                self.console.print_exception()
    
    def _display_results(self, events: list, original_request: str) -> None:
        """Display the results of processing a request."""
        if not events:
            self.console.print("[yellow]No results to display[/yellow]")
            return
        
        # Show summary of what was processed
        summary_data = {
            'Original Request': original_request,
            'Events Processed': len(events),
            'Event Types': ', '.join(set(event.command_type.value for event in events))
        }
        
        summary_table = self.table_reporter.create_summary_table(
            summary_data, 
            title="Request Summary"
        )
        self.console.print(summary_table)
        self.console.print()
        
        # Display results for each event type
        for event in events:
            self._display_event_result(event)
    
    def _display_event_result(self, event: Any) -> None:
        """Display the result of a single event using specialized views."""
        event_type = event.command_type.value
        event_tool = event.tool_name + " " + ", ".join(event.tool_args)
        
        # Create event header
        header_text = f"[bold cyan]{event_type}[/bold cyan]: {event_tool}"
        self.console.print(header_text)
        
        # Use specialized view manager to render results
        if hasattr(event, 'result') and event.result:
            self.view_manager.render_event(event, event.result)
        else:
            self.console.print(f"[dim]No results available for {event_type}[/dim]")
        
        self.console.print()  # Empty line between events
    
    def stop(self) -> None:
        """Stop the console."""
        self.running = False
        self.console.print("[yellow]Console stopped[/yellow]")
    
    def set_orchestrator(self, orchestrator: Any) -> None:
        """Set the orchestrator instance."""
        self.orchestrator = orchestrator
        self.commands.orchestrator = orchestrator
    
    def get_console(self) -> Console:
        """Get the rich console instance."""
        return self.console
    
    def print_message(self, message: str, style: str = "white") -> None:
        """Print a message with optional styling."""
        self.console.print(f"[{style}]{message}[/{style}]")
    
    def print_error(self, message: str) -> None:
        """Print an error message."""
        self.console.print(f"[red]❌ {message}[/red]")
    
    def print_success(self, message: str) -> None:
        """Print a success message."""
        self.console.print(f"[green]✅ {message}[/green]")
    
    def print_info(self, message: str) -> None:
        """Print an informational message."""
        self.console.print(f"[blue]ℹ️ {message}[/blue]") 
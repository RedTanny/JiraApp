"""
Generic view for displaying any type of data.

This view serves as the fallback when no specialized view exists
or when specialized views fail to render.
"""

from typing import Any
from rich.console import Console
from .base_view import BaseView
from .table_reporter import TableReporter


class GenericView(BaseView):
    """Generic fallback view for any data type."""
    
    def can_handle(self, tool_name: str, result: Any) -> bool:
        """
        Generic view can handle any tool and result type.
        
        Args:
            tool_name: Name of the MCP tool (unused in generic view)
            result: The result data (unused in generic view)
            
        Returns:
            Always True - generic view handles everything
        """
        return True
    
    def render(self, event: Any, result: Any) -> None:
        """
        Render the result using generic table formatting.
        
        Args:
            event: The parsed event containing tool information
            result: The result data to be displayed
        """
        # Show the tool name and command type
        event_type = getattr(event, 'command_type', None)
        if event_type:
            self.console.print(f"[bold cyan]Tool:[/bold cyan] {event.tool_name}")
            self.console.print(f"[bold cyan]Type:[/bold cyan] {event_type.value}")
            self.console.print()
        
        # Handle different result types
        if isinstance(result, dict):
            self._render_dict_result(result)
        elif isinstance(result, list):
            self._render_list_result(result)
        elif isinstance(result, str):
            self._render_string_result(result)
        else:
            self._render_unknown_result(result)
    
    def _render_dict_result(self, result: dict) -> None:
        """Render dictionary results as a table."""
        if not result:
            self.console.print("[dim]Empty result[/dim]")
            return
        
        # Convert dict to list of key-value pairs for table display
        table_data = [{"Field": k, "Value": str(v)} for k, v in result.items()]
        self.table_reporter.display_table(table_data, title="Result Data")
    
    def _render_list_result(self, result: list) -> None:
        """Render list results as a table."""
        if not result:
            self.console.print("[dim]Empty result[/dim]")
            return
        
        # If list contains dictionaries, display as table
        if result and isinstance(result[0], dict):
            self.table_reporter.display_table(result, title="Result Data")
        else:
            # Simple list - display as numbered items
            for i, item in enumerate(result, 1):
                self.console.print(f"{i}. {item}")
    
    def _render_string_result(self, result: str) -> None:
        """Render string results as formatted text."""
        if not result:
            self.console.print("[dim]Empty result[/dim]")
            return
        
        # Check if it looks like JSON or structured data
        if result.startswith('{') or result.startswith('['):
            try:
                import json
                parsed = json.loads(result)
                if isinstance(parsed, dict):
                    self._render_dict_result(parsed)
                elif isinstance(parsed, list):
                    self._render_list_result(parsed)
                else:
                    self.console.print(result)
            except (json.JSONDecodeError, ValueError):
                self.console.print(result)
        else:
            # Regular text - display as is
            self.console.print(result)
    
    def _render_unknown_result(self, result: Any) -> None:
        """Render unknown result types."""
        self.console.print(f"[dim]Result type: {type(result).__name__}[/dim]")
        self.console.print(str(result)) 
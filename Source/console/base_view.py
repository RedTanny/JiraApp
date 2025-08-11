"""
Base view interface for specialized data display.

All specialized views inherit from this base class to ensure consistent
interface and behavior across different view types.
"""

from abc import ABC, abstractmethod
from typing import Any
from rich.console import Console
from .table_reporter import TableReporter


class BaseView(ABC):
    """Base interface for all specialized views."""
    
    def __init__(self, console: Console, table_reporter: TableReporter):
        self.console = console
        self.table_reporter = table_reporter
    
    @abstractmethod
    def can_handle(self, tool_name: str, result: Any) -> bool:
        """
        Check if this view can handle the given tool and result.
        
        Args:
            tool_name: Name of the MCP tool that generated the result
            result: The result data to be displayed
            
        Returns:
            True if this view can handle the tool/result combination
        """
        pass
    
    @abstractmethod
    def render(self, event: Any, result: Any) -> None:
        """
        Render the specialized view for the event result.
        
        Args:
            event: The parsed event containing tool information
            result: The result data to be displayed
        """
        pass
    
    def _show_error(self, message: str) -> None:
        """
        Display an error message at the bottom of the view.
        
        Args:
            message: Error message to display
        """
        self.console.print(f"[red]Error: {message}[/red]")
    
    def _safe_render(self, event: Any, result: Any) -> bool:
        """
        Safely attempt to render the view with error handling.
        
        Args:
            event: The parsed event
            result: The result data
            
        Returns:
            True if rendering succeeded, False if it failed
        """
        try:
            self.render(event, result)
            return True
        except Exception as e:
            self._show_error(f"Failed to render view: {str(e)}")
            return False 
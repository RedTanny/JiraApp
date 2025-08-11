"""
View manager for routing events to specialized view renderers.

The ViewManager automatically selects the appropriate view based on the
tool name and provides fallback to generic views when needed.
"""

from typing import Any, Dict, Type
from rich.console import Console
from .base_view import BaseView
from .table_reporter import TableReporter


class ViewManager:
    """Manages specialized views and routes events to appropriate renderers."""
    
    def __init__(self, console: Console, table_reporter: TableReporter):
        self.console = console
        self.table_reporter = table_reporter
        self.views: Dict[str, BaseView] = {}
        self._register_default_views()
    
    def _register_default_views(self) -> None:
        """Register the default generic view."""
        from .generic_view import GenericView
        self.views["default"] = GenericView(self.console, self.table_reporter)
    
    def register_view(self, tool_name: str, view: BaseView) -> None:
        """
        Register a specialized view for a specific tool.
        
        Args:
            tool_name: Name of the MCP tool this view handles
            view: The view instance to register
        """
        self.views[tool_name] = view
    
    def render_event(self, event: Any, result: Any) -> None:
        """
        Route event to appropriate specialized view.
        
        Args:
            event: The parsed event containing tool information
            result: The result data to be displayed
        """
        # Find the best matching view
        view = self._find_best_view(event.tool_name, result)
        
        # Render using the specialized view
        if not view._safe_render(event, result):
            # If specialized view fails, fall back to generic view
            self.console.print("[yellow]Falling back to generic view...[/yellow]")
            generic_view = self.views["default"]
            generic_view.render(event, result)
    
    def _find_best_view(self, tool_name: str, result: Any) -> BaseView:
        """
        Find the best view for the given tool and result.
        
        Args:
            tool_name: Name of the MCP tool
            result: The result data
            
        Returns:
            The best matching view instance
        """
        # Try exact tool name match first
        if tool_name in self.views:
            view = self.views[tool_name]
            if view.can_handle(tool_name, result):
                return view
        
        # Try pattern matching for similar tools
        for pattern, view in self.views.items():
            if pattern != "default" and self._matches_pattern(tool_name, pattern):
                if view.can_handle(tool_name, result):
                    return view
        
        # Fall back to default view
        return self.views["default"]
    
    def _matches_pattern(self, tool_name: str, pattern: str) -> bool:
        """
        Check if a tool name matches a pattern.
        
        Args:
            tool_name: The actual tool name
            pattern: The pattern to match against
            
        Returns:
            True if the tool name matches the pattern
        """
        # Simple pattern matching - can be enhanced later
        if pattern == tool_name:
            return True
        
        # Handle wildcard patterns (e.g., "search_*" matches "search_issues")
        if pattern.endswith("*"):
            return tool_name.startswith(pattern[:-1])
        
        return False
    
    def get_registered_views(self) -> Dict[str, str]:
        """
        Get a list of registered views and their tool names.
        
        Returns:
            Dictionary mapping tool names to view class names
        """
        return {
            tool_name: view.__class__.__name__ 
            for tool_name, view in self.views.items()
        } 
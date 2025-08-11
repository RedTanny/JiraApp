"""
Specialized view for displaying JIRA search results.

This view formats JIRA search results in a clean, readable table
format with proper columns and formatting.
"""

import re
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.box import ROUNDED
from .base_view import BaseView
from .table_reporter import TableReporter


class JiraSearchView(BaseView):
    """Specialized view for JIRA search results."""
    
    def can_handle(self, tool_name: str, result: Any) -> bool:
        """
        Check if this view can handle JIRA search results.
        
        Args:
            tool_name: Name of the MCP tool
            result: The result data
            
        Returns:
            True if this view can handle the tool/result combination
        """
        return tool_name == "search_jira_issues" and isinstance(result, str)
    
    def render(self, event: Any, result: Any) -> None:
        """
        Render the JIRA search results in a specialized format.
        
        Args:
            event: The parsed event containing tool information
            result: The result string from the JIRA search tool
        """
        # Parse the result string to extract structured data
        search_data = self._parse_search_result(result)
        if not search_data:
            self._show_error("Failed to parse JIRA search results")
            return
        
        # Render search summary
        self._render_search_summary(len(search_data))
        
        # Render results table
        self._render_results_table(search_data)
    
    def _parse_search_result(self, result: str) -> Optional[List[Dict[str, Any]]]:
        """
        Parse the search result string to extract structured data.
        
        Args:
            result: The result string from the JIRA search tool
            
        Returns:
            List of dictionaries containing parsed issue data or None if parsing fails
        """
        try:
            # Look for the list part in the result string
            # The result format is typically: "JIRA Search Results (X issues): [...]"
            if "JIRA Search Results" in result:
                # Extract the list part
                list_start = result.find('[')
                list_end = result.rfind(']') + 1
                if list_start != -1 and list_end != -1:
                    list_str = result[list_start:list_end]
                    
                    # Convert string representation to actual list
                    import ast
                    return ast.literal_eval(list_str)
            
            return None
        except Exception as e:
            self._show_error(f"Failed to parse search results: {str(e)}")
            return None
    
    def _render_search_summary(self, result_count: int) -> None:
        """Render a summary of the search results."""
        summary_text = f"Found [bold green]{result_count}[/bold green] issue(s)"
        
        summary_panel = Panel(
            summary_text,
            title="[bold cyan]Search Results Summary[/bold cyan]",
            border_style="blue",
            box=ROUNDED,
            padding=(0, 1)
        )
        self.console.print(summary_panel)
        self.console.print()
    
    def _render_results_table(self, issues: List[Dict[str, Any]]) -> None:
        """Render the search results in a clean table format."""
        if not issues:
            self.console.print("[yellow]No issues found[/yellow]")
            return
        
        # Prepare table data with key fields
        table_data = []
        for issue in issues:
            # Extract key fields and format them
            table_data.append({
                'Key': issue.get('key', ''),
                'Summary': self._truncate_text(issue.get('summary', ''), 60),
                'Status': issue.get('status', ''),
                'Priority': issue.get('priority', ''),
                'Assignee': issue.get('assignee', 'Unassigned'),
                'Project': issue.get('project', ''),
                'Updated': self._format_date(issue.get('updated', ''))
            })
        
        # Create and display the table
        table = self.table_reporter.create_table(table_data, title="JIRA Issues")
        
        # Wrap table in a bordered panel
        results_panel = Panel(
            table,
            title="[bold cyan]Search Results[/bold cyan]",
            border_style="green",
            box=ROUNDED,
            padding=(0, 1)
        )
        self.console.print(results_panel)
        
        # Show additional details if there are many results
        if len(issues) > 10:
            self.console.print(f"\n[dim]Showing first 10 results. Total: {len(issues)} issues[/dim]")
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to specified length with ellipsis."""
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length-3] + "..."
    
    def _format_date(self, date_str: str) -> str:
        """Format date string for display."""
        if not date_str or date_str == 'Unknown':
            return 'Unknown'
        
        try:
            # Parse ISO format date and format it nicely
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            # If parsing fails, return as is
            return date_str

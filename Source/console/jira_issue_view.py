"""
Specialized view for displaying JIRA issue details.

This view formats JIRA issue information in a clean, readable format
with proper sections for metadata, description, and related information.
"""

import re
from typing import Any, Dict, Optional
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.box import ROUNDED
from .base_view import BaseView
from .table_reporter import TableReporter


class JiraIssueView(BaseView):
    """Specialized view for JIRA issue details."""
    
    def can_handle(self, tool_name: str, result: Any) -> bool:
        """
        Check if this view can handle JIRA issue results.
        
        Args:
            tool_name: Name of the MCP tool
            result: The result data
            
        Returns:
            True if this view can handle the tool/result combination
        """
        return tool_name == "get_jira_issue" and isinstance(result, str)
    
    def render(self, event: Any, result: Any) -> None:
        """
        Render the JIRA issue in a specialized format.
        
        Args:
            event: The parsed event containing tool information
            result: The result string from the JIRA tool
        """
        # Parse the result string to extract structured data
        issue_data = self._parse_jira_result(result)
        if not issue_data:
            self._show_error("Failed to parse JIRA issue data")
            return
        
        # Render issue header with border
        self._render_issue_header(issue_data)
        
        # Render metadata section with border
        self._render_metadata_section(issue_data)
        
        # Render description with border
        self._render_description_section(issue_data)
    
    def _parse_jira_result(self, result: str) -> Optional[Dict[str, Any]]:
        """
        Parse the JIRA result string to extract structured data.
        
        Args:
            result: The result string from the JIRA tool
            
        Returns:
            Dictionary containing parsed issue data or None if parsing fails
        """
        try:
            # Look for the dictionary part in the result string
            # The result format is typically: "JIRA Issue Details:\n{...}"
            if "JIRA Issue Details:" in result:
                # Extract the dictionary part
                dict_start = result.find('{')
                dict_end = result.rfind('}') + 1
                if dict_start != -1 and dict_end != -1:
                    dict_str = result[dict_start:dict_end]
                    
                    # Convert string representation to actual dict
                    # Handle the string formatting (quotes, etc.)
                    import ast
                    return ast.literal_eval(dict_str)
            
            return None
        except Exception as e:
            self._show_error(f"Failed to parse JIRA result: {str(e)}")
            return None
    
    def _render_issue_header(self, issue_data: Dict[str, Any]) -> None:
        """Render the main issue header with key, summary, and status."""
        # Issue key and summary
        key = issue_data.get('key', 'Unknown')
        summary = issue_data.get('summary', 'No Summary')
        header_content = f"[bold blue]{key}[/bold blue] - {summary}"
        
        # Status badge
        status = issue_data.get('status', 'Unknown')
        status_color = self._get_status_color(status)
        status_line = f"Status: [{status_color}]{status}[/{status_color}]"
        
        # Combine header and status in a bordered panel
        full_header = f"{header_content}\n{status_line}"
        header_panel = Panel(
            full_header,
            title="[bold cyan]Issue Information[/bold cyan]",
            border_style="blue",
            box=ROUNDED,
            padding=(0, 1)
        )
        self.console.print(header_panel)
        self.console.print()
    
    def _render_metadata_section(self, issue_data: Dict[str, Any]) -> None:
        """Render issue metadata in a clean table format with border."""
        metadata = {
            'Project': issue_data.get('project', 'Unknown'),
            'Priority': issue_data.get('priority', 'Unknown'),
            'Assignee': issue_data.get('assignee', 'Unassigned'),
            'Reporter': issue_data.get('reporter', 'Unknown'),
            'Created': self._format_date(issue_data.get('created')),
            'Updated': self._format_date(issue_data.get('updated'))
        }
        
        # Create metadata table
        table_data = [{"Field": k, "Value": v} for k, v in metadata.items()]
        table = self.table_reporter.create_table(table_data, title="Issue Details")
        
        # Wrap table in a bordered panel
        metadata_panel = Panel(
            table,
            title="[bold cyan]Issue Details[/bold cyan]",
            border_style="cyan",
            box=ROUNDED,
            padding=(0, 1)
        )
        self.console.print(metadata_panel)
        self.console.print()
    
    def _render_description_section(self, issue_data: Dict[str, Any]) -> None:
        """Render the issue description with proper formatting and border."""
        description = issue_data.get('description', 'No description available')
        if description and description != 'No description':
            # Format the description text
            formatted_desc = self._format_description(description)
            
            # Wrap description in a bordered panel
            description_panel = Panel(
                formatted_desc,
                title="[bold cyan]Description[/bold cyan]",
                border_style="green",
                box=ROUNDED,
                padding=(0, 1)
            )
            self.console.print(description_panel)
            self.console.print()
    
    def _get_status_color(self, status: str) -> str:
        """Get appropriate color for status."""
        status_lower = status.lower()
        if 'done' in status_lower or 'closed' in status_lower:
            return 'green'
        elif 'in progress' in status_lower:
            return 'yellow'
        elif 'obsolete' in status_lower or 'cancelled' in status_lower:
            return 'red'
        else:
            return 'blue'
    
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
    
    def _format_description(self, description: str) -> str:
        """Format description text for better readability."""
        if not description:
            return description
        
        # Handle common markdown-like formatting
        # Convert \r\n to \n for consistent line breaks
        formatted = description.replace('\r\n', '\n')
        
        # Handle bullet points and numbered lists
        formatted = re.sub(r'^(\s*)[*•]\s+', r'\1• ', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^(\s*)(\d+)\.\s+', r'\1\2. ', formatted, flags=re.MULTILINE)
        
        # Handle headers (lines starting with #)
        formatted = re.sub(r'^(\s*)#\s+(.+)$', r'\1[bold]\2[/bold]', formatted, flags=re.MULTILINE)
        formatted = re.sub(r'^(\s*)##\s+(.+)$', r'\1[bold cyan]\2[/bold cyan]', formatted, flags=re.MULTILINE)
        
        return formatted 
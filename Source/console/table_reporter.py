"""
Table reporter for console UI.

Generates clean, bordered tables for dynamic data display.
"""

from typing import List, Dict, Any, Optional, Union
from rich.console import Console
from rich.table import Table
from rich.text import Text


class TableReporter:
    """Generates clean, bordered tables for console output."""
    
    def __init__(self, console: Console):
        self.console = console
    
    def create_table(
        self,
        data: List[Dict[str, Any]],
        title: Optional[str] = None,
        max_column_width: int = 50
    ) -> Table:
        """
        Create a table from a list of dictionaries.
        
        Args:
            data: List of dictionaries where keys are column names
            title: Optional table title
            max_column_width: Maximum width for any column
            
        Returns:
            Rich Table object ready for display
        """
        if not data:
            # Create empty table with default columns
            table = Table(title=title or "No Data")
            table.add_column("No data available", style="dim")
            return table
        
        # Get column names from first data item
        columns = list(data[0].keys())
        
        # Create table
        table = Table(title=title, show_header=True, header_style="bold cyan")
        
        # Add columns with appropriate styling
        for column in columns:
            # Determine column style based on content type
            style = self._get_column_style(column)
            table.add_column(
                column,
                style=style,
                max_width=max_column_width,
                overflow="fold"
            )
        
        # Add data rows
        for row_data in data:
            row_values = []
            for column in columns:
                value = row_data.get(column, "")
                # Convert value to string and handle None/empty
                if value is None:
                    value = ""
                elif isinstance(value, (dict, list)):
                    value = str(value)[:max_column_width]
                else:
                    value = str(value)
                
                row_values.append(value)
            
            table.add_row(*row_values)
        
        return table
    
    def create_simple_table(
        self,
        headers: List[str],
        rows: List[List[Any]],
        title: Optional[str] = None,
        max_column_width: int = 50
    ) -> Table:
        """
        Create a table from headers and row data.
        
        Args:
            headers: List of column headers
            rows: List of row data (each row is a list of values)
            title: Optional table title
            max_column_width: Maximum width for any column
            
        Returns:
            Rich Table object ready for display
        """
        table = Table(title=title, show_header=True, header_style="bold cyan")
        
        # Add columns
        for header in headers:
            style = self._get_column_style(header)
            table.add_column(
                header,
                style=style,
                max_column_width=max_column_width,
                overflow="fold"
            )
        
        # Add rows
        for row in rows:
            # Convert all values to strings
            row_values = [str(value) if value is not None else "" for value in row]
            table.add_row(*row_values)
        
        return table
    
    def display_table(
        self,
        data: Union[List[Dict[str, Any]], Table],
        title: Optional[str] = None,
        max_column_width: int = 50
    ) -> None:
        """
        Display a table in the console.
        
        Args:
            data: Either a list of dictionaries or a pre-built Table
            title: Optional table title (only used if data is list of dicts)
            max_column_width: Maximum column width (only used if data is list of dicts)
        """
        if isinstance(data, Table):
            table = data
        else:
            table = self.create_table(data, title, max_column_width)
        
        self.console.print(table)
    
    def _get_column_style(self, column_name: str) -> str:
        """Get appropriate styling for a column based on its name."""
        column_lower = column_name.lower()
        
        # Status columns
        if 'status' in column_lower:
            return "green"
        elif 'error' in column_lower or 'fail' in column_lower:
            return "red"
        elif 'warning' in column_lower:
            return "yellow"
        
        # ID/Key columns
        elif any(key in column_lower for key in ['id', 'key', 'code']):
            return "cyan"
        
        # Date/Time columns
        elif any(time_key in column_lower for time_key in ['date', 'time', 'created', 'updated']):
            return "magenta"
        
        # Priority columns
        elif 'priority' in column_lower:
            return "bold"
        
        # Default style
        return "white"
    
    def create_summary_table(
        self,
        summary_data: Dict[str, Any],
        title: str = "Summary"
    ) -> Table:
        """
        Create a summary table from key-value pairs.
        
        Args:
            summary_data: Dictionary of summary information
            title: Table title
            
        Returns:
            Rich Table object
        """
        table = Table(title=title, show_header=False, box=None)
        
        for key, value in summary_data.items():
            # Format the key (make it title case)
            formatted_key = key.replace('_', ' ').title()
            formatted_value = str(value) if value is not None else ""
            
            table.add_row(
                f"[bold cyan]{formatted_key}:[/bold cyan]",
                formatted_value
            )
        
        return table 
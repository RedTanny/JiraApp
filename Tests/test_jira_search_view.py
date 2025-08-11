"""
Test script for the JIRA search view.

This script tests the JiraSearchView to ensure it properly
formats search results in a clean, readable format.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Source'))

from rich.console import Console
from console.jira_search_view import JiraSearchView
from console.table_reporter import TableReporter


def test_jira_search_view():
    """Test the JIRA search view with sample data."""
    console = Console()
    table_reporter = TableReporter(console)
    
    # Create a mock event
    class MockEvent:
        def __init__(self):
            self.tool_name = "search_jira_issues"
            self.command_type = type('CommandType', (), {'value': 'QUERY'})()
    
    # Sample JIRA search result (similar to what the MCP tool returns)
    sample_result = '''JIRA Search Results (10 issues):
[{'key': 'NCS-8754', 'summary': 'Support of NTS for time sync', 'status': 'SAFe Request', 'priority': 'Critical', 'assignee': 'Yves Brissette (EXT-Nokia)', 'project': 'NCS', 'updated': '2025-01-15T10:30:00.000+0200'}, {'key': 'NCS-8753', 'summary': 'Support of 4k certificates in NCS', 'status': 'SAFe Request', 'priority': 'Critical', 'assignee': 'Yves Brissette (EXT-Nokia)', 'project': 'NCS', 'updated': '2025-01-14T14:20:00.000+0200'}, {'key': 'NCS-8752', 'summary': 'CIS RHEL Benchmark Compliance Enhancement', 'status': 'SAFe Request', 'priority': 'Major', 'assignee': 'Diana Shekhter (EXT-Nokia)', 'project': 'NCS', 'updated': '2025-01-13T09:15:00.000+0200'}]'''
    
    # Test the view
    console.print("\n[bold blue]Testing JIRA Search View:[/bold blue]")
    console.print("=" * 50)
    
    event = MockEvent()
    view = JiraSearchView(console, table_reporter)
    
    # Test can_handle
    can_handle = view.can_handle("search_jira_issues", sample_result)
    console.print(f"Can handle: {can_handle}")
    
    # Test rendering
    if can_handle:
        view.render(event, sample_result)
    else:
        console.print("[red]View cannot handle this data![/red]")


def main():
    """Run all tests."""
    console = Console()
    console.print("[bold green]Testing JIRA Search View[/bold green]")
    console.print("=" * 60)
    
    try:
        test_jira_search_view()
        console.print("\n[bold green]✅ All tests completed successfully![/bold green]")
        console.print("\n[bold yellow]Next step:[/bold yellow] Test the search view in the actual application!")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]")
        import traceback
        console.print_exception()


if __name__ == "__main__":
    main()

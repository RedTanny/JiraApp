"""
Test script for the specialized view system.

This script tests the view system components including the ViewManager,
JiraIssueView, and GenericView to ensure they work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Source'))

from rich.console import Console
from console.view_manager import ViewManager
from console.jira_issue_view import JiraIssueView
from console.generic_view import GenericView
from console.table_reporter import TableReporter


def test_jira_issue_view():
    """Test the JIRA issue view with sample data."""
    console = Console()
    table_reporter = TableReporter(console)
    
    # Create a mock event
    class MockEvent:
        def __init__(self):
            self.tool_name = "get_jira_issue"
            self.command_type = type('CommandType', (), {'value': 'QUERY'})()
    
    # Sample JIRA issue result (similar to what the MCP tool returns)
    sample_result = '''JIRA Issue Details:
{'key': 'NCS-8540', 'summary': 'Poc Scalling Ceph MDS', 'status': 'SAFE OBSOLETE', 'project': 'NCS', 'priority': 'Unknown', 'assignee': 'Yael Azulay (EXT-Nokia)', 'reporter': 'Shimon Tanny (EXT-Nokia)', 'created': '2025-02-10T10:13:03.096+0200', 'updated': '2025-07-14T12:14:07.000+0300', 'description': '# Feature summary overview\\n\\nPoc to check if by scaling MDS can it help solve cases with high pressure files on cephFS like issue\\n\\nThe idea is to add 2 active MDS and 3 passive , note default configuration stays the same 3 MDS .'}'''
    
    # Test the view
    console.print("\n[bold blue]Testing JIRA Issue View:[/bold blue]")
    console.print("=" * 50)
    
    event = MockEvent()
    view = JiraIssueView(console, table_reporter)
    
    # Test can_handle
    can_handle = view.can_handle("get_jira_issue", sample_result)
    console.print(f"Can handle: {can_handle}")
    
    # Test rendering
    if can_handle:
        view.render(event, sample_result)
    else:
        console.print("[red]View cannot handle this data![/red]")


def test_view_manager():
    """Test the ViewManager with different tool types."""
    console = Console()
    table_reporter = TableReporter(console)
    
    # Create view manager
    view_manager = ViewManager(console, table_reporter)
    
    # Test with JIRA issue
    class MockJiraEvent:
        def __init__(self):
            self.tool_name = "get_jira_issue"
            self.command_type = type('CommandType', (), {'value': 'QUERY'})()
    
    # Test with unknown tool
    class MockUnknownEvent:
        def __init__(self):
            self.tool_name = "unknown_tool"
            self.command_type = type('CommandType', (), {'value': 'QUERY'})()
    
    jira_result = '''JIRA Issue Details:
{'key': 'TEST-123', 'summary': 'Test Issue', 'status': 'Open'}'''
    
    unknown_result = {'data': 'some data'}
    
    console.print("\n[bold blue]Testing View Manager:[/bold blue]")
    console.print("=" * 50)
    
    # Test JIRA issue routing
    console.print("\n[bold]Testing JIRA issue routing:[/bold]")
    view_manager.render_event(MockJiraEvent(), jira_result)
    
    # Test unknown tool routing (should use generic view)
    console.print("\n[bold]Testing unknown tool routing (should use generic view):[/bold]")
    view_manager.render_event(MockUnknownEvent(), unknown_result)
    
    # Show registered views
    console.print(f"\n[bold]Registered views:[/bold] {view_manager.get_registered_views()}")


def main():
    """Run all tests."""
    console = Console()
    console.print("[bold green]Testing Specialized View System[/bold green]")
    console.print("=" * 60)
    
    try:
        test_jira_issue_view()
        test_view_manager()
        console.print("\n[bold green]✅ All tests completed successfully![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]")
        import traceback
        console.print_exception()


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Demo script for Console UI components.

This script demonstrates the console UI functionality without requiring
the full orchestrator or MCP layer.
"""

import sys
from pathlib import Path

# Add the Source directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "Source"))

from console.console_ui import ConsoleUI
from console.table_reporter import TableReporter
from console.status_indicator import StatusIndicator


def demo_status_indicator():
    """Demonstrate the status indicator functionality."""
    print("\n=== Status Indicator Demo ===")
    
    from rich.console import Console
    console = Console()
    status = StatusIndicator(console)
    
    # Simulate a processing operation
    status.start_operation("Processing data...", "processing")
    import time
    time.sleep(1)
    
    status.update_status("Updating records...", "updating")
    time.sleep(1)
    
    status.update_status("Finalizing...", "processing")
    time.sleep(0.5)
    
    duration = status.complete_operation("Data processing completed")
    print(f"Operation took {duration:.1f} seconds")
    
    # Show some info messages
    status.show_info("System is ready", "success")
    status.show_error("Connection timeout")


def demo_table_reporter():
    """Demonstrate the table reporter functionality."""
    print("\n=== Table Reporter Demo ===")
    
    from rich.console import Console
    console = Console()
    reporter = TableReporter(console)
    
    # Sample JIRA-like data
    jira_data = [
        {
            "Key": "PROJ-123",
            "Summary": "Fix login bug",
            "Status": "Open",
            "Assignee": "john.doe",
            "Priority": "High"
        },
        {
            "Key": "PROJ-124", 
            "Summary": "Update documentation",
            "Status": "In Progress",
            "Assignee": "jane.smith",
            "Priority": "Medium"
        },
        {
            "Key": "PROJ-125",
            "Summary": "Add new feature",
            "Status": "To Do",
            "Assignee": "bob.wilson",
            "Priority": "Low"
        }
    ]
    
    # Display the table
    reporter.display_table(jira_data, title="Sample JIRA Tickets")
    
    # Create a summary table
    summary_data = {
        "Total Tickets": 3,
        "Open Tickets": 1,
        "In Progress": 1,
        "To Do": 1,
        "High Priority": 1
    }
    
    summary_table = reporter.create_summary_table(summary_data, title="Project Summary")
    console.print(summary_table)


def demo_console_ui():
    """Demonstrate the console UI functionality."""
    print("\n=== Console UI Demo ===")
    
    # Create console UI without orchestrator
    console_ui = ConsoleUI(orchestrator=None)
    
    # Test built-in commands
    print("\nTesting built-in commands:")
    
    # Test help command
    console_ui._handle_builtin_command("/help")
    
    # Test status command
    console_ui._handle_builtin_command("/status")
    
    # Test unknown command
    console_ui._handle_builtin_command("/unknown")
    
    # Test natural language (should show error since no orchestrator)
    console_ui._handle_natural_language_request("Find all open tickets")


def main():
    """Run all demos."""
    print("MCP JIRA Console UI Demo")
    print("=" * 40)
    
    try:
        demo_status_indicator()
        demo_table_reporter()
        demo_console_ui()
        
        print("\n=== Demo Completed Successfully ===")
        print("All console UI components are working correctly!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 
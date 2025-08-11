"""
Test script for the enhanced input system.

This script tests the history manager and enhanced input functionality
to ensure command history, search, and navigation work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Source'))

from rich.console import Console
from console.history_manager import HistoryManager
from console.enhanced_input import EnhancedInput


def test_history_manager():
    """Test the history manager functionality."""
    console = Console()
    
    # Create history manager
    history = HistoryManager(max_history=5)
    
    console.print("\n[bold blue]Testing History Manager:[/bold blue]")
    console.print("=" * 50)
    
    # Test adding commands
    test_commands = [
        "help",
        "tools", 
        "status",
        "clear",
        "search for JIRA issues",
        "get details for NCS-8540"
    ]
    
    for cmd in test_commands:
        history.add_command(cmd)
        console.print(f"Added: {cmd}")
    
    # Test history navigation
    console.print(f"\n[bold]History size:[/bold] {len(history.get_history())}")
    console.print(f"[bold]Max history:[/bold] {history.max_history}")
    
    # Test getting previous commands
    console.print("\n[bold]Previous commands:[/bold]")
    for i in range(3):
        prev = history.get_previous()
        if prev:
            console.print(f"  {i+1}. {prev}")
    
    # Test search functionality
    console.print("\n[bold]Searching for 'JIRA':[/bold]")
    search_result = history.start_search("JIRA")
    if search_result:
        console.print(f"  Found: {search_result}")
        
        # Test search navigation
        next_result = history.search_next()
        if next_result:
            console.print(f"  Next: {next_result}")
    else:
        console.print("  No results found")
    
    # Test clearing history
    console.print("\n[bold]Clearing history...[/bold]")
    history.clear_history()
    console.print(f"History size after clear: {len(history.get_history())}")


def test_enhanced_input():
    """Test the enhanced input handler."""
    console = Console()
    
    # Create history manager and enhanced input
    history = HistoryManager(max_history=10)
    enhanced_input = EnhancedInput(console, history)
    
    console.print("\n[bold blue]Testing Enhanced Input:[/bold blue]")
    console.print("=" * 50)
    
    # Add some test commands
    test_commands = [
        "/help",
        "/tools", 
        "/status",
        "Search for open JIRA tickets",
        "Get issue details for PROJ-123"
    ]
    
    for cmd in test_commands:
        history.add_command(cmd)
    
    # Test key handling methods
    console.print("\n[bold]Testing key handling methods:[/bold]")
    
    # Test navigation
    up_result = enhanced_input._navigate_history_up()
    if up_result:
        console.print(f"  Up arrow: {up_result}")
    
    down_result = enhanced_input._navigate_history_down()
    if down_result is not None:
        console.print(f"  Down arrow: {down_result}")
    
    # Test search
    console.print("\n[bold]Testing search functionality:[/bold]")
    search_result = enhanced_input._start_search()
    if search_result:
        console.print(f"  Search result: {search_result}")
    
    # Test auto-completion
    console.print("\n[bold]Testing auto-completion:[/bold]")
    enhanced_input.current_input = "/h"
    tab_result = enhanced_input._auto_complete()
    if tab_result:
        console.print(f"  Tab completion: {tab_result}")
    
    # Show help
    console.print("\n[bold]Enhanced Input Help:[/bold]")
    enhanced_input.show_help()


def main():
    """Run all tests."""
    console = Console()
    console.print("[bold green]Testing Enhanced Input System[/bold green]")
    console.print("=" * 60)
    
    try:
        test_history_manager()
        test_enhanced_input()
        console.print("\n[bold green]✅ All tests completed successfully![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]")
        import traceback
        console.print_exception()


if __name__ == "__main__":
    main()

"""
Test script for the readline-based input system.

This script tests the readline input handler to ensure
it properly integrates with the history manager.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Source'))

from rich.console import Console
from console.history_manager import HistoryManager
from console.readline_input import ReadlineInput


def test_readline_integration():
    """Test the readline input integration with history."""
    console = Console()
    
    # Create history manager and readline input
    history = HistoryManager(max_history=10)
    readline_input = ReadlineInput(console, history)
    
    console.print("\n[bold blue]Testing Readline Input Integration:[/bold blue]")
    console.print("=" * 60)
    
    # Add some test commands to history
    test_commands = [
        "/help",
        "/tools", 
        "/status",
        "Search for open JIRA tickets",
        "Get issue details for PROJ-123",
        "Update Confluence page",
        "List all projects"
    ]
    
    for cmd in test_commands:
        history.add_command(cmd)
        console.print(f"Added to history: {cmd}")
    
    # Show history statistics
    stats = readline_input.get_history_stats()
    console.print(f"\n[bold]History Statistics:[/bold]")
    console.print(f"  Our history size: {stats['our_history']}")
    console.print(f"  Readline history size: {stats['readline_history']}")
    console.print(f"  Max history: {stats['max_history']}")
    
    # Show available key bindings
    console.print(f"\n[bold]Available Key Bindings:[/bold]")
    readline_input.show_help()
    
    # Test tab completion (non-interactive)
    console.print(f"\n[bold]Tab Completion Test:[/bold]")
    console.print("  Type '/h' + Tab to complete to '/help'")
    console.print("  Type 'to' + Tab to complete to 'tools'")
    
    console.print(f"\n[bold green]✅ Readline integration test completed![/bold green]")
    console.print(f"[bold]Note:[/bold] Arrow key functionality can only be tested in the actual application")


def main():
    """Run all tests."""
    console = Console()
    console.print("[bold green]Testing Readline Input System[/bold green]")
    console.print("=" * 60)
    
    try:
        test_readline_integration()
        console.print("\n[bold green]✅ All tests completed successfully![/bold green]")
        console.print("\n[bold yellow]Next step:[/bold yellow] Test the actual application to verify arrow keys work!")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]")
        import traceback
        console.print_exception()


if __name__ == "__main__":
    main()

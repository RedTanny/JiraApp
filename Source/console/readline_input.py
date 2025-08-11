"""
Readline-based input handler with proper keyboard support.

Provides working arrow keys, history navigation, and search
capabilities using the readline library.
"""

import readline
import os
import sys
from typing import Optional, List
from rich.console import Console
from .history_manager import HistoryManager


class ReadlineInput:
    """Readline-based input handler with history and search support."""
    
    def __init__(self, console: Console, history_manager: HistoryManager):
        self.console = console
        self.history = history_manager
        self._setup_readline()
    
    def _setup_readline(self) -> None:
        """Setup readline with custom completers and history."""
        # Set up readline to use our history
        readline.set_history_length(self.history.max_history)
        
        # Set up tab completion
        readline.set_completer(self._completer)
        readline.parse_and_bind('tab: complete')
        
        # Set up custom key bindings
        self._setup_key_bindings()
        
        # Load existing history into readline
        self._load_history_to_readline()
    
    def _setup_key_bindings(self) -> None:
        """Setup custom key bindings for enhanced functionality."""
        # Note: These bindings may vary by platform
        try:
            # Ctrl+R for reverse search (if supported)
            readline.parse_and_bind('\\C-r: reverse-search-history')
            
            # Ctrl+G to cancel search
            readline.parse_and_bind('\\C-g: abort')
            
            # Ctrl+U to clear line
            readline.parse_and_bind('\\C-u: unix-line-discard')
            
            # Ctrl+W to delete word
            readline.parse_and_bind('\\C-w: unix-word-rubout')
            
            # Ctrl+L to clear screen
            readline.parse_and_bind('\\C-l: clear-screen')
            
        except Exception:
            # Some bindings may not be supported on all platforms
            pass
    
    def _completer(self, text: str, state: int) -> Optional[str]:
        """
        Tab completion for commands and common inputs.
        
        Args:
            text: The text to complete
            state: Completion state (0 = first call, 1 = second call, etc.)
            
        Returns:
            Completion suggestion or None if no more
        """
        commands = [
            '/help', '/tools', '/status', '/clear', '/quit', '/keys',
            'help', 'tools', 'status', 'clear', 'quit', 'keys'
        ]
        
        # Filter commands that start with the input text
        matches = [cmd for cmd in commands if cmd.startswith(text)]
        
        # Return the appropriate match based on state
        if state < len(matches):
            return matches[state]
        else:
            return None
    
    def _load_history_to_readline(self) -> None:
        """Load our history into readline's history."""
        for command in self.history.get_history():
            readline.add_history(command)
    
    def get_input(self, prompt: str = "") -> str:
        """
        Get user input with full readline support.
        
        Args:
            prompt: The prompt to display
            
        Returns:
            User input string
        """
        try:
            # Get input using readline
            user_input = input(prompt)
            
            # Add to our history manager
            if user_input.strip():
                self.history.add_command(user_input.strip())
                # Also add to readline history
                readline.add_history(user_input.strip())
            
            return user_input
            
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+D and Ctrl+C gracefully
            raise
    
    def show_help(self) -> None:
        """Show help for available key bindings."""
        help_text = """
[bold cyan]Readline Input Key Bindings:[/bold cyan]

[bold]Navigation:[/bold]
  ↑/↓          Navigate command history (working!)
  Ctrl+P/N     Previous/Next command (alternative to arrows)
  Home/End     Jump to start/end of line
  Ctrl+←/→     Jump between words
  
[bold]History Search:[/bold]
  Ctrl+R       Start reverse search through history
  Ctrl+S       Forward search through history
  Ctrl+G       Cancel current search
  
[bold]Line Editing:[/bold]
  Ctrl+U       Clear current line
  Ctrl+W       Delete word before cursor
  Ctrl+K       Delete from cursor to end of line
  Tab          Auto-complete commands
  
[bold]Other:[/bold]
  Ctrl+L       Clear screen
  Ctrl+C       Interrupt current operation
  Ctrl+D       End of input (exit)
  
[bold]Commands:[/bold]
  /help        Show this help
  /tools       List available tools
  /status      Show system status
  /clear       Clear screen
  /quit        Exit application
  /keys        Show this key bindings help
        """
        self.console.print(help_text)
    
    def get_history_stats(self) -> dict:
        """Get statistics about the history."""
        readline_history_size = readline.get_current_history_length()
        our_history_size = len(self.history.get_history())
        
        return {
            'readline_history': readline_history_size,
            'our_history': our_history_size,
            'max_history': self.history.max_history
        }

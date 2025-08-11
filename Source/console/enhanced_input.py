"""
Enhanced input handler with history navigation and search.

Provides a rich command line input experience with history,
search, and basic navigation capabilities.
"""

import sys
from typing import Optional, Callable
from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text
from .history_manager import HistoryManager


class EnhancedInput:
    """Enhanced input handler with history and search capabilities."""
    
    def __init__(self, console: Console, history_manager: HistoryManager):
        self.console = console
        self.history = history_manager
        self.current_input = ""
        self.cursor_position = 0
        self.search_mode = False
        self.search_prompt = ""
    
    def get_input(self, prompt: str = "") -> str:
        """
        Get user input with enhanced features.
        
        Args:
            prompt: The prompt to display
            
        Returns:
            User input string
        """
        # For now, use Rich's built-in input which provides basic history
        # We'll enhance this with custom key handling in the next iteration
        user_input = Prompt.ask(prompt)
        
        # Add to history
        if user_input.strip():
            self.history.add_command(user_input.strip())
        
        return user_input
    
    def get_input_with_history(self, prompt: str = "") -> str:
        """
        Get user input with full history support.
        
        This is a placeholder for the enhanced version that will handle
        custom key bindings. For now, it uses the basic input method.
        
        Args:
            prompt: The prompt to display
            
        Returns:
            User input string
        """
        return self.get_input(prompt)
    
    def _handle_key(self, key: str) -> Optional[str]:
        """
        Handle special key presses.
        
        Args:
            key: The key that was pressed
            
        Returns:
            Modified input or None if no change
        """
        if key == "up":
            return self._navigate_history_up()
        elif key == "down":
            return self._navigate_history_down()
        elif key == "ctrl+r":
            return self._start_search()
        elif key == "ctrl+g":
            return self._cancel_search()
        elif key == "home":
            return self._go_to_start()
        elif key == "end":
            return self._go_to_end()
        elif key == "ctrl+left":
            return self._jump_word_left()
        elif key == "ctrl+right":
            return self._jump_word_right()
        elif key == "ctrl+u":
            return self._clear_line()
        elif key == "tab":
            return self._auto_complete()
        
        return None
    
    def _navigate_history_up(self) -> Optional[str]:
        """Navigate to previous command in history."""
        if self.search_mode:
            result = self.history.search_previous()
        else:
            result = self.history.get_previous()
        
        if result is not None:
            self.current_input = result
            self.cursor_position = len(result)
            return result
        return None
    
    def _navigate_history_down(self) -> Optional[str]:
        """Navigate to next command in history."""
        if self.search_mode:
            result = self.history.search_next()
        else:
            result = self.history.get_next()
        
        if result is not None:
            self.current_input = result
            self.cursor_position = len(result)
            return result
        else:
            # Clear input when reaching end of history
            self.current_input = ""
            self.cursor_position = 0
            return ""
    
    def _start_search(self) -> Optional[str]:
        """Start reverse search through history."""
        # Show search prompt
        search_query = Prompt.ask("[bold cyan]Search history[/bold cyan]")
        if search_query:
            result = self.history.start_search(search_query)
            if result:
                self.current_input = result
                self.cursor_position = len(result)
                return result
            else:
                self.console.print("[yellow]No matches found[/yellow]")
        return None
    
    def _cancel_search(self) -> Optional[str]:
        """Cancel current search."""
        self.history.cancel_search()
        return None
    
    def _go_to_start(self) -> Optional[str]:
        """Move cursor to start of line."""
        self.cursor_position = 0
        return None
    
    def _go_to_end(self) -> Optional[str]:
        """Move cursor to end of line."""
        self.cursor_position = len(self.current_input)
        return None
    
    def _jump_word_left(self) -> Optional[str]:
        """Jump to previous word."""
        # Simple word boundary detection
        text = self.current_input[:self.cursor_position]
        words = text.split()
        if len(words) > 1:
            # Find position of previous word
            prev_word_end = text.rfind(words[-2]) + len(words[-2])
            self.cursor_position = prev_word_end
        else:
            self.cursor_position = 0
        return None
    
    def _jump_word_right(self) -> Optional[str]:
        """Jump to next word."""
        # Simple word boundary detection
        text = self.current_input[self.cursor_position:]
        if text.strip():
            words = text.split()
            if words:
                # Find position of next word
                next_word_start = text.find(words[0])
                self.cursor_position += next_word_start
        else:
            self.cursor_position = len(self.current_input)
        return None
    
    def _clear_line(self) -> Optional[str]:
        """Clear current line."""
        self.current_input = ""
        self.cursor_position = 0
        return ""
    
    def _auto_complete(self) -> Optional[str]:
        """Auto-complete command."""
        # Simple auto-completion for built-in commands
        commands = ['help', 'tools', 'status', 'clear', 'quit']
        current = self.current_input.strip()
        
        if current.startswith('/'):
            current = current[1:]  # Remove /
            for cmd in commands:
                if cmd.startswith(current):
                    completed = f"/{cmd}"
                    self.current_input = completed
                    self.cursor_position = len(completed)
                    return completed
        
        return None
    
    def show_help(self) -> None:
        """Show help for available key bindings."""
        help_text = """
[bold cyan]Enhanced Input Key Bindings:[/bold cyan]

[bold]Navigation:[/bold]
  ↑/↓          Navigate command history
  Home/End     Jump to start/end of line
  Ctrl+←/→     Jump between words
  
[bold]History Search:[/bold]
  Ctrl+R       Start reverse search through history
  Ctrl+G       Cancel current search
  
[bold]Line Editing:[/bold]
  Ctrl+U       Clear current line
  Tab          Auto-complete commands
  
[bold]Commands:[/bold]
  /help        Show this help
  /tools       List available tools
  /status      Show system status
  /clear       Clear screen
  /quit        Exit application
        """
        self.console.print(help_text)

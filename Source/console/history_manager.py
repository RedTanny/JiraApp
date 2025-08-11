"""
History manager for console command history.

Provides persistent command history with navigation and search capabilities.
"""

import os
import json
from typing import List, Optional, Tuple
from pathlib import Path


class HistoryManager:
    """Manages command history with persistence and search."""
    
    def __init__(self, max_history: int = 100, history_file: Optional[str] = None):
        """
        Initialize the history manager.
        
        Args:
            max_history: Maximum number of commands to store
            history_file: Path to history file (default: ~/.mcp_jira_history)
        """
        self.max_history = max_history
        self.history: List[str] = []
        self.current_index = -1
        self.search_mode = False
        self.search_query = ""
        self.search_results: List[str] = []
        self.search_index = -1
        
        # Set default history file if none provided
        if history_file is None:
            home_dir = Path.home()
            self.history_file = home_dir / ".mcp_jira_history"
        else:
            self.history_file = Path(history_file)
        
        # Load existing history
        self._load_history()
    
    def add_command(self, command: str) -> None:
        """
        Add a command to history.
        
        Args:
            command: The command to add
        """
        if not command.strip():
            return
        
        # Remove duplicate consecutive commands
        if self.history and self.history[-1] == command:
            return
        
        # Add to history
        self.history.append(command)
        
        # Trim to max size
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Reset navigation index
        self.current_index = -1
        
        # Save to file
        self._save_history()
    
    def get_previous(self) -> Optional[str]:
        """
        Get the previous command in history.
        
        Returns:
            Previous command or None if at beginning
        """
        if not self.history:
            return None
        
        if self.current_index == -1:
            self.current_index = len(self.history) - 1
        elif self.current_index > 0:
            self.current_index -= 1
        else:
            return None
        
        return self.history[self.current_index]
    
    def get_next(self) -> Optional[str]:
        """
        Get the next command in history.
        
        Returns:
            Next command or None if at end
        """
        if not self.history or self.current_index == -1:
            return None
        
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        else:
            self.current_index = -1
            return ""
    
    def start_search(self, query: str) -> Optional[str]:
        """
        Start a reverse search through history.
        
        Args:
            query: Search query string
            
        Returns:
            First matching result or None if no matches
        """
        self.search_mode = True
        self.search_query = query.lower()
        self.search_results = []
        
        # Find all matching commands
        for cmd in reversed(self.history):
            if self.search_query in cmd.lower():
                self.search_results.append(cmd)
        
        if self.search_results:
            self.search_index = 0
            return self.search_results[0]
        else:
            self.search_mode = False
            return None
    
    def search_next(self) -> Optional[str]:
        """
        Get next search result.
        
        Returns:
            Next search result or None if no more
        """
        if not self.search_mode or not self.search_results:
            return None
        
        if self.search_index < len(self.search_results) - 1:
            self.search_index += 1
            return self.search_results[self.search_index]
        else:
            # Wrap around to first result
            self.search_index = 0
            return self.search_results[0]
    
    def search_previous(self) -> Optional[str]:
        """
        Get previous search result.
        
        Returns:
            Previous search result or None if no more
        """
        if not self.search_mode or not self.search_results:
            return None
        
        if self.search_index > 0:
            self.search_index -= 1
            return self.search_results[self.search_index]
        else:
            # Wrap around to last result
            self.search_index = len(self.search_results) - 1
            return self.search_results[self.search_index]
    
    def cancel_search(self) -> None:
        """Cancel current search and exit search mode."""
        self.search_mode = False
        self.search_query = ""
        self.search_results = []
        self.search_index = -1
    
    def get_history(self) -> List[str]:
        """
        Get all history entries.
        
        Returns:
            List of all commands in history
        """
        return self.history.copy()
    
    def clear_history(self) -> None:
        """Clear all history entries."""
        self.history.clear()
        self.current_index = -1
        self._save_history()
    
    def _load_history(self) -> None:
        """Load history from file."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
                    # Ensure we don't exceed max history
                    if len(self.history) > self.max_history:
                        self.history = self.history[-self.max_history:]
        except Exception:
            # If loading fails, start with empty history
            self.history = []
    
    def _save_history(self) -> None:
        """Save history to file."""
        try:
            # Create directory if it doesn't exist
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'history': self.history,
                    'max_history': self.max_history
                }, f, indent=2)
        except Exception:
            # If saving fails, continue with in-memory history
            pass

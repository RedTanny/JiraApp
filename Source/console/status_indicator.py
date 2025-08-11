"""
Status indicator for console UI.

Handles status display, timing, and emoji indicators.
"""

import time
from typing import Optional
from rich.console import Console
from rich.status import Status
from rich.text import Text


class StatusIndicator:
    """Handles status display and timing for console operations."""
    
    def __init__(self, console: Console):
        self.console = console
        self.start_time: Optional[float] = None
        self.current_status: Optional[Status] = None
        
        # Status emoji mapping
        self.status_icons = {
            'processing': '⏳',
            'success': '✅',
            'error': '❌',
            'searching': '🔍',
            'waiting': '⏸️',
            'connecting': '🔌',
            'updating': '📝',
            'querying': '🔎'
        }
    
    def start_operation(self, message: str, status_type: str = 'processing') -> None:
        """Start a new operation with status display."""
        icon = self.status_icons.get(status_type, '⏳')
        status_text = f"{icon} {message}"
        
        self.start_time = time.time()
        self.current_status = self.console.status(
            status_text,
            spinner="dots"
        )
        self.current_status.start()
    
    def update_status(self, message: str, status_type: str = 'processing') -> None:
        """Update the current status message."""
        if self.current_status:
            icon = self.status_icons.get(status_type, '⏳')
            status_text = f"{icon} {message}"
            self.current_status.update(status_text)
    
    def complete_operation(self, message: str = "Completed", status_type: str = 'success') -> float:
        """Complete the current operation and return duration."""
        if self.current_status:
            self.current_status.stop()
            self.current_status = None
        
        duration = 0.0
        if self.start_time:
            duration = time.time() - self.start_time
            self.start_time = None
        
        # Show completion message with timing
        icon = self.status_icons.get(status_type, '✅')
        timing_text = f"[{icon}] {message}"
        if duration > 0:
            timing_text += f" [Completed in {duration:.1f}s]"
        
        self.console.print(timing_text)
        return duration
    
    def show_error(self, message: str) -> None:
        """Show an error message."""
        if self.current_status:
            self.current_status.stop()
            self.current_status = None
        
        if self.start_time:
            self.start_time = None
        
        icon = self.status_icons['error']
        self.console.print(f"[red]{icon} {message}[/red]")
    
    def show_info(self, message: str, status_type: str = 'processing') -> None:
        """Show an informational message."""
        icon = self.status_icons.get(status_type, 'ℹ️')
        self.console.print(f"{icon} {message}")
    
    def show_progress(self, current: int, total: int, message: str = "Progress") -> None:
        """Show progress information."""
        percentage = (current / total) * 100 if total > 0 else 0
        progress_bar = "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
        
        self.console.print(f"⏳ {message}: [{progress_bar}] {percentage:.1f}% ({current}/{total})") 
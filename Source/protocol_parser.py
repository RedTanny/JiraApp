from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class CommandType(Enum):
    """Enum defining the types of commands that can be parsed."""
    QUERY = "QUERY"
    TASK = "TASK"
    ERROR = "ERROR"


@dataclass
class ParsedEvent:
    """Event class containing command type and data."""
    command_type: CommandType
    tool_name: str
    tool_args: List[str]
    raw_command: str
    line_number: int


class FailParser(Exception):
    """Raised when LLM output cannot be parsed according to protocol."""
    pass


class ProtocolParser:
    """Parser for LLM output following the BEGIN/END protocol with structured commands."""
    
    def __init__(self):
        self._command_pattern = re.compile(r'^(\w+)\((.*)\)$', re.MULTILINE)
        self._begin_pattern = re.compile(r'^BEGIN$', re.MULTILINE)
        self._end_pattern = re.compile(r'^END$', re.MULTILINE)
        
    def parse_llm_output(self, llm_output: str) -> List[ParsedEvent]:
        """
        Parse LLM output and extract structured commands.
        
        Args:
            llm_output: Raw text output from the LLM
            
        Returns:
            List of parsed events with command type and data
            
        Raises:
            FailParser: If the LLM output cannot be parsed according to protocol
        """
        if not llm_output or not llm_output.strip():
            raise FailParser("Empty or None LLM output")
            
        events = []
        lines = llm_output.strip().split('\n')
        
        # Find BEGIN and END markers
        begin_line = None
        end_line = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if self._begin_pattern.match(line):
                begin_line = i
            elif self._end_pattern.match(line):
                end_line = i
                break
        
        if begin_line is None:
            raise FailParser("Missing BEGIN marker in LLM output")
            
        if end_line is None:
            raise FailParser("Missing END marker in LLM output")
            
        if begin_line >= end_line:
            raise FailParser("BEGIN marker appears after or at the same line as END marker")
        
        # Parse commands between BEGIN and END
        for i in range(begin_line + 1, end_line):
            line = lines[i].strip()
            if not line:
                continue
                
            event = self._parse_command_line(line, i)
            if event:
                events.append(event)
        
        return events
    
    def _parse_command_line(self, line: str, line_number: int) -> Optional[ParsedEvent]:
        """
        Parse a single command line.
        
        Args:
            line: The command line to parse
            line_number: Line number for error reporting
            
        Returns:
            ParsedEvent if successful, None if parsing failed
        """
        match = self._command_pattern.match(line)
        if not match:
            raise FailParser(f"Invalid command format at line {line_number + 1}: {line}")
            
        command_name = match.group(1).upper()
        command_data = match.group(2).strip()
        
        try:
            command_type = CommandType(command_name)
        except ValueError:
            raise FailParser(f"Unknown command type '{command_name}' at line {line_number + 1}")

        tool_name = command_data.split("(")[0]
        string_args = command_data.split("(")[1].split(")")[0]
        tool_args = string_args.split(",")
        
        return ParsedEvent(
            command_type=command_type,
            tool_name=tool_name,
            tool_args=tool_args,
            raw_command=line,
            line_number=line_number + 1  # Convert to 1-based line numbers for user
        ) 
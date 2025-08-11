#!/usr/bin/env python3
"""
Unit tests for the Protocol Parser module.
"""

import sys
import os
import unittest
from pathlib import Path

# Add the Source directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Source"))

from protocol_parser import (
    ProtocolParser, 
    CommandType, 
    ParsedEvent, 
    FailParser
)


class TestCommandType(unittest.TestCase):
    """Test the CommandType enum."""
    
    def test_command_types(self):
        """Test that all expected command types exist."""
        self.assertEqual(CommandType.QUERY.value, "QUERY")
        self.assertEqual(CommandType.TASK.value, "TASK")
        self.assertEqual(CommandType.ERROR.value, "ERROR")
    
    def test_command_type_count(self):
        """Test that we have exactly 3 command types."""
        self.assertEqual(len(CommandType), 3)


class TestParsedEvent(unittest.TestCase):
    """Test the ParsedEvent dataclass."""
    
    def test_parsed_event_creation(self):
        """Test creating a ParsedEvent instance."""
        event = ParsedEvent(
            command_type=CommandType.QUERY,
            command_data="Find all tickets",
            raw_command="QUERY(Find all tickets)",
            line_number=2
        )
        
        self.assertEqual(event.command_type, CommandType.QUERY)
        self.assertEqual(event.command_data, "Find all tickets")
        self.assertEqual(event.raw_command, "QUERY(Find all tickets)")
        self.assertEqual(event.line_number, 2)


class TestProtocolParser(unittest.TestCase):
    """Test the ProtocolParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = ProtocolParser()
    
    def test_parse_valid_llm_output(self):
        """Test parsing valid LLM output."""
        llm_output = """BEGIN
QUERY(Find all open JIRA tickets)
TASK(Update confluence page)
END"""
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 2)
        
        # Check first event
        self.assertEqual(events[0].command_type, CommandType.QUERY)
        self.assertEqual(events[0].command_data, "Find all open JIRA tickets")
        self.assertEqual(events[0].line_number, 2)
        
        # Check second event
        self.assertEqual(events[1].command_type, CommandType.TASK)
        self.assertEqual(events[1].command_data, "Update confluence page")
        self.assertEqual(events[1].line_number, 3)
    
    def test_parse_empty_commands(self):
        """Test parsing LLM output with empty lines between commands."""
        llm_output = """BEGIN

QUERY(Find tickets)

TASK(Update page)

END"""
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].command_type, CommandType.QUERY)
        self.assertEqual(events[1].command_type, CommandType.TASK)  # Fixed: should be TASK, not ERROR
    
    def test_parse_single_command(self):
        """Test parsing LLM output with a single command."""
        llm_output = """BEGIN
QUERY(Get status)
END"""
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].command_type, CommandType.QUERY)
        self.assertEqual(events[0].command_data, "Get status")
    
    def test_parse_no_commands(self):
        """Test parsing LLM output with no commands."""
        llm_output = """BEGIN
END"""
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 0)
    
    def test_parse_with_whitespace(self):
        """Test parsing LLM output with various whitespace."""
        llm_output = """  BEGIN  
  QUERY(  Find tickets  )  
  TASK(  Update page  )  
  END  """
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].command_data, "Find tickets")
        self.assertEqual(events[1].command_data, "Update page")
    
    def test_parse_error_command(self):
        """Test parsing ERROR command type."""
        llm_output = """BEGIN
ERROR(Connection timeout)
END"""
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].command_type, CommandType.ERROR)
        self.assertEqual(events[0].command_data, "Connection timeout")
    
    def test_parse_case_insensitive_commands(self):
        """Test that command parsing converts to uppercase for enum lookup."""
        llm_output = """BEGIN
query(Find tickets)
TASK(Update page)
END"""
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].command_type, CommandType.QUERY)  # Should convert 'query' to 'QUERY'
        self.assertEqual(events[1].command_type, CommandType.TASK)
    
    def test_parse_empty_llm_output(self):
        """Test parsing empty LLM output."""
        with self.assertRaises(FailParser) as context:
            self.parser.parse_llm_output("")
        
        self.assertIn("Empty or None LLM output", str(context.exception))
    
    def test_parse_none_llm_output(self):
        """Test parsing None LLM output."""
        with self.assertRaises(FailParser) as context:
            self.parser.parse_llm_output(None)
        
        self.assertIn("Empty or None LLM output", str(context.exception))
    
    def test_parse_missing_begin(self):
        """Test parsing LLM output missing BEGIN marker."""
        llm_output = """QUERY(Find tickets)
TASK(Update page)
END"""
        
        with self.assertRaises(FailParser) as context:
            self.parser.parse_llm_output(llm_output)
        
        self.assertIn("Missing BEGIN marker", str(context.exception))
    
    def test_parse_missing_end(self):
        """Test parsing LLM output missing END marker."""
        llm_output = """BEGIN
QUERY(Find tickets)
TASK(Update page)"""
        
        with self.assertRaises(FailParser) as context:
            self.parser.parse_llm_output(llm_output)
        
        self.assertIn("Missing END marker", str(context.exception))
    
    def test_parse_begin_after_end(self):
        """Test parsing LLM output with BEGIN after END."""
        llm_output = """END
QUERY(Find tickets)
BEGIN"""
        
        with self.assertRaises(FailParser) as context:
            self.parser.parse_llm_output(llm_output)
        
        self.assertIn("Missing BEGIN marker", str(context.exception))  # Fixed: this is the correct error message
    
    def test_parse_begin_same_line_as_end(self):
        """Test parsing LLM output with BEGIN and END on same line."""
        llm_output = """BEGIN END
QUERY(Find tickets)"""
        
        with self.assertRaises(FailParser) as context:
            self.parser.parse_llm_output(llm_output)
        
        self.assertIn("Missing BEGIN marker", str(context.exception))  # Fixed: this is the correct error message
    
    def test_parse_invalid_command_format(self):
        """Test parsing LLM output with invalid command format."""
        llm_output = """BEGIN
QUERY Find tickets
TASK(Update page)
END"""
        
        with self.assertRaises(FailParser) as context:
            self.parser.parse_llm_output(llm_output)
        
        self.assertIn("Invalid command format at line 2", str(context.exception))
    
    def test_parse_unknown_command_type(self):
        """Test parsing LLM output with unknown command type."""
        llm_output = """BEGIN
UNKNOWN(Do something)
END"""
        
        with self.assertRaises(FailParser) as context:
            self.parser.parse_llm_output(llm_output)
        
        self.assertIn("Unknown command type 'UNKNOWN' at line 2", str(context.exception))
    
    def test_parse_command_with_empty_data(self):
        """Test parsing commands with empty data."""
        llm_output = """BEGIN
QUERY()
TASK()
END"""
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].command_data, "")
        self.assertEqual(events[1].command_data, "")
    
    def test_parse_command_with_special_characters(self):
        """Test parsing commands with special characters in data."""
        llm_output = """BEGIN
QUERY(Find tickets with status="Open" AND priority=High)
TASK(Update page: "Project Status" - add new section)
END"""
        
        events = self.parser.parse_llm_output(llm_output)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].command_data, 'Find tickets with status="Open" AND priority=High')
        self.assertEqual(events[1].command_data, 'Update page: "Project Status" - add new section')


if __name__ == "__main__":
    unittest.main() 
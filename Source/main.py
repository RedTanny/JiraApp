#!/usr/bin/env python3
"""
Main application entry point for MCP JIRA system.

This file orchestrates the startup sequence:
1. Load configuration
2. Initialize MCP Layer
3. Create Orchestrator
4. Start Console UI
"""

import sys
import os
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Try to load python-dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Environment variables must be set manually.")

# Import our components
from mcp_layer import McpLayer
from orchestrator import Orchestrator
from console.console_ui import ConsoleUI


class MCPJiraApp:
    """Main application class for MCP JIRA system."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Load environment variables from .env file if available
        self._load_environment_variables()
        
        self.config_path = config_path or self._find_default_config()
        self.config: Dict[str, Any] = {}        
        self.orchestrator: Optional[Orchestrator] = None
        self.console_ui: Optional[ConsoleUI] = None
        
    def _load_environment_variables(self) -> None:
        """Load environment variables from .env file if it exists."""
        if not DOTENV_AVAILABLE:
            return
            
        # Look for .env file in current directory, then parent directory
        env_paths = [
            ".env",
            "../.env",
            "../../.env"
        ]
        
        env_loaded = False
        for env_path in env_paths:
            if os.path.exists(env_path):
                try:
                    load_dotenv(env_path, override=True)
                    print(f"✅ Environment variables loaded from: {env_path}")
                    env_loaded = True
                    break
                except Exception as e:
                    print(f"⚠️  Warning: Could not load {env_path}: {e}")
        
        if not env_loaded:
            print("ℹ️  No .env file found. Using system environment variables.")
        
    def _find_default_config(self) -> str:
        """Find the default configuration file."""
        # Look for config in current directory, then Source directory
        possible_paths = [
            "JiraApp.yaml",
            "Source/JiraApp.yaml"             
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path        
        # If no config found, return empty string
        return ""
    
    def load_config(self) -> bool:
        """Load configuration from YAML file."""
        try:
            if not os.path.exists(self.config_path):
                print(f"❌ Configuration file not found: {self.config_path}")
                return False
            
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            print(f"✅ Configuration loaded from: {self.config_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return False
        
    def create_orchestrator(self) -> bool:
        """Create and configure the Orchestrator."""
        try:
            print("🎯 Creating Orchestrator...")
                        
            # Create orchestrator
            self.orchestrator = Orchestrator(self.config)
            res = self.orchestrator.initialize()
            if not res:
                print("❌ Error initializing Orchestrator")
                return False
            print("✅ Orchestrator created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating Orchestrator: {e}")
            return False
    
    def start_console_ui(self) -> bool:
        """Start the Console UI."""
        try:
            print("🖥️ Starting Console UI...")
            
            # Create console UI
            self.console_ui = ConsoleUI(self.orchestrator)
            
            print("✅ Console UI started successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error starting Console UI: {e}")
            return False
    
    def run(self) -> int:
        """Run the main application."""
        print("🚀 Starting MCP JIRA Application...")
        print("=" * 50)
        
        try:
            # Step 1: Load configuration
            if not self.load_config():
                return 1            
            # Step 2: Create Orchestrator
            if not self.create_orchestrator():
                return 1
            
            # Step 4: Start Console UI
            if not self.start_console_ui():
                return 1
            
            print("\n🎉 Application startup completed successfully!")
            print("=" * 50)
            
            # Start the console interactive loop
            self.console_ui.start()
            
            return 0
            
        except KeyboardInterrupt:
            print("\n⚠️ Application interrupted by user")
            return 0
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        print("\n🧹 Cleaning up resources...")
        
        try:
            if self.console_ui:
                self.console_ui.stop()
            
            if self.orchestrator:
                self.orchestrator.cleanup()
                
            print("✅ Cleanup completed")
            
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCP JIRA Console Application")
    parser.add_argument(
        "--config", 
        "-c",
        help="Path to configuration file (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    # Create and run application
    app = MCPJiraApp(args.config)
    return app.run()


if __name__ == "__main__":
    sys.exit(main()) 
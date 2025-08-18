#!/usr/bin/env python3
"""
Benchmark script for prompt engineering performance with structured function calls.
Tests the multiply tool using prompt engineering instead of native tool calling.
"""

import time
import json
import statistics
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_ollama import ChatOllama

@dataclass
class BenchmarkResult:
    model: str
    run_type: str  # "boot" or "warm"
    latency_ms: float
    structure_success: bool
    parsing_success: bool
    execution_success: bool
    error_message: str = ""
    timestamp: str = ""
    raw_response: str = ""
    parsed_command: str = ""
    execution_result: Any = None

class PromptToolBenchmark:
    def __init__(self):
        self.models = ["llama3.2:3b"]
        self.results: List[BenchmarkResult] = []
        self.model_first_run: Dict[str, bool] = {model: True for model in self.models}
        
        # Test cases for the multiply tool
        self.test_cases = [
            {
                "name": "multiply_5_12",
                "prompt": "What is 5 multiplied by 12?",
                "expected_result": 60,
                "description": "Multiply 5 by 12 using the multiply tool"
            },
            {
                "name": "multiply_10_10",
                "prompt": "How much is 10 * 10?",
                "expected_result": 100,
                "description": "Multiply 10 by 10 using the multiply tool"
            },
            {
                "name": "multiply_5_30",
                "prompt": "Multiply 5 * 30",
                "expected_result": 150,
                "description": "Multiply 5 by 30 using the multiply tool"
            },
            {
                "name": "multiply_7_8",
                "prompt": "What's 7 times 8?",
                "expected_result": 56,
                "description": "Multiply 7 by 8 using the multiply tool"
            },
            {
                "name": "multiply_15_4",
                "prompt": "Calculate 15 multiplied by 4",
                "expected_result": 60,
                "description": "Multiply 15 by 4 using the multiply tool"
            }
        ]
        
        # Prompt template specifically for the multiply tool
        self.prompt_template = """You are an AI assistant designed to translate natural language requests into specific function calls.

Your available tools are:
- `multiply(a, b)`: Multiplies two integers and returns the result.

Requirements:
- Only output the structure: BEGIN, <Commands>(...), END.
- Commands can be QUERY, TASK, or ERROR.
- Do not add any other text.

Here are examples of how to translate user requests:

1. **User Request:** "What is 3 multiplied by 4?"
   **Your Output:**
   BEGIN
   QUERY(multiply(3, 4))
   END

2. **User Request:** "Calculate 10 times 7"
   **Your Output:**
   BEGIN
   QUERY(multiply(10, 7))
   END

3. **User Request:** "Multiply 2 and 8"
   **Your Output:**
   BEGIN
   QUERY(multiply(2, 8))
   END

4. **User Request:** "What's the product of 6 and 9?"
   **Your Output:**
   BEGIN
   QUERY(multiply(6, 9))
   END

User Request: {user_input}"""
        
    def check_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            result = subprocess.run(['ollama', 'list'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama."""
        try:
            result = subprocess.run(['ollama', 'list'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                available = []
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 1:
                            available.append(parts[0])
                return available
        except Exception as e:
            print(f"Error getting available models: {e}")
        return []
    
    def parse_structured_response(self, response: str) -> Tuple[bool, str]:
        """Parse the structured response and extract the multiply command."""
        try:
            # Look for BEGIN/END pattern
            begin_match = re.search(r'BEGIN', response, re.IGNORECASE)
            end_match = re.search(r'END', response, re.IGNORECASE)
            
            if not begin_match or not end_match:
                return False, ""
            
            # Extract content between BEGIN and END
            begin_pos = begin_match.end()
            end_pos = end_match.start()
            content = response[begin_pos:end_pos].strip()
            
            # Look for multiply command
            multiply_pattern = r'QUERY\s*\(\s*multiply\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*\)'
            match = re.search(multiply_pattern, content, re.IGNORECASE)
            
            if match:
                # Extract the full command
                full_match = re.search(r'QUERY\s*\(\s*multiply\s*\([^)]*\)\s*\)', content, re.IGNORECASE)
                if full_match:
                    return True, full_match.group(0)
            
            return False, ""
            
        except Exception as e:
            print(f"Error parsing response: {e}")
            return False, ""
    
    def execute_multiply_command(self, command: str) -> Tuple[bool, Any]:
        """Execute the parsed multiply command and return the result."""
        try:
            # Extract the numbers from the command
            numbers_pattern = r'multiply\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)'
            match = re.search(numbers_pattern, command, re.IGNORECASE)
            
            if match:
                a = int(match.group(1))
                b = int(match.group(2))
                result = a * b
                return True, result
            
            return False, None
            
        except Exception as e:
            print(f"Error executing command: {e}")
            return False, None
    
    def benchmark_prompt_tool(self, llm: ChatOllama, test_case: Dict[str, Any], run_type: str) -> BenchmarkResult:
        """Benchmark prompt engineering for the multiply tool."""
        start_time = time.time()
        structure_success = False
        parsing_success = False
        execution_success = False
        error_message = ""
        raw_response = ""
        parsed_command = ""
        execution_result = None
        
        try:
            
            # Build the prompt with the test case
            prompt = self.prompt_template.format(user_input=test_case["prompt"])
            
             
            # Invoke the LLM with the prompt
            response = llm.invoke(prompt)
            
            raw_response = response.content if hasattr(response, 'content') else str(response)
            
            # Step 1: Check if response follows BEGIN/END structure
            if "BEGIN" in raw_response.upper() and "END" in raw_response.upper():
                structure_success = True
            
            # Step 2: Parse the structured response
            if structure_success:
                parsing_success, parsed_command = self.parse_structured_response(raw_response)
                
                # Step 3: Execute the parsed command
                if parsing_success:
                    execution_success, execution_result = self.execute_multiply_command(parsed_command)
                    
                    # Check if execution result matches expected
                    if execution_success and execution_result == test_case["expected_result"]:
                        pass  # All good
                    elif execution_success:
                        error_message = f"Wrong result: expected {test_case['expected_result']}, got {execution_result}"
                    else:
                        error_message = "Failed to execute parsed command"
                else:
                    error_message = "Failed to parse multiply command from structured response"
            else:
                error_message = "Response does not follow BEGIN/END structure"
                
        except Exception as e:
            error_message = str(e)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return BenchmarkResult(
            model=llm.model,
            run_type=run_type,
            latency_ms=latency_ms,
            structure_success=structure_success,
            parsing_success=parsing_success,
            execution_success=execution_success,
            error_message=error_message,
            timestamp=datetime.now().isoformat(),
            raw_response=raw_response,
            parsed_command=parsed_command,
            execution_result=execution_result
        )
    
    def run_benchmarks(self, runs_per_model: int = 20):
        """Run benchmarks for all models."""
        print("🔧 Prompt Tool Benchmark Starting...")
        print(f"Testing {len(self.models)} models with {len(self.test_cases)} test cases, {runs_per_model} runs each")
        print("=" * 80)
        
        if not self.check_ollama_available():
            print("❌ Ollama is not running or accessible")
            return
        
        available_models = self.get_available_models()
        print(f"Available models: {', '.join(available_models)}")
        print()
        
        for model in self.models:
            if model not in available_models:
                print(f"⚠️  Model {model} not available, skipping...")
                continue
                
            print(f"🧠 Testing model: {model}")
            # Initialize the LLM with the model
            llm = ChatOllama(model=model)
            
            for test_case in self.test_cases:
                print(f"  📝 Test case: {test_case['name']} - {test_case['description']}")
                
                for run in range(runs_per_model):
                    run_type = "boot" if self.model_first_run[model] else "warm"
                    
                    print(f"    Run {run + 1}/{runs_per_model} ({run_type})...", end=" ")
                    
                    result = self.benchmark_prompt_tool(llm, test_case, run_type)
                    self.results.append(result)
                    
                    if result.execution_success and result.execution_result == test_case["expected_result"]:
                        print(f"✅ {result.latency_ms:.1f}ms")
                    elif result.parsing_success:
                        print(f"⚠️  {result.latency_ms:.1f}ms (parsed but execution failed)")
                    elif result.structure_success:
                        print(f"⚠️  {result.latency_ms:.1f}ms (structure ok but parsing failed)")
                    else:
                        print(f"❌ {result.latency_ms:.1f}ms - {result.error_message}")
                    
                    if self.model_first_run[model]:
                        self.model_first_run[model] = False
                    
                    time.sleep(1)
                
                print()
    
    def generate_report(self):
        """Generate a comprehensive benchmark report."""
        if not self.results:
            print("No results to report")
            return
        
        print("\n📊 BENCHMARK REPORT")
        print("=" * 80)
        
        # Group results by model and run type
        model_stats: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
        
        for result in self.results:
            if result.model not in model_stats:
                model_stats[result.model] = {}
            
            run_type = result.run_type
            
            if run_type not in model_stats[result.model]:
                model_stats[result.model][run_type] = {
                    "latency": [], 
                    "structure_rate": [], 
                    "parsing_rate": [], 
                    "execution_rate": []
                }
            
            # Record success rates
            model_stats[result.model][run_type]["structure_rate"].append(1.0 if result.structure_success else 0.0)
            model_stats[result.model][run_type]["parsing_rate"].append(1.0 if result.parsing_success else 0.0)
            model_stats[result.model][run_type]["execution_rate"].append(1.0 if result.execution_success else 0.0)
            model_stats[result.model][run_type]["latency"].append(result.latency_ms)
        
        for model, stats in model_stats.items():
            print(f"\n🔍 {model}")
            print("-" * 60)
            
            for run_type in ["boot", "warm"]:
                if run_type in stats:
                    latencies = stats[run_type]["latency"]
                    structure_rates = stats[run_type]["structure_rate"]
                    parsing_rates = stats[run_type]["parsing_rate"]
                    execution_rates = stats[run_type]["execution_rate"]
                    
                    if latencies:
                        avg_latency = statistics.mean(latencies)
                        min_latency = min(latencies)
                        max_latency = max(latencies)
                        std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
                        avg_structure_rate = statistics.mean(structure_rates) * 100
                        avg_parsing_rate = statistics.mean(parsing_rates) * 100
                        avg_execution_rate = statistics.mean(execution_rates) * 100
                        
                        print(f"  {run_type.capitalize()} runs ({len(latencies)}):")
                        print(f"    Avg Latency: {avg_latency:.1f}ms")
                        print(f"    Min Latency: {min_latency:.1f}ms")
                        print(f"    Max Latency: {max_latency:.1f}ms")
                        print(f"    Std Dev: {std_dev:.1f}ms")
                        print(f"    Structure Success: {avg_structure_rate:.1f}%")
                        print(f"    Parsing Success: {avg_parsing_rate:.1f}%")
                        print(f"    Execution Success: {avg_execution_rate:.1f}%")
                    else:
                        print(f"  {run_type.capitalize()} runs: No data")
        
        print("\n📈 OVERALL SUMMARY")
        print("-" * 60)
        
        boot_latencies = [r.latency_ms for r in self.results if r.run_type == "boot"]
        warm_latencies = [r.latency_ms for r in self.results if r.run_type == "warm"]
        all_structure_rates = [1.0 if r.structure_success else 0.0 for r in self.results]
        all_parsing_rates = [1.0 if r.parsing_success else 0.0 for r in self.results]
        all_execution_rates = [1.0 if r.execution_success else 0.0 for r in self.results]
        
        if boot_latencies:
            print(f"Boot time average: {statistics.mean(boot_latencies):.1f}ms")
        if warm_latencies:
            print(f"Warm time average: {statistics.mean(warm_latencies):.1f}ms")
        if all_structure_rates:
            print(f"Overall structure success rate: {statistics.mean(all_structure_rates) * 100:.1f}%")
        if all_parsing_rates:
            print(f"Overall parsing success rate: {statistics.mean(all_parsing_rates) * 100:.1f}%")
        if all_execution_rates:
            print(f"Overall execution success rate: {statistics.mean(all_execution_rates) * 100:.1f}%")
        
        self.save_results()
    
    def save_results(self):
        """Save benchmark results to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_tool_benchmark_{timestamp}.json"
        
        results_dict = [asdict(result) for result in self.results]
        
        with open(filename, 'w') as f:
            json.dump({
                "benchmark_type": "prompt_tool",
                "timestamp": timestamp,
                "models_tested": self.models,
                "test_cases": [{"name": tc["name"], "description": tc["description"]} for tc in self.test_cases],
                "results": results_dict
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    """Main function to run the benchmark."""
    benchmark = PromptToolBenchmark()
    
    try:
        benchmark.run_benchmarks(runs_per_model=20)
        benchmark.generate_report()
    except KeyboardInterrupt:
        print("\n\n⏹️  Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

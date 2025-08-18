#!/usr/bin/env python3
"""
Benchmark script for tool calling performance across different Ollama models.
Tests tool calling latency and categorizes first runs as boot time.
"""

import time
import json
import statistics
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_ollama import ChatOllama
from langchain_core.tools import tool

@dataclass
class BenchmarkResult:
    model: str
    run_type: str  # "boot" or "warm"
    latency_ms: float
    success: bool
    error_message: str = ""
    timestamp: str = ""

# Define a simple tool to use for the benchmark
@tool
def multiply(a: int, b: int) -> int:
    """
    Multiply two integers.
    
    Args:
        a: The first integer.
        b: The second integer.
    """
    return a * b

class ToolCallingBenchmark:
    def __init__(self):
        # A simple tool and a list of models to test
        self.tool = multiply
        self.models = [
            "llama3.2:3b"
           # "gemma3n:latest", 
           # "deepseek-r1:1.5b",
           # "qwen3:4b",
           # "phi3.5:3.8b"
        ]
        self.results: List[BenchmarkResult] = []
        self.model_first_run: Dict[str, bool] = {model: True for model in self.models}
        
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
    
    def benchmark_tool_calling(self, model: str, run_type: str) -> BenchmarkResult:
        """Benchmark tool calling for a specific model."""
        start_time = time.time()
        success = False
        error_message = ""
        
        try:
            # Initialize the LLM with the model
            llm = ChatOllama(model=model)
            
            # Bind the tool to the LLM instance
            llm_with_tools = llm.bind_tools([self.tool])
            
            # The prompt is specifically designed to require tool use
            prompt = "What is 5 multiplied by 12?"
            
            # Invoke the LLM with the tool-calling prompt
            response = llm_with_tools.invoke(prompt)
            
            # Check if the response contains a tool call
            if response.tool_calls:
                # Assuming the model makes a single tool call for this simple prompt
                tool_call = response.tool_calls[0]
                if tool_call['name'] == 'multiply' and tool_call['args'] == {'a': 5, 'b': 12}:
                    success = True
                else:
                    error_message = f"Incorrect tool call: {tool_call}"
            else:
                error_message = "No tool call detected"
                
        except Exception as e:
            error_message = str(e)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return BenchmarkResult(
            model=model,
            run_type=run_type,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            timestamp=datetime.now().isoformat()
        )
    
    def run_benchmarks(self, runs_per_model: int = 3):
        """Run benchmarks for all models."""
        print("🔧 Tool Calling Benchmark Starting...")
        print(f"Testing {len(self.models)} models with {runs_per_model} runs each")
        print("=" * 60)
        
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
            
            for run in range(runs_per_model):
                run_type = "boot" if self.model_first_run[model] else "warm"
                
                print(f"  Run {run + 1}/{runs_per_model} ({run_type})...", end=" ")
                
                result = self.benchmark_tool_calling(model, run_type)
                self.results.append(result)
                
                if result.success:
                    print(f"✅ {result.latency_ms:.1f}ms")
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
        print("=" * 60)
        
        model_stats: Dict[str, Dict[str, List[float]]] = {}
        
        for result in self.results:
            if result.model not in model_stats:
                model_stats[result.model] = {"boot": [], "warm": []}
            
            if result.success:
                model_stats[result.model][result.run_type].append(result.latency_ms)
        
        for model, stats in model_stats.items():
            print(f"\n🔍 {model}")
            print("-" * 40)
            
            for run_type in ["boot", "warm"]:
                latencies = stats[run_type]
                if latencies:
                    avg_latency = statistics.mean(latencies)
                    min_latency = min(latencies)
                    max_latency = max(latencies)
                    std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
                    
                    print(f"  {run_type.capitalize()} runs ({len(latencies)}):")
                    print(f"    Avg: {avg_latency:.1f}ms")
                    print(f"    Min: {min_latency:.1f}ms")
                    print(f"    Max: {max_latency:.1f}ms")
                    print(f"    Std: {std_dev:.1f}ms")
                else:
                    print(f"  {run_type.capitalize()} runs: No successful runs")
        
        print("\n📈 OVERALL SUMMARY")
        print("-" * 40)
        
        boot_latencies = [r.latency_ms for r in self.results if r.run_type == "boot" and r.success]
        warm_latencies = [r.latency_ms for r in self.results if r.run_type == "warm" and r.success]
        
        if boot_latencies:
            print(f"Boot time average: {statistics.mean(boot_latencies):.1f}ms")
        if warm_latencies:
            print(f"Warm time average: {statistics.mean(warm_latencies):.1f}ms")
        
        self.save_results()
    
    def save_results(self):
        """Save benchmark results to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tool_calling_benchmark_{timestamp}.json"
        
        results_dict = [asdict(result) for result in self.results]
        
        with open(filename, 'w') as f:
            json.dump({
                "benchmark_type": "tool_calling",
                "timestamp": timestamp,
                "models_tested": self.models,
                "results": results_dict
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    """Main function to run the benchmark."""
    benchmark = ToolCallingBenchmark()
    
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
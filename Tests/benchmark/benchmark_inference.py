#!/usr/bin/env python3
"""
Benchmark script for inference performance across different Ollama models.
Tests text generation latency and categorizes first runs as boot time.
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

os.environ['OLLAMA_HOST'] = 'http://127.0.0.1:11434'
# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_ollama import ChatOllama

@dataclass
class BenchmarkResult:
    model: str
    run_type: str  # "boot" or "warm"
    latency_ms: float
    tokens_generated: int
    tokens_per_second: float
    success: bool
    error_message: str = ""
    timestamp: str = ""

class InferenceBenchmark:
    def __init__(self):
        self.models = [
            "llama3.2:3b",
            "gemma3n:latest", 
            "deepseek-r1:1.5b",
            "qwen3:4b",
            "phi3.5:3.8b"
        ]
        self.results: List[BenchmarkResult] = []
        self.model_first_run: Dict[str, bool] = {model: True for model in self.models}
        
        # Test prompts of different lengths
        self.test_prompts = [
            "Write a short poem about AI.",
            "Explain the concept of machine learning in one paragraph.",            
        ]
        
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
    
    def count_tokens_approximate(self, text: str) -> int:
        """Approximate token count (rough estimate: 1 token ≈ 4 characters)."""
        return len(text) // 4
    
    def benchmark_inference(self, model: str, prompt: str, run_type: str) -> BenchmarkResult:
        """Benchmark inference for a specific model and prompt."""
        start_time = time.time()
        success = False
        error_message = ""
        response_text = ""
        
        try:
            # Initialize the LLM with the model
            llm = ChatOllama(model=model)
            
            # Test inference
            response = llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            if response_text and len(response_text) > 0:
                success = True
            else:
                error_message = "Empty response"
                
        except Exception as e:
            error_message = str(e)
        
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Calculate token metrics
        tokens_generated = self.count_tokens_approximate(response_text)
        tokens_per_second = (tokens_generated / (end_time - start_time)) if (end_time - start_time) > 0 else 0
        
        return BenchmarkResult(
            model=model,
            run_type=run_type,
            latency_ms=latency_ms,
            tokens_generated=tokens_generated,
            tokens_per_second=tokens_per_second,
            success=success,
            error_message=error_message,
            timestamp=datetime.now().isoformat()
        )
    
    def run_benchmarks(self, runs_per_model: int = 2):
        """Run benchmarks for all models."""
        print("🚀 Inference Benchmark Starting...")
        print(f"Testing {len(self.models)} models with {len(self.test_prompts)} prompts, {runs_per_model} runs each")
        print("=" * 70)
              
        # Get available models
        available_models = self.get_available_models()
        print(f"Available models: {', '.join(available_models)}")
        print()
        
        for model in self.models:
            if model not in available_models:
                print(f"⚠️  Model {model} not available, skipping...")
                continue
                
            print(f"🧠 Testing model: {model}")
            
            for prompt_idx, prompt in enumerate(self.test_prompts):
                print(f"  Prompt {prompt_idx + 1}: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
                
                for run in range(runs_per_model):
                    run_type = "boot" if self.model_first_run[model] else "warm"
                    
                    print(f"    Run {run + 1}/{runs_per_model} ({run_type})...", end=" ")
                    
                    result = self.benchmark_inference(model, prompt, run_type)
                    self.results.append(result)
                    
                    if result.success:
                        print(f"✅ {result.latency_ms:.1f}ms, {result.tokens_generated} tokens, {result.tokens_per_second:.1f} t/s")
                    else:
                        print(f"❌ {result.latency_ms:.1f}ms - {result.error_message}")
                    
                    # Mark first run as complete
                    if self.model_first_run[model]:
                        self.model_first_run[model] = False
                    
                    # Small delay between runs
                    time.sleep(1)
                
                print()
            
            print()
    
    def generate_report(self):
        """Generate a comprehensive benchmark report."""
        if not self.results:
            print("No results to report")
            return
        
        print("\n📊 INFERENCE BENCHMARK REPORT")
        print("=" * 70)
        
        # Group results by model and run type
        model_stats: Dict[str, Dict[str, List[BenchmarkResult]]] = {}
        
        for result in self.results:
            if result.model not in model_stats:
                model_stats[result.model] = {"boot": [], "warm": []}
            
            if result.success:
                model_stats[result.model][result.run_type].append(result)
        
        # Calculate and display statistics
        for model, stats in model_stats.items():
            print(f"\n🔍 {model}")
            print("-" * 50)
            
            for run_type in ["boot", "warm"]:
                results = stats[run_type]
                if results:
                    latencies = [r.latency_ms for r in results]
                    tokens_per_sec = [r.tokens_per_second for r in results]
                    tokens_generated = [r.tokens_generated for r in results]
                    
                    avg_latency = statistics.mean(latencies)
                    avg_tokens_per_sec = statistics.mean(tokens_per_sec)
                    avg_tokens = statistics.mean(tokens_generated)
                    
                    print(f"  {run_type.capitalize()} runs ({len(results)}):")
                    print(f"    Avg Latency: {avg_latency:.1f}ms")
                    print(f"    Avg Tokens/sec: {avg_tokens_per_sec:.1f}")
                    print(f"    Avg Tokens Generated: {avg_tokens:.0f}")
                else:
                    print(f"  {run_type.capitalize()} runs: No successful runs")
        
        # Overall summary
        print("\n📈 OVERALL SUMMARY")
        print("-" * 50)
        
        boot_results = [r for r in self.results if r.run_type == "boot" and r.success]
        warm_results = [r for r in self.results if r.run_type == "warm" and r.success]
        
        if boot_results:
            avg_boot_latency = statistics.mean([r.latency_ms for r in boot_results])
            avg_boot_tokens_per_sec = statistics.mean([r.tokens_per_second for r in boot_results])
            print(f"Boot time average: {avg_boot_latency:.1f}ms, {avg_boot_tokens_per_sec:.1f} tokens/sec")
        
        if warm_results:
            avg_warm_latency = statistics.mean([r.latency_ms for r in warm_results])
            avg_warm_tokens_per_sec = statistics.mean([r.tokens_per_second for r in warm_results])
            print(f"Warm time average: {avg_warm_latency:.1f}ms, {avg_warm_tokens_per_sec:.1f} tokens/sec")
        
        # Save results to file
        self.save_results()
    
    def save_results(self):
        """Save benchmark results to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inference_benchmark_{timestamp}.json"
        
        # Convert results to dict for JSON serialization
        results_dict = [asdict(result) for result in self.results]
        
        with open(filename, 'w') as f:
            json.dump({
                "benchmark_type": "inference",
                "timestamp": timestamp,
                "models_tested": self.models,
                "test_prompts": self.test_prompts,
                "results": results_dict
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    """Main function to run the benchmark."""
    benchmark = InferenceBenchmark()
    
    try:
        benchmark.run_benchmarks(runs_per_model=2)
        benchmark.generate_report()
    except KeyboardInterrupt:
        print("\n\n⏹️  Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

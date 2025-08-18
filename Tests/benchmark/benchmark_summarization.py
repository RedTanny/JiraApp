#!/usr/bin/env python3
"""
Benchmark script for text summarization performance across different Ollama models.
Focus: Jira ticket summarization with three sections: Executive Summary, Action Items, Technical Details.
Categorizes first runs as boot time.
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
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_ollama import ChatOllama

@dataclass
class BenchmarkResult:
    model: str
    run_type: str  # "boot" or "warm"
    latency_ms: float
    input_length: int
    output_length: int
    compression_ratio: float
    success: bool
    error_message: str = ""
    timestamp: str = ""

class SummarizationBenchmark:
    def __init__(self):
        self.models = [
            "deepseek-r1:1.5b",
            "llama3.2:3b",
            "gemma3n:latest",             
            "phi3.5:3.8b"
        ]
        self.results: List[BenchmarkResult] = []
        self.model_first_run: Dict[str, bool] = {model: True for model in self.models}
        
        # Jira-like ticket texts of varying sizes
        self.test_texts = [
            # Ticket A - short
            (
                "PROJ-1421: Login button unresponsive on mobile\n\n"
                "Summary: Users report the login button does not trigger authentication on iOS Safari.\n"
                "Steps: 1) Navigate to /login 2) Enter valid creds 3) Tap 'Login' 4) Nothing happens.\n"
                "Expected: User is redirected to dashboard.\n"
                "Observed: No network call fired. Console shows 'TypeError: e.preventDefault is not a function'.\n"
                "Environment: iOS 17.2, Safari 17.0.\n"
                "Comments: QA reproduced; Product requested hotfix.\n"
            ),
            # Ticket B - medium
            (
                "PROJ-1987: Search latency spikes above SLO during peak hours\n\n"
                "Description: From 10:00-12:00 UTC, P95 latency increases from 350ms to 2.5s.\n"
                "Preliminary findings: Elevated DB CPU (85-95%), cache miss ratio doubled, autoscaling reached max nodes.\n"
                "Related changes: Deployed feature flag 'semantic_search_v2' yesterday.\n"
                "Logs: Many 'timeout acquiring connection from pool' messages in search-api.\n"
                "Impact: Customer complaints from tier-1 accounts; reported by CSM.\n"
                "Requested: Immediate mitigation and root-cause analysis.\n"
                "Comments: SRE suggests increasing pool size; Data team suggests roll back feature flag.\n"
            ),
            # Ticket C - long
            (
                "PROJ-2050: Migrate notification service to event-driven architecture\n\n"
                "Background: Current cron-based batch notifications cause delays and duplicate sends under retries.\n"
                "Goal: Move to Kafka + consumer groups; idempotent processing; per-tenant throttling and DLQ.\n"
                "Requirements: 1) Publish events from order, billing, and support systems; 2) Enforce at-least-once delivery;\n"
                "3) Add schema registry for payload evolution; 4) Migrate templates to new renderer; 5) Add observability (traces, metrics).\n"
                "Risks: Breaking changes to downstream email provider; PCI considerations for payload fields.\n"
                "Timeline: Phase 1 (publishers), Phase 2 (consumers + metrics), Phase 3 (cutover + delete cron).\n"
                "Success metrics: <200ms end-to-end for 95% notifications, <0.01% duplicates.\n"
                "Stakeholders: Platform, SRE, Billing, Support.\n"
                "Comments: Prototype exists; needs security review and capacity planning.\n"
            ),
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
    
    def _has_required_sections(self, text: str) -> bool:
        t = text.lower()
        return (
            "executive summary" in t and
            "action items" in t and
            "technical details" in t
        )
    
    def benchmark_summarization(self, model: str, text: str, run_type: str) -> BenchmarkResult:
        """Benchmark summarization for a specific model and text."""
        start_time = time.time()
        success = False
        error_message = ""
        summary = ""
        
        try:
            # Initialize the LLM with the model
            llm = ChatOllama(model=model)
            
            # Jira-focused structured summarization prompt
            prompt = (
                "You are an expert Jira analyst. Summarize the following ticket into three sections using concise Markdown.\n"
                "Output strictly in this structure and nothing else:\n\n"
                "### Executive Summary\n"
                "- One to three bullets capturing the essence, impact, and priority\n\n"
                "### Action Items\n"
                "- Bulleted list with owner (if available) and suggested due date\n"
                "- Include immediate mitigations and follow-ups\n\n"
                "### Technical Details\n"
                "- Root cause hypotheses, logs, metrics, environments, risks, dependencies\n\n"
                f"Ticket:\n{text}\n"
            )
            
            # Test summarization
            response = llm.invoke(prompt)
            summary = response.content if hasattr(response, 'content') else str(response)
            
            if summary and self._has_required_sections(summary):
                success = True
            else:
                error_message = "Missing required sections or empty output"
                
        except Exception as e:
            error_message = str(e)
        
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Calculate metrics
        input_length = len(text)
        output_length = len(summary) if summary else 0
        compression_ratio = (input_length - output_length) / input_length if input_length > 0 else 0
        
        return BenchmarkResult(
            model=model,
            run_type=run_type,
            latency_ms=latency_ms,
            input_length=input_length,
            output_length=output_length,
            compression_ratio=compression_ratio,
            success=success,
            error_message=error_message,
            timestamp=datetime.now().isoformat()
        )
    
    def run_benchmarks(self, runs_per_model: int = 2):
        """Run benchmarks for all models."""
        print("📝 Jira Summarization Benchmark Starting...")
        print(f"Testing {len(self.models)} models with {len(self.test_texts)} tickets, {runs_per_model} runs each")
        print("=" * 80)
        
        # Check Ollama availability
        if not self.check_ollama_available():
            print("❌ Ollama is not running or accessible")
            return
        
        # Get available models
        available_models = self.get_available_models()
        print(f"Available models: {', '.join(available_models)}")
        print()
        
        for model in self.models:
            if model not in available_models:
                print(f"⚠️  Model {model} not available, skipping...")
                continue
                
            print(f"🧠 Testing model: {model}")
            
            for text_idx, text in enumerate(self.test_texts):
                text_length = len(text)
                preview = re.sub(r"\s+", " ", text)[:60]
                print(f"  Ticket {text_idx + 1} ({text_length} chars): {preview}{'...' if text_length > 60 else ''}")
                
                for run in range(runs_per_model):
                    run_type = "boot" if self.model_first_run[model] else "warm"
                    
                    print(f"    Run {run + 1}/{runs_per_model} ({run_type})...", end=" ")
                    
                    result = self.benchmark_summarization(model, text, run_type)
                    self.results.append(result)
                    
                    if result.success:
                        print(f"✅ {result.latency_ms:.1f}ms, {result.output_length} chars, {result.compression_ratio:.1%} compression")
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
        
        print("\n📊 SUMMARIZATION BENCHMARK REPORT")
        print("=" * 80)
        
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
            print("-" * 60)
            
            for run_type in ["boot", "warm"]:
                results = stats[run_type]
                if results:
                    latencies = [r.latency_ms for r in results]
                    compression_ratios = [r.compression_ratio for r in results]
                    output_lengths = [r.output_length for r in results]
                    
                    avg_latency = statistics.mean(latencies)
                    avg_compression = statistics.mean(compression_ratios)
                    avg_output_length = statistics.mean(output_lengths)
                    
                    print(f"  {run_type.capitalize()} runs ({len(results)}):")
                    print(f"    Avg Latency: {avg_latency:.1f}ms")
                    print(f"    Avg Compression: {avg_compression:.1%}")
                    print(f"    Avg Output Length: {avg_output_length:.0f} chars")
                else:
                    print(f"  {run_type.capitalize()} runs: No successful runs")
        
        # Overall summary
        print("\n📈 OVERALL SUMMARY")
        print("-" * 60)
        
        boot_results = [r for r in self.results if r.run_type == "boot" and r.success]
        warm_results = [r for r in self.results if r.run_type == "warm" and r.success]
        
        if boot_results:
            avg_boot_latency = statistics.mean([r.latency_ms for r in boot_results])
            avg_boot_compression = statistics.mean([r.compression_ratio for r in boot_results])
            print(f"Boot time average: {avg_boot_latency:.1f}ms, {avg_boot_compression:.1%} compression")
        
        if warm_results:
            avg_warm_latency = statistics.mean([r.latency_ms for r in warm_results])
            avg_warm_compression = statistics.mean([r.compression_ratio for r in warm_results])
            print(f"Warm time average: {avg_warm_latency:.1f}ms, {avg_warm_compression:.1%} compression")
        
        # Save results to file
        self.save_results()
    
    def save_results(self):
        """Save benchmark results to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summarization_benchmark_{timestamp}.json"
        
        # Convert results to dict for JSON serialization
        results_dict = [asdict(result) for result in self.results]
        
        with open(filename, 'w') as f:
            json.dump({
                "benchmark_type": "summarization",
                "timestamp": timestamp,
                "models_tested": self.models,
                "test_texts": [{"length": len(text), "preview": re.sub(r"\\s+", " ", text)[:100]} for text in self.test_texts],
                "results": results_dict
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")

def main():
    """Main function to run the benchmark."""
    benchmark = SummarizationBenchmark()
    
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

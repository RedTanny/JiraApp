#!/usr/bin/env python3
"""
Simple LLM Chat Testing
Tests direct LLM chat without agent framework to measure pure LLM performance
"""

import os
import sys
import time
import json
from typing import Dict, List, Tuple

# Add the Client directory to the path
sys.path.append(str(os.path.join(os.path.dirname(__file__), '..', 'Client', 'data_access')))

try:
    from llama_stack_client import LlamaStackClient
except ImportError as e:
    print(f"❌ llama-stack-client not available: {e}")
    sys.exit(1)

# Configuration
LLAMA_STACK_URL = "http://localhost:8321"
TEST_ISSUE_KEY = "NCS-8540"

def test_simple_llm_chat(prompt: str, description: str) -> Tuple[float, str]:
    """
    Test simple LLM chat without agent framework
    
    Args:
        prompt: The prompt to send to the LLM
        description: Description for logging
        
    Returns:
        Tuple of (response_time_seconds, response_text)
    """
    print(f"\n🔧 Testing: {description}")
    print(f"   Prompt: {prompt[:100]}...")
    
    try:
        # Create simple client
        client = LlamaStackClient(base_url=LLAMA_STACK_URL)
        
        # Get available models
        models = client.models.list()
        llm_models = [m for m in models if m.model_type == "llm"]
        
        if not llm_models:
            print("   ❌ No LLM models available")
            return None, "No LLM models available"
        
        # Use first available model
        model = llm_models[0]
        print(f"   Model: {model.identifier}")
        
        # Prefer llama3.2:3b for tool support (Phi doesn't support tools)
        llama_models = [m for m in llm_models if 'llama3.2' in m.identifier.lower()]
        if llama_models:
            model = llama_models[0]
            print(f"   Selected Llama model for tool support: {model.identifier}")
        else:
            print(f"   No Llama models available, using: {model.identifier}")
            print(f"   ⚠️  Note: Some models may not support tool calling")
        
        start_time = time.time()
        
        # Simple chat completion
        response = client.chat.completions.create(
            model=model.identifier,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7,
            stream=False
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Extract response
        if response.choices and len(response.choices) > 0:
            response_text = response.choices[0].message.content
        else:
            response_text = "No response content"
        
        print(f"   ✅ Success")
        print(f"   ⏱️  Response Time: {response_time:.3f}s")
        print(f"   📊 Response Size: {len(response_text)} bytes")
        print(f"   📄 Response Preview: {response_text[:200]}...")
        
        return response_time, response_text
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        print(f"   📄 Traceback: {traceback.format_exc()}")
        return None, f"ERROR: {e}"

def test_llm_connection() -> bool:
    """Test LLM connection"""
    print("\n🔧 Testing: LLM Connection")
    
    try:
        start_time = time.time()
        client = LlamaStackClient(base_url=LLAMA_STACK_URL)
        
        # Test connection by listing models
        models = client.models.list()
        llm_models = [m for m in models if m.model_type == "llm"]
        
        end_time = time.time()
        connection_time = end_time - start_time
        
        print(f"   ✅ Connected successfully")
        print(f"   ⏱️  Connection Time: {connection_time:.3f}s")
        print(f"   🤖 Available LLM models: {len(llm_models)}")
        for model in llm_models[:3]:  # Show first 3 models
            print(f"      - {model.identifier}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def test_simple_questions() -> List[Tuple[str, float, str]]:
    """Test simple questions without tool calling"""
    print("\n🚀 Simple LLM Chat Testing (No Tools)")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        {
            "prompt": "Hello, how are you today?",
            "description": "Simple greeting"
        },
        {
            "prompt": "What is 2 + 2?",
            "description": "Simple math"
        },
        {
            "prompt": "Explain what JIRA is in one sentence.",
            "description": "Simple explanation"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔧 Test {i}: {test_case['description']}")
        
        response_time, response_text = test_simple_llm_chat(
            test_case['prompt'], 
            test_case['description']
        )
        
        results.append((test_case['description'], response_time, response_text))
    
    return results

def test_tool_awareness() -> List[Tuple[str, float, str]]:
    """Test if LLM knows about tools without using them"""
    print("\n🚀 LLM Tool Awareness Testing")
    print("=" * 60)
    
    # Test cases that mention tools but don't call them
    test_cases = [
        {
            "prompt": f"I have access to JIRA tools. If I wanted to get information about issue {TEST_ISSUE_KEY}, what would I need to do?",
            "description": "Tool awareness question"
        },
        {
            "prompt": "I can search JIRA issues. What would be a good JQL query to find open issues in the NCS project?",
            "description": "JQL knowledge question"
        },
        {
            "prompt": "What tools would be useful for working with JIRA data?",
            "description": "Tool recommendation question"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔧 Test {i}: {test_case['description']}")
        
        response_time, response_text = test_simple_llm_chat(
            test_case['prompt'], 
            test_case['description']
        )
        
        results.append((test_case['description'], response_time, response_text))
    
    return results

def run_simple_llm_tests():
    """Run all simple LLM tests"""
    print("🚀 Simple LLM Performance Testing")
    print("=" * 60)
    
    # Test LLM connection first
    if not test_llm_connection():
        print("\n❌ Failed to connect to LLM")
        return
    
    # Test simple questions
    simple_results = test_simple_questions()
    
    # Test tool awareness
    tool_results = test_tool_awareness()
    
    # Combine results
    all_results = simple_results + tool_results
    
    # Print summary
    print("\n📊 Simple LLM Performance Summary")
    print("=" * 60)
    print(f"{'Test':<25} {'Time (s)':<10} {'Size (bytes)':<15} {'Status':<10}")
    print("-" * 60)
    
    for test_name, response_time, response_text in all_results:
        status = "✅" if response_time and response_time < 60 else "❌"
        time_str = f"{response_time:.3f}" if response_time else "N/A"
        size_str = f"{len(response_text)}" if response_text else "N/A"
        print(f"{test_name:<25} {time_str:<10} {size_str:<15} {status:<10}")
    
    # Calculate averages
    valid_times = [t for t in [r[1] for r in all_results] if t and t < 60]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        print(f"\n📈 Average Response Time: {avg_time:.3f}s")
        print(f"📈 Fastest Response: {min(valid_times):.3f}s")
        print(f"📈 Slowest Response: {max(valid_times):.3f}s")
        
        # Compare with agent results
        print(f"\n📊 Performance Comparison:")
        print(f"   Simple LLM Chat: {avg_time:.3f}s average")
        print(f"   With Agent Framework: ~32.651s average (from previous test)")
        print(f"   Agent Framework Overhead: ~{(32.651/avg_time):.1f}x slower")
    
    print(f"\n🎉 Simple LLM testing completed!")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "connection":
            test_llm_connection()
        elif sys.argv[1] == "simple":
            test_simple_questions()
        elif sys.argv[1] == "tools":
            test_tool_awareness()
        else:
            print("Usage: python test_simple_llm_chat.py [connection|simple|tools]")
    else:
        run_simple_llm_tests()

if __name__ == "__main__":
    main() 
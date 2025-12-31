#!/usr/bin/env python3
"""
Test script for the unified LLMProvider.
Tests text generation, token tracking, and batch processing.
"""
import sys
import time
sys.path.insert(0, '.')

from src.LLMProvider import LLMProvider, LLMResponse
from src.config.config import (
    CHUNKING_PROVIDER, CHUNKING_MODEL,
    EXTRACTION_PROVIDER, EXTRACTION_MODEL,
    EVALUATION_PROVIDER, EVALUATION_MODEL
)

def test_basic_generation():
    """Test basic text generation with Gemini"""
    print("\n" + "="*60)
    print("TEST 1: Basic Text Generation")
    print("="*60)
    
    provider = LLMProvider(provider=CHUNKING_PROVIDER, model=CHUNKING_MODEL)
    print(f"Provider: {provider}")
    
    response = provider.generate(
        prompt="Say 'Hello, LLMProvider is working!' in exactly those words.",
        temperature=0.0,
        max_tokens=50
    )
    
    print(f"\nSuccess: {response.success}")
    print(f"Response: {response.text}")
    print(f"Input tokens: {response.input_tokens}")
    print(f"Output tokens: {response.output_tokens}")
    print(f"Cost: ${response.cost:.6f}")
    
    if response.error:
        print(f"Error: {response.error}")
    
    return response.success


def test_with_system_prompt():
    """Test generation with system prompt"""
    print("\n" + "="*60)
    print("TEST 2: Generation with System Prompt")
    print("="*60)
    
    provider = LLMProvider(provider=EXTRACTION_PROVIDER, model=EXTRACTION_MODEL)
    print(f"Provider: {provider}")
    
    response = provider.generate(
        prompt="What is 2 + 2?",
        system_prompt="You are a helpful math tutor. Answer briefly.",
        temperature=0.0,
        max_tokens=50
    )
    
    print(f"\nSuccess: {response.success}")
    print(f"Response: {response.text}")
    print(f"Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"Cost: ${response.cost:.6f}")
    
    return response.success


def test_config_values():
    """Display current config values"""
    print("\n" + "="*60)
    print("CURRENT CONFIG VALUES")
    print("="*60)
    print(f"Chunking:   {CHUNKING_PROVIDER}/{CHUNKING_MODEL}")
    print(f"Extraction: {EXTRACTION_PROVIDER}/{EXTRACTION_MODEL}")
    print(f"Evaluation: {EVALUATION_PROVIDER}/{EVALUATION_MODEL}")


def test_batch_generation(num_requests=100, max_workers=10):
    """Test multithreaded batch generation with 100 API calls"""
    print("\n" + "="*60)
    print(f"TEST 3: Batch Generation ({num_requests} requests, {max_workers} workers)")
    print("="*60)
    
    provider = LLMProvider(provider=CHUNKING_PROVIDER, model=CHUNKING_MODEL)
    print(f"Provider: {provider}")
    
    # Create 100 different prompts
    prompts = [f"What is {i} + {i}? Answer with just the number." for i in range(1, num_requests + 1)]
    
    print(f"\n🚀 Starting {num_requests} parallel requests...")
    start_time = time.time()
    
    responses = provider.batch_generate(
        prompts=prompts,
        system_prompt="You are a calculator. Answer with just the number, nothing else.",
        max_workers=max_workers,
        temperature=0.0,
        max_tokens=100  # Increased - Gemini 2.5 uses tokens for "thinking" before output
    )
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate stats
    successful = sum(1 for r in responses if r.success)
    failed = num_requests - successful
    total_input_tokens = sum(r.input_tokens for r in responses)
    total_output_tokens = sum(r.output_tokens for r in responses)
    total_cost = sum(r.cost for r in responses)
    
    print(f"\n📊 Results:")
    print(f"   Total time: {total_time:.2f} seconds")
    print(f"   Avg time per request: {total_time/num_requests:.3f} seconds")
    print(f"   Throughput: {num_requests/total_time:.2f} requests/second")
    print(f"\n   Successful: {successful}/{num_requests}")
    print(f"   Failed: {failed}/{num_requests}")
    print(f"\n   Total input tokens: {total_input_tokens}")
    print(f"   Total output tokens: {total_output_tokens}")
    print(f"   Total cost: ${total_cost:.6f}")
    
    # Show a few sample responses
    print(f"\n📝 Sample responses (first 5):")
    for i, resp in enumerate(responses[:5]):
        status = "✓" if resp.success else "✗"
        print(f"   {status} Prompt {i+1}: '{resp.text[:50]}...' " if len(resp.text) > 50 else f"   {status} Prompt {i+1}: '{resp.text}'")
    
    # Check for any errors
    errors = [r for r in responses if not r.success]
    if errors:
        print(f"\n⚠️  Errors ({len(errors)}):")
        for i, err in enumerate(errors[:3]):
            print(f"   {i+1}. {err.error}")
    
    return successful == num_requests


def main():
    print("\n🧪 LLMProvider Test Suite")
    print("="*60)
    
    # Show config
    test_config_values()
    
    # Run tests
    results = []
    
    try:
        results.append(("Basic Generation", test_basic_generation()))
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        results.append(("Basic Generation", False))
    
    try:
        results.append(("System Prompt", test_with_system_prompt()))
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        results.append(("System Prompt", False))
    
    try:
        # Run batch test with 100 requests and 10 parallel workers
        results.append(("Batch Generation (100 requests)", test_batch_generation(num_requests=100, max_workers=10)))
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Batch Generation (100 requests)", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'✅ All tests passed!' if all_passed else '❌ Some tests failed'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())


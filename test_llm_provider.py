#!/usr/bin/env python3
"""
Test script for the unified LLMProvider.
Tests text generation and token tracking.
"""
import sys
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


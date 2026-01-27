#!/usr/bin/env python3
"""
Quick test to verify the google-genai migration works.
Tests both basic generation and file upload functionality.
"""
import sys
sys.path.insert(0, '.')

from src.LLMProvider import LLMProvider
from src.utils.file_manager import GeminiFileManager

def test_basic_generation():
    """Test basic text generation without files."""
    print("\n" + "="*80)
    print("TEST 1: Basic Text Generation")
    print("="*80)
    
    provider = LLMProvider(provider="gemini", model="gemini-2.5-flash")
    print(f"✓ Provider initialized: {provider}")
    
    response = provider.generate(
        prompt="What is 2+2? Answer in one word.",
        system_prompt="You are a helpful assistant.",
        temperature=0.0,
        max_tokens=1000
    )
    
    print(f"✓ Response: {response.text}")
    print(f"✓ Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"✓ Cost: ${response.cost:.6f}")
    print(f"✓ Success: {response.success}")
    
    if not response.success:
        print(f"❌ Error: {response.error}")
    
    assert response.success, f"Response should be successful. Error: {response.error}"
    assert len(response.text) > 0, "Response should have text"
    
    print("\n✅ Basic generation test PASSED!")
    return True


def test_file_manager():
    """Test file manager initialization and methods."""
    print("\n" + "="*80)
    print("TEST 2: File Manager")
    print("="*80)
    
    file_manager = GeminiFileManager()
    print(f"✓ File Manager initialized")
    print(f"✓ Client type: {type(file_manager.client)}")
    
    # Check that client has expected methods
    assert hasattr(file_manager.client, 'files'), "Client should have files attribute"
    assert hasattr(file_manager.client.files, 'upload'), "Client should have upload method"
    assert hasattr(file_manager.client.files, 'get'), "Client should have get method"
    assert hasattr(file_manager.client.files, 'delete'), "Client should have delete method"
    
    print("✓ Client has all required methods")
    print("\n✅ File manager test PASSED!")
    return True


def test_provider_client_type():
    """Verify provider has correct client type."""
    print("\n" + "="*80)
    print("TEST 3: Provider Client Type")
    print("="*80)
    
    provider = LLMProvider(provider="gemini", model="gemini-2.5-flash")
    
    print(f"✓ Client type: {type(provider._client)}")
    print(f"✓ Has models attribute: {hasattr(provider._client, 'models')}")
    
    assert hasattr(provider._client, 'models'), "Client should have models attribute"
    
    print("\n✅ Provider client type test PASSED!")
    return True


def main():
    """Run all tests."""
    print("\n🧪 Google GenAI Migration Test Suite")
    print("="*80)
    
    results = []
    
    try:
        results.append(("Basic Generation", test_basic_generation()))
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Basic Generation", False))
    
    try:
        results.append(("File Manager", test_file_manager()))
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("File Manager", False))
    
    try:
        results.append(("Provider Client Type", test_provider_client_type()))
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Provider Client Type", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED! Migration successful!")
        print("="*80)
        print("\nYou can now:")
        print("1. Test context generation with a real PDF")
        print("2. Run the full extraction pipeline")
        print("3. Verify extraction guide generation")
    else:
        print("\n" + "="*80)
        print("❌ SOME TESTS FAILED - Check errors above")
        print("="*80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

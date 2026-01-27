#!/usr/bin/env python3
"""
Unit tests for Gemini system_instruction implementation.
Tests that system instructions are properly set and used.
"""
import sys
sys.path.insert(0, '.')

from src.LLMProvider import LLMProvider


def test_gemini_with_system_instruction():
    """
    Test that Gemini properly uses system_instruction.
    
    The system instruction should guide the model's behavior.
    We test this by giving a system instruction that affects the response format.
    """
    print("\n" + "="*80)
    print("TEST: Gemini with System Instruction")
    print("="*80)
    
    provider = LLMProvider(provider="gemini", model="gemini-2.5-flash")
    print(f"Provider: {provider}")
    
    # Test 1: With system instruction for JSON format
    print("\n--- Test 1: System instruction for JSON output ---")
    response = provider.generate(
        prompt="What is 2 + 2?",
        system_prompt="You are a calculator API. Always respond with ONLY valid JSON in this format: {\"result\": <number>}. No other text.",
        temperature=0.0,
        max_tokens=100
    )
    
    print(f"Success: {response.success}")
    print(f"Response: {response.text}")
    print(f"Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"Cost: ${response.cost:.6f}")
    
    # Verify it's JSON-like (should contain "result")
    assert response.success, "Response should be successful"
    assert "result" in response.text.lower() or "{" in response.text, \
        "Response should contain JSON structure"
    
    # Test 2: Different system instruction - verbose explanation
    print("\n--- Test 2: System instruction for verbose explanation ---")
    response2 = provider.generate(
        prompt="What is 2 + 2?",
        system_prompt="You are a patient math teacher. Always explain your answers step by step with detailed reasoning.",
        temperature=0.0,
        max_tokens=200
    )
    
    print(f"Success: {response2.success}")
    print(f"Response: {response2.text[:200]}...")  # First 200 chars
    print(f"Tokens: {response2.input_tokens} in / {response2.output_tokens} out")
    print(f"Cost: ${response2.cost:.6f}")
    
    assert response2.success, "Response should be successful"
    # This one should be longer and more explanatory
    assert len(response2.text) > len(response.text), \
        "Verbose response should be longer than JSON response"
    
    # Test 3: No system instruction (baseline)
    print("\n--- Test 3: No system instruction (baseline) ---")
    response3 = provider.generate(
        prompt="What is 2 + 2?",
        system_prompt=None,
        temperature=0.0,
        max_tokens=100
    )
    
    print(f"Success: {response3.success}")
    print(f"Response: {response3.text}")
    print(f"Tokens: {response3.input_tokens} in / {response3.output_tokens} out")
    print(f"Cost: ${response3.cost:.6f}")
    
    assert response3.success, "Response should be successful"
    
    print("\n" + "="*80)
    print("✅ All tests passed! System instruction is working correctly.")
    print("="*80)
    
    return True


def test_clinical_trial_context():
    """
    Test with a clinical trial extraction scenario.
    This mimics the actual use case for context generation.
    """
    print("\n" + "="*80)
    print("TEST: Clinical Trial Context System Instruction")
    print("="*80)
    
    provider = LLMProvider(provider="gemini", model="gemini-2.5-flash")
    
    # Simulate extraction guide as system instruction
    system_instruction = """You are a clinical trial data extractor.

TRIAL CONTEXT:
- Trial: ARASENS (NCT02799602)
- Treatment Arm: Darolutamide + ADT + Docetaxel (n=651)
- Control Arm: Placebo + ADT + Docetaxel (n=654)

TERMINOLOGY:
- "Synchronous metastases" = "de novo metastatic" = "M1 at diagnosis"
- "High volume" = "CHAARTED high-volume disease"

RULES:
- Always return valid JSON
- Use exact terminology from trial
- If uncertain, return null
"""
    
    prompt = """Extract the following information:
- What is the treatment arm called?
- What does "de novo metastatic" mean in this trial?

Format as JSON: {"treatment_arm": "...", "de_novo_meaning": "..."}"""
    
    response = provider.generate(
        prompt=prompt,
        system_prompt=system_instruction,
        temperature=0.0,
        max_tokens=300
    )
    
    print(f"Success: {response.success}")
    print(f"Response:\n{response.text}")
    print(f"Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"Cost: ${response.cost:.6f}")
    
    assert response.success, "Response should be successful"
    # Should reference the trial context
    assert "darolutamide" in response.text.lower() or "arasens" in response.text.lower(), \
        "Response should use trial context"
    
    print("\n✅ Clinical trial context test passed!")
    
    return True


def test_context_generation_prompt():
    """
    Test the actual context generation prompt that will be used in production.
    """
    print("\n" + "="*80)
    print("TEST: Context Generation Prompt Format")
    print("="*80)
    
    provider = LLMProvider(provider="gemini", model="gemini-2.5-flash")
    
    # Simplified version of the actual context generation prompt
    context_gen_prompt = """Generate a structured extraction guide for a clinical trial.

Analyze this trial information and output JSON:
{
  "trial_identity": {
    "name": "...",
    "nct_id": "..."
  },
  "arm_mapping": {
    "treatment_arm": {"synonyms": ["..."]},
    "control_arm": {"synonyms": ["..."]}
  }
}

Trial info:
This is the ARASENS trial (NCT02799602). It compares darolutamide + ADT + docetaxel 
versus placebo + ADT + docetaxel in metastatic castration-sensitive prostate cancer."""
    
    response = provider.generate(
        prompt=context_gen_prompt,
        system_prompt="You are a clinical trial analyzer. Generate comprehensive extraction guides in JSON format.",
        temperature=0.0,
        max_tokens=500
    )
    
    print(f"Success: {response.success}")
    print(f"Response:\n{response.text[:400]}...")  # First 400 chars
    print(f"Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"Cost: ${response.cost:.6f}")
    
    assert response.success, "Response should be successful"
    # Should contain JSON structure
    assert "{" in response.text and "}" in response.text, \
        "Response should contain JSON"
    
    print("\n✅ Context generation prompt test passed!")
    
    return True


def main():
    """Run all tests."""
    print("\n🧪 Gemini System Instruction Test Suite")
    print("="*80)
    
    results = []
    
    try:
        results.append(("Basic System Instruction", test_gemini_with_system_instruction()))
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Basic System Instruction", False))
    
    try:
        results.append(("Clinical Trial Context", test_clinical_trial_context()))
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Clinical Trial Context", False))
    
    try:
        results.append(("Context Generation Prompt", test_context_generation_prompt()))
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Context Generation Prompt", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'✅ All tests passed!' if all_passed else '❌ Some tests failed'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

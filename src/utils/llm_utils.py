# src/utils/llm_utils.py
"""
LLM utilities for evaluation and general text generation.
Uses unified LLMProvider for all inference.
"""
from pathlib import Path
from ..config.config import EVALUATION_PROVIDER, EVALUATION_MODEL
from ..LLMProvider import LLMProvider
from ..utils.logging_utils import setup_logger

logger = setup_logger("llm_utils")

# Lazy-loaded evaluation provider
_evaluation_provider = None


def _get_evaluation_provider():
    """Get or initialize the evaluation LLM provider."""
    global _evaluation_provider
    if _evaluation_provider is None:
        _evaluation_provider = LLMProvider(provider=EVALUATION_PROVIDER, model=EVALUATION_MODEL)
        logger.info(f"Initialized evaluation provider: {EVALUATION_PROVIDER}/{EVALUATION_MODEL}")
    return _evaluation_provider


def ask_llm_text(prompt_path, text, model_type=None):
    """
    Send text prompt to LLM and get response.
    
    Uses EVALUATION_PROVIDER and EVALUATION_MODEL from config.
    
    Args:
        prompt_path: Path to prompt template file
        text: Text content to append to prompt
        model_type: Deprecated, kept for backward compatibility (uses config instead)
    
    Returns:
        tuple: (response_text, input_tokens, output_tokens)
               Returns (None, 0, 0) on failure
    """
    # Load prompt template
    prompt_template = Path(prompt_path).read_text(encoding="utf-8")
    full_prompt = f"{prompt_template}\n\n{text}"
    
    provider = _get_evaluation_provider()
    
    response = provider.generate(
        prompt=full_prompt,
        system_prompt="You are an expert evaluator for clinical trial data extraction.",
        temperature=0.0,
    )
    
    if response.success:
        return response.text, response.input_tokens, response.output_tokens
    else:
        logger.error(f"LLM call failed ({response.provider}/{response.model}): {response.error}")
        return None, 0, 0


def generate_text(prompt: str, system_prompt: str = None, temperature: float = 0.0):
    """
    General-purpose text generation using evaluation provider.
    
    Args:
        prompt: User prompt
        system_prompt: Optional system instruction
        temperature: Sampling temperature
    
    Returns:
        tuple: (response_text, input_tokens, output_tokens)
    """
    provider = _get_evaluation_provider()
    
    response = provider.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
    )
    
    if response.success:
        return response.text, response.input_tokens, response.output_tokens
    else:
        logger.error(f"LLM call failed ({response.provider}/{response.model}): {response.error}")
        return None, 0, 0

# src/model_handling/llm_extraction.py
"""
LLM-based extraction for clinical trial data.
Uses unified LLMProvider for all inference.
"""
import json
from datetime import datetime
from pathlib import Path
from ..config.config import EXTRACTION_PROVIDER, EXTRACTION_MODEL
from ..LLMProvider import LLMProvider
from ..utils.logging_utils import setup_logger

logger = setup_logger("llm_extraction")

# Lazy-loaded extraction provider
_extraction_provider = None


def _get_extraction_provider():
    """Get or initialize the extraction LLM provider."""
    global _extraction_provider
    if _extraction_provider is None:
        _extraction_provider = LLMProvider(provider=EXTRACTION_PROVIDER, model=EXTRACTION_MODEL)
        logger.info(f"Initialized extraction provider: {EXTRACTION_PROVIDER}/{EXTRACTION_MODEL}")
    return _extraction_provider


def build_extraction_prompt(group):
    """Build extraction prompt for a group of columns."""
    columns_str = "\n".join([
        f'- {col["Column Name"]}: {col["Definition"]}'
        for col in group
    ])

    return f"""
You are an expert at extracting structured data from clinical trial documents.
Extract values for these columns ONLY if explicitly present.

Columns:
{columns_str}

Rules:
- Return ONLY valid JSON.
- If value is missing or uncertain → use null.
- Include short evidence quote when value is found.
- For each column, include brief reasoning (1 sentence) explaining the value or why null.

Output format:
{{
  "Column Name 1": {{"value": "extracted value" or null, "evidence": "short quote" or null, "reasoning": "brief reason"}},
  "Column Name 2": {{"value": null, "evidence": null, "reasoning": "brief reason"}}
}}

Content:
"""


SYSTEM_PROMPT = "You are a precise medical data extractor. Never hallucinate. Always explain your reasoning."


def extract_group_from_chunk(chunk, group, context_text=None, metrics_dir: Path = None):
    """
    Extract values from a chunk using unified LLMProvider.
    
    Args:
        chunk: Document chunk dict with 'type' and 'content'
        group: List of column definitions to extract
        context_text: Optional context from first pages
        metrics_dir: Directory for logging LLM calls
    
    Returns:
        tuple: (extracted_dict, input_tokens, output_tokens)
    """
    llm_logs_dir = metrics_dir / "llm_logs" if metrics_dir else Path("llm_logs")
    llm_logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = llm_logs_dir / "llm_calls.jsonl"

    provider = _get_extraction_provider()
    prompt = None
    raw_response = None
    
    try:
        # Build content based on chunk type
        if chunk["type"] == "text":
            content_text = chunk["content"]
        elif chunk["type"] in ["table", "figure"]:
            content_text = chunk.get("table_content") or chunk.get("figure_content", "")
        elif chunk["type"] == "image":
            content_text = "[Image content - extracting from surrounding text]"
        else:
            content_text = ""

        if not content_text.strip():
            fallback = {col["Column Name"]: {"value": None, "evidence": None, "reasoning": None} for col in group}
            return fallback, 0, 0

        # Build full prompt
        prompt = ""
        if context_text:
            prompt += f"CONTEXT (from first 2 pages):\n{context_text}\n\n"
        prompt += build_extraction_prompt(group) + content_text

        # Call unified provider
        response = provider.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.0,
            max_tokens=1500
        )

        if not response.success:
            raise Exception(response.error)

        raw_response = response.text

        # Clean code blocks
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:]
        if raw_response.startswith("```"):
            raw_response = raw_response[3:]
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3]
        raw_response = raw_response.strip()

        extracted = json.loads(raw_response)

        # Validate and normalize
        result = {}
        for col in group:
            col_name = col["Column Name"]
            entry = extracted.get(col_name, {"value": None, "evidence": None, "reasoning": None})
            if not isinstance(entry, dict):
                entry = {"value": str(entry) if entry else None, "evidence": None, "reasoning": None}
            if "value" not in entry:
                entry["value"] = None
            if "evidence" not in entry:
                entry["evidence"] = None
            if "reasoning" not in entry:
                entry["reasoning"] = None
            result[col_name] = entry

        # Log the call
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": response.provider,
            "model": response.model,
            "prompt": prompt,
            "response": raw_response,
            "extracted": result,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost": response.cost,
            "error": None
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        return result, response.input_tokens, response.output_tokens

    except json.JSONDecodeError as e:
        error = f"JSON parse failed: {e}"
        logger.warning(error)
        fallback = {col["Column Name"]: {"value": None, "evidence": None, "reasoning": None} for col in group}
        _log_error(log_file, provider, prompt, raw_response, error, 
                   getattr(response, 'input_tokens', 0) if 'response' in dir() else 0,
                   getattr(response, 'output_tokens', 0) if 'response' in dir() else 0)
        return fallback, getattr(response, 'input_tokens', 0) if 'response' in dir() else 0, getattr(response, 'output_tokens', 0) if 'response' in dir() else 0
    
    except Exception as e:
        error = f"Extraction failed: {e}"
        logger.error(error)
        fallback = {col["Column Name"]: {"value": None, "evidence": None, "reasoning": None} for col in group}
        _log_error(log_file, provider, prompt, raw_response, error, 0, 0)
        return fallback, 0, 0


def _log_error(log_file, provider, prompt, raw_response, error, input_tokens=0, output_tokens=0):
    """Helper to log errors."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider.provider if provider else None,
        "model": provider.model if provider else None,
        "prompt": prompt,
        "response": raw_response,
        "extracted": None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": 0,
        "error": error
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Don't fail on logging errors


def save_cost_metrics(file_path, metrics):
    """Save cost metrics to file from metrics dict."""
    with open(file_path, "w") as f:
        for k, v in metrics.items():
            f.write(f"{k}: {v}\n")

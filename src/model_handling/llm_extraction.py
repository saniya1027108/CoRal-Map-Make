# src/extraction/llm_extraction.py
import json
import base64
import openai
from ..config.config import OPENAI_API_KEY, OPEN_AI_MODEL, OPENAI_TEMPERATURE, COST_PER_1K_INPUT, COST_PER_1K_OUTPUT
from ..utils.logging_utils import setup_logger

logger = setup_logger("llm_extraction")

# Configure OpenAI
openai.api_key = OPENAI_API_KEY


def build_extraction_prompt(group):
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

Output format:
{{
  "Column Name 1": {{"value": "extracted value", "evidence": "short quote"}},
  "Column Name 2": {{"value": null, "evidence": null}}
}}

Content:
"""


def extract_group_from_chunk(chunk, group, context_text = None):
    """
    Extract values using OpenAI (gpt-4o-mini or gpt-4o)
    
    Returns: (extracted_dict, input_tokens, output_tokens)
    """
    try:
        # Build content based on chunk type
        if chunk["type"] == "text":
            content_text = chunk["content"]
        elif chunk["type"] in ["table", "figure"]:
            content_text = chunk.get("table_content") or chunk.get("figure_content", "")
        elif chunk["type"] == "image":
            # Optional: describe image via Gemini first? Or skip
            content_text = "[Image content - extracting from surrounding text]"
        else:
            content_text = ""

        if not content_text.strip():
            fallback = {col["Column Name"]: {"value": None, "evidence": None} for col in group}
            return fallback, 0, 0

        prompt = ""
        if context_text:
            prompt += f"CONTEXT (from first 2 pages):\n{context_text}\n\n"
        prompt += build_extraction_prompt(group) + content_text

        response = openai.chat.completions.create(
            model=OPEN_AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise medical data extractor. Never hallucinate."},
                {"role": "user", "content": prompt}
            ],
            temperature=OPENAI_TEMPERATURE,
            max_tokens=1500
        )

        # Get usage
        usage = getattr(response, "usage", None)
        if usage:
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
        else:
            input_tokens = 0
            output_tokens = 0

        raw = response.choices[0].message.content.strip()

        # Clean code blocks
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        extracted = json.loads(raw)

        # Validate and normalize
        result = {}
        for col in group:
            col_name = col["Column Name"]
            entry = extracted.get(col_name, {"value": None, "evidence": None})
            if not isinstance(entry, dict):
                entry = {"value": str(entry) if entry else None, "evidence": None}
            if "value" not in entry:
                entry["value"] = None
            if "evidence" not in entry:
                entry["evidence"] = None
            result[col_name] = entry

        return result, input_tokens, output_tokens

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed: {e}\nRaw output: {raw}")
        fallback = {col["Column Name"]: {"value": None, "evidence": None} for col in group}
        return fallback, input_tokens, output_tokens  # Usage still counted even on parse error
    except Exception as e:
        logger.error(f"OpenAI extraction failed: {e}")
        fallback = {col["Column Name"]: {"value": None, "evidence": None} for col in group}
        return fallback, 0, 0


def save_cost_metrics(file_path, metrics):
    """
    Save cost metrics to file from metrics dict.
    """
    with open(file_path, "w") as f:
        for k, v in metrics.items():
            f.write(f"{k}: {v}\n")
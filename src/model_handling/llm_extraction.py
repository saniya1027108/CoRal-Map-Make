# src/extraction/llm_extraction.py
import json
import base64
import openai
from ..config.config import OPENAI_API_KEY, OPEN_AI_MODEL, OPENAI_TEMPERATURE
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
            return {col["Column Name"]: {"value": None, "evidence": None} for col in group}

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

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed: {e}\nRaw output: {raw}")
    except Exception as e:
        logger.error(f"Open ReasonableAI extraction failed: {e}")

    # Fallback: all null
    return {col["Column Name"]: {"value": None, "evidence": None} for col in group}
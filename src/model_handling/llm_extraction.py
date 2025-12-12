# src/model_handling/llm_extraction.py
# (Updated with LLM logging, reasoning in output, and passing log dir)
import json
from datetime import datetime
from pathlib import Path
from ..config.config import OPENAI_API_KEY, OPEN_AI_MODEL, OPENAI_TEMPERATURE, COST_PER_1K_INPUT, COST_PER_1K_OUTPUT, EXTRACTION_MODEL, GROQ_MODEL_NAME, NOVITA_MODEL_NAME, GROQ_API_KEY, NOVITA_API_KEY
from ..utils.logging_utils import setup_logger

logger = setup_logger("llm_extraction")

# Configure OpenAI
from groq import Groq
import openai
from openai import OpenAI
# OpenAI client (official)
openai.api_key = OPENAI_API_KEY

# Groq client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Novita client (OpenAI-compatible API)
novita_client = OpenAI(
    base_url="https://api.novita.ai/v3/openai",
    api_key=NOVITA_API_KEY
) if NOVITA_API_KEY else None

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
- For each column, include brief reasoning (1 sentence) explaining the value or why null.

Output format:
{{
  "Column Name 1": {{"value": "extracted value" or null, "evidence": "short quote" or null, "reasoning": "brief reason"}},
  "Column Name 2": {{"value": null, "evidence": null, "reasoning": "brief reason"}}
}}

Content:
"""


def extract_group_from_chunk(chunk, group, context_text = None, metrics_dir: Path = None):
    """
    Extract values using OpenAI (gpt-4o-mini or gpt-4o). Logs each call with reasoning.
    
    Returns: (extracted_dict, input_tokens, output_tokens)
    """
    llm_logs_dir = metrics_dir / "llm_logs" if metrics_dir else Path("llm_logs")
    llm_logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = llm_logs_dir / "llm_calls.jsonl"

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
            fallback = {col["Column Name"]: {"value": None, "evidence": None, "reasoning": None} for col in group}
            return fallback, 0, 0

        prompt = ""
        if context_text:
            prompt += f"CONTEXT (from first 2 pages):\n{context_text}\n\n"
        prompt += build_extraction_prompt(group) + content_text

        model_used = None
        raw_response = None
        input_tokens = 0
        output_tokens = 0
        error = None

        if EXTRACTION_MODEL == "groq" and groq_client:
            model_used = GROQ_MODEL_NAME
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a precise medical data extractor. Never hallucinate. Always explain reasoning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            raw_response = response.choices[0].message.content.strip()
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

        elif EXTRACTION_MODEL == "novita" and novita_client:
            model_used = NOVITA_MODEL_NAME
            response = novita_client.chat.completions.create(
                model=NOVITA_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a precise medical data extractor. Never hallucinate. Always explain your reasoning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=1500
            )
            raw_response = response.choices[0].message.content.strip()
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

        elif EXTRACTION_MODEL == "openai":
            model_used = OPEN_AI_MODEL
            response = openai.chat.completions.create(
                model=OPEN_AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise medical data extractor. Never hallucinate. Always explain your reasoning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=OPENAI_TEMPERATURE,
                max_tokens=1500
            )
            raw_response = response.choices[0].message.content.strip()
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

        else:
            raise ValueError(f"Model {EXTRACTION_MODEL} not available or API key missing")

        # Clean code blocks
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:]
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
            "model": model_used,
            "prompt": prompt,
            "response": raw_response,
            "extracted": result,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "error": error
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        return result, input_tokens, output_tokens

    except json.JSONDecodeError as e:
        error = f"JSON parse failed: {e}"
        logger.warning(error)
        fallback = {col["Column Name"]: {"value": None, "evidence": None, "reasoning": None} for col in group}
        # Log error
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_used,
            "prompt": prompt,
            "response": raw_response,
            "extracted": None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "error": error
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        return fallback, input_tokens, output_tokens  # Usage still counted even on parse error
    except Exception as e:
        error = f"Extraction failed: {e}"
        logger.error(error)
        fallback = {col["Column Name"]: {"value": None, "evidence": None, "reasoning": None} for col in group}
        # Log error
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_used,
            "prompt": prompt,
            "response": None,
            "extracted": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "error": error
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        return fallback, 0, 0


def save_cost_metrics(file_path, metrics):
    """
    Save cost metrics to file from metrics dict.
    """
    with open(file_path, "w") as f:
        for k, v in metrics.items():
            f.write(f"{k}: {v}\n")
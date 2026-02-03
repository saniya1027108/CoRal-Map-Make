#!/usr/bin/env python3
from __future__ import annotations

"""
Run extraction using pre-generated extraction plans (V2).

Primary goal: prevent identifier drift.
- Plans must be canonical: one plan per canonical column, with column_index + exact column_name.
- Extractions must be canonical: extractions keyed by column_index, validated against the plan.

This script intentionally mirrors the original run_extraction_with_plans.py workflow, but adds:
1) Strict plan validation (indices + canonical names) before any LLM calls.
2) Structured extraction output keyed by column_index (order-independent).
3) Deterministic canonicalization: column_name is verified (or overridden) from Definitions.csv.

Usage:
  python experiment-scripts/run_extraction_with_plans_v2.py \
      --pdf "test_results/new/NCT.../NCT....pdf" \
      --chunks "test_results/new/NCT.../pdf_chunked.json"

  python experiment-scripts/run_extraction_with_plans_v2.py \
      --pdf "test_results/new/NCT.../NCT....pdf" \
      --chunks "test_results/new/NCT.../pdf_chunked.json" \
      --provider openai --model gpt-4o
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field, field_validator

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from google import genai
from google.genai import types

from src.LLMProvider.structurer import OutputStructurer, StructurerResponse
from src.table_definitions.definitions import load_definitions
from src.utils.logging_utils import setup_logger

logger = setup_logger("extraction_with_plans_v2")


# -----------------------------
# Shared helpers
# -----------------------------


def safe_stem(name: str) -> str:
    """Stable filename stem for group names (keep consistent with planning V2)."""
    return (
        name.replace(" ", "_")
        .replace("/", "_")
        .replace("|", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def call_openai_extraction_with_file_id(client: OpenAI, *, file_id: str, prompt: str, model: str) -> str:
    """Call OpenAI Responses API using a pre-uploaded PDF file_id."""
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_file", "file_id": file_id},
                ],
            }
        ],
    )
    return response.output_text.strip()


def upload_pdf_openai(client: OpenAI, pdf_path: Path) -> str:
    with open(pdf_path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="assistants")
    return uploaded.id


def delete_openai_file_safely(client: OpenAI, file_id: str) -> None:
    try:
        client.files.delete(file_id)
    except Exception:
        pass


def call_gemini_extraction(client, *, pdf_part, prompt: str, model: str) -> str:
    config = types.GenerateContentConfig(temperature=0.0, max_output_tokens=8000)
    response = client.models.generate_content(model=model, contents=[pdf_part, prompt], config=config)
    return (response.text or "").strip()


# -----------------------------
# Fallback Structurers (for when local vLLM fails)
# -----------------------------


def structure_with_openai(
    client: OpenAI,
    prompt: str,
    schema: Type[BaseModel],
    model: str = "gpt-4.1",
    max_retries: int = 3
) -> StructurerResponse:
    """
    Fallback structurer using OpenAI with JSON mode.
    Used when local vLLM structurer fails after 5 attempts.
    """
    import json
    from pydantic import ValidationError
    
    json_schema = schema.model_json_schema()
    
    system_prompt = f"""You are a JSON formatter. Convert the provided text into valid JSON matching this exact schema:

{json.dumps(json_schema, indent=2)}

Rules:
- Output ONLY valid JSON, no markdown, no explanations
- Match the schema exactly
- Use null for missing values
"""
    
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            raw_json = response.choices[0].message.content.strip()
            data_dict = json.loads(raw_json)
            validated_data = schema.model_validate(data_dict)
            
            return StructurerResponse(
                data=validated_data,
                success=True,
                attempts=attempt,
                error=None
            )
            
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == max_retries:
                return StructurerResponse(
                    data={},
                    success=False,
                    attempts=attempt,
                    error=f"Failed after {max_retries} attempts. Last error: {str(e)}"
                )
            continue
        except Exception as e:
            return StructurerResponse(
                data={},
                success=False,
                attempts=attempt,
                error=f"Unexpected error: {str(e)}"
            )
    
    return StructurerResponse(
        data={},
        success=False,
        attempts=max_retries,
        error="Max retries reached"
    )


def structure_with_gemini(
    client,
    prompt: str,
    schema: Type[BaseModel],
    model: str = "gemini-2.5-flash",
    max_retries: int = 3
) -> StructurerResponse:
    """
    Fallback structurer using Gemini with JSON schema.
    Used when local vLLM structurer fails after 5 attempts.
    """
    import json
    from pydantic import ValidationError
    
    json_schema = schema.model_json_schema()
    
    system_instruction = f"""You are a JSON formatter. Convert the provided text into valid JSON matching this exact schema:

{json.dumps(json_schema, indent=2)}

Rules:
- Output ONLY valid JSON, no markdown, no explanations
- Match the schema exactly
- Use null for missing values
"""
    
    for attempt in range(1, max_retries + 1):
        try:
            config = types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=json_schema
            )
            
            response = client.models.generate_content(
                model=model,
                contents=[system_instruction, prompt],
                config=config
            )
            
            raw_json = (response.text or "").strip()
            data_dict = json.loads(raw_json)
            validated_data = schema.model_validate(data_dict)
            
            return StructurerResponse(
                data=validated_data,
                success=True,
                attempts=attempt,
                error=None
            )
            
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == max_retries:
                return StructurerResponse(
                    data={},
                    success=False,
                    attempts=attempt,
                    error=f"Failed after {max_retries} attempts. Last error: {str(e)}"
                )
            continue
        except Exception as e:
            return StructurerResponse(
                data={},
                success=False,
                attempts=attempt,
                error=f"Unexpected error: {str(e)}"
            )
    
    return StructurerResponse(
        data={},
        success=False,
        attempts=max_retries,
        error="Max retries reached"
    )


# -----------------------------
# Plan schema (V2)
# -----------------------------


SourceType = Literal["table", "text", "figure", "not_applicable"]
Confidence = Literal["high", "medium", "low"]


class ColumnExtractionPlanV2(BaseModel):
    column_index: int
    column_name: str
    found_in_pdf: bool
    page: int
    source_type: SourceType
    confidence: Confidence
    extraction_plan: str
    column_name_raw: Optional[str] = None


class GroupExtractionPlanV2(BaseModel):
    group_name: str
    columns: List[ColumnExtractionPlanV2]


# -----------------------------
# Extraction schema (V2)
# -----------------------------


class ColumnExtractionV2(BaseModel):
    column_index: int
    column_name: str
    value: Optional[Union[str, int, float]] = None
    evidence: Optional[str] = None
    page: str
    # Be permissive: models sometimes return "medium-high", "High", etc.
    confidence: str = "low"
    column_name_raw: Optional[str] = None

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        if isinstance(v, str):
            s = v.strip().lower()
            if s in {"high", "h", "certain", "very_high", "veryhigh"}:
                return "high"
            if s in {"medium", "med", "m", "moderate"}:
                return "medium"
            if s in {"low", "l", "uncertain", "unsure"}:
                return "low"
            # Handle compound labels like "medium-high"
            if "high" in s:
                return "high"
            if "medium" in s:
                return "medium"
            if "low" in s:
                return "low"
            return "low"
        return v


class GroupExtractionV2(BaseModel):
    group_name: str
    extractions: List[ColumnExtractionV2]


# -----------------------------
# Canonicalization / validation
# -----------------------------


def expected_columns_for_group(groups_dict: Dict[str, list], group_name: str) -> List[str]:
    if group_name not in groups_dict:
        raise KeyError(f"Group not found in definitions: {group_name}")
    return [c["Column Name"] for c in groups_dict[group_name]]


def validate_and_normalize_plan(
    *,
    plan: GroupExtractionPlanV2,
    expected_columns: List[str],
    name_policy: Literal["strict", "override"] = "strict",
) -> GroupExtractionPlanV2:
    n = len(expected_columns)

    by_idx: Dict[int, ColumnExtractionPlanV2] = {}
    dupes = []
    out_of_range = []
    for item in plan.columns:
        idx = item.column_index
        if idx in by_idx:
            dupes.append(idx)
            continue
        if idx < 1 or idx > n:
            out_of_range.append(idx)
            continue
        by_idx[idx] = item

    missing = [i for i in range(1, n + 1) if i not in by_idx]
    if dupes or out_of_range or missing:
        raise ValueError(
            f"Invalid plan indices for group '{plan.group_name}': "
            f"dupes={sorted(set(dupes))}, out_of_range={sorted(set(out_of_range))}, missing_count={len(missing)}"
        )

    normalized: List[ColumnExtractionPlanV2] = []
    mismatches = []

    for idx in range(1, n + 1):
        item = by_idx[idx]
        canonical = expected_columns[idx - 1]
        if item.column_name != canonical:
            mismatches.append((idx, item.column_name, canonical))
            if name_policy == "override":
                item.column_name_raw = item.column_name
                item.column_name = canonical
        if not item.found_in_pdf:
            item.page = -1
            item.source_type = "not_applicable"
        normalized.append(item)

    if mismatches and name_policy == "strict":
        preview = "; ".join([f"#{i}: '{got}' != '{want}'" for i, got, want in mismatches[:5]])
        raise ValueError(f"Plan column_name mismatch(es) for group '{plan.group_name}': {preview}")

    plan.columns = normalized
    return plan


def validate_and_normalize_extraction(
    *,
    extraction: GroupExtractionV2,
    expected_columns: List[str],
    expected_indices: List[int],
    name_policy: Literal["strict", "override"] = "strict",
) -> GroupExtractionV2:
    expected_indices_set = set(expected_indices)
    by_idx: Dict[int, ColumnExtractionV2] = {}
    dupes = []
    extras = []
    for item in extraction.extractions:
        idx = item.column_index
        if idx in by_idx:
            dupes.append(idx)
            continue
        if idx not in expected_indices_set:
            extras.append(idx)
            continue
        by_idx[idx] = item

    missing = [i for i in expected_indices if i not in by_idx]
    # Soft behavior: do not crash the run if the structurer missed items or emitted duplicates/extras.
    # We'll keep the first instance of each index, ignore extras, and fill missing indices with null results.
    if dupes or extras or missing:
        logger.warning(
            f"[Soft-validate] Group '{extraction.group_name}': "
            f"dupes={sorted(set(dupes))}, extras={sorted(set(extras))}, missing_count={len(missing)}"
        )

    normalized: List[ColumnExtractionV2] = []
    mismatches = []
    for idx in expected_indices:
        canonical = expected_columns[idx - 1]
        item = by_idx.get(idx)
        if item is None:
            normalized.append(
                ColumnExtractionV2(
                    column_index=idx,
                    column_name=canonical,
                    value=None,
                    evidence=None,
                    page="",
                    confidence="low",
                )
            )
            continue
        if item.column_name != canonical:
            mismatches.append((idx, item.column_name, canonical))
            if name_policy == "override":
                item.column_name_raw = item.column_name
                item.column_name = canonical
        normalized.append(item)

    # Column name mismatch is important, but don't crash the entire run.
    if mismatches and name_policy == "strict":
        preview = "; ".join([f"#{i}: '{got}' != '{want}'" for i, got, want in mismatches[:5]])
        logger.warning(
            f"[Soft-validate] Extraction column_name mismatch(es) for group '{extraction.group_name}': {preview}"
        )

    extraction.extractions = normalized
    return extraction


# -----------------------------
# Chunk selection (legacy: page + type)
# -----------------------------


def find_relevant_chunks(col_plans: List[ColumnExtractionPlanV2], chunks: list) -> list:
    """Find chunks relevant to the plan. Matches by source_type and page."""
    relevant = []
    seen_chunk_ids = set()

    for col_plan in col_plans:
        if not col_plan.found_in_pdf:
            continue

        source_type = (col_plan.source_type or "").lower()
        target_page = col_plan.page
        if target_page == -1:
            continue

        for i, chunk in enumerate(chunks):
            chunk_id = f"{i}_{chunk.get('type', 'text')}"
            if chunk_id in seen_chunk_ids:
                continue

            chunk_type = (chunk.get("type", "text") or "text").lower()
            chunk_page = chunk.get("page")

            if chunk_type != source_type:
                continue

            page_match = False
            if isinstance(chunk_page, int):
                page_match = chunk_page == target_page
            elif isinstance(chunk_page, str):
                if "-" in chunk_page:
                    try:
                        start_s, end_s = chunk_page.split("-", 1)
                        start, end = int(start_s), int(end_s)
                        page_match = start <= target_page <= end
                    except Exception:
                        page_match = False
                else:
                    try:
                        page_match = int(chunk_page) == target_page
                    except Exception:
                        page_match = False

            if page_match:
                chunk_data = {
                    "chunk_id": i,
                    "type": chunk_type,
                    "page": chunk_page,
                    "content": (chunk.get("content", "") or "")[:1000],
                }
                
                # For table chunks, include the actual structured table content
                if chunk_type == "table" and "table_content" in chunk:
                    chunk_data["table_content"] = chunk.get("table_content", "")
                
                relevant.append(chunk_data)
                seen_chunk_ids.add(chunk_id)

    return relevant


def format_chunks(chunks: list) -> str:
    if not chunks:
        return "No relevant chunks found."
    parts = []
    for c in chunks:
        chunk_id = c["chunk_id"]
        chunk_type = c["type"].upper()
        page = c["page"]
        
        # For table chunks, use the structured table_content if available
        if chunk_type == "TABLE" and "table_content" in c and c["table_content"]:
            table_content = c["table_content"]
            # Include summary + full table (limit to 3000 chars for very large tables)
            content_summary = c["content"][:300].replace("\n", " ")
            parts.append(
                f"--- Chunk {chunk_id} ({chunk_type} on page {page}) ---\n"
                f"Summary: {content_summary}...\n\n"
                f"Structured Table:\n{table_content[:3000]}"
            )
        else:
            # For text/figure chunks, use content preview
            content_preview = c["content"][:500].replace("\n", " ")
            parts.append(f"--- Chunk {chunk_id} ({chunk_type} on page {page}) ---\n{content_preview}...")
    
    return "\n\n".join(parts)


def format_columns_for_prompt(
    found_cols: List[ColumnExtractionPlanV2],
    groups_dict: Dict[str, list],
    group_name: str
) -> str:
    """Format columns for extraction prompt, including definitions from Definitions.csv"""
    out = []
    
    # Build a lookup for column name -> definition
    column_definitions = {}
    if group_name in groups_dict:
        for col_info in groups_dict[group_name]:
            column_definitions[col_info["Column Name"]] = col_info["Definition"]
    
    for plan in found_cols:
        definition = column_definitions.get(plan.column_name, "No definition available")
        out.append(
            "\n".join(
                [
                    f'- Column index {plan.column_index}: "{plan.column_name}"',
                    f"  Definition: {definition}",
                    f"  Expected Location: Page {plan.page} | {plan.source_type}",
                    f"  Planner Confidence: {plan.confidence}",
                    "  Extraction Instructions:",
                    f"  {plan.extraction_plan}",
                ]
            )
        )
    return "\n\n".join(out)


# -----------------------------
# Plan loading
# -----------------------------


def load_plans_v2(plans_dir: Path) -> Dict[str, GroupExtractionPlanV2]:
    """Load plans from compiled file or fallback to individual files in logs."""
    plans: Dict[str, GroupExtractionPlanV2] = {}
    
    # First, try to load from compiled plans file
    compiled_path = plans_dir / "plans_all_columns.json"
    if compiled_path.exists():
        logger.info(f"Loading plans from compiled file: {compiled_path.name}")
        data = json.loads(compiled_path.read_text(encoding="utf-8"))
        plan_list = data.get("plans", [])
        logger.info(f"Found {len(plan_list)} groups in compiled plans")
        
        for plan_data in plan_list:
            plan = GroupExtractionPlanV2.model_validate(plan_data)
            plans[plan.group_name] = plan
        
        return plans
    
    # Fallback: load from individual files in logs subdirectory
    logs_dir = plans_dir / "logs"
    if logs_dir.exists():
        plan_files = list(logs_dir.glob("*_plan.json"))
        logger.info(f"Loading {len(plan_files)} plan files from: {logs_dir}")
        
        for p in plan_files:
            data = json.loads(p.read_text(encoding="utf-8"))
            plan = GroupExtractionPlanV2.model_validate(data)
            plans[plan.group_name] = plan
        
        return plans
    
    # No plans found
    logger.warning(f"No plans found in {plans_dir} or {plans_dir}/logs")
    return plans


# -----------------------------
# Group extraction
# -----------------------------


def extract_group_v2(
    *,
    group_name: str,
    plan: GroupExtractionPlanV2,
    expected_columns: List[str],
    pdf_path: Path,
    chunks: list,
    provider: Literal["openai", "gemini"],
    model: str,
    openai_client: Optional[OpenAI],
    openai_file_id: Optional[str],
    gemini_client,
    gemini_pdf_part,
    structurer: OutputStructurer,
    output_dir: Path,
    name_policy: Literal["strict", "override"],
    groups_dict: Dict[str, list],
) -> GroupExtractionV2:
    # Create logs subdirectory for column-wise extraction outputs
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Only extract columns the planner marked as present.
    found_cols = [c for c in plan.columns if c.found_in_pdf]
    if not found_cols:
        return GroupExtractionV2(group_name=group_name, extractions=[])

    relevant_chunks = find_relevant_chunks(found_cols, chunks)

    columns_block = format_columns_for_prompt(found_cols, groups_dict, group_name)
    chunks_block = format_chunks(relevant_chunks)

    prompt = f"""You are extracting clinical trial data from a research paper.

TASK:
Extract values for the following canonical columns. Each column has a canonical index and a canonical name.

⚠️ CRITICAL: You MUST use the EXACT column names as listed below.
Do NOT paraphrase, abbreviate, or modify names in ANY way.
Character-for-character match is REQUIRED (including spaces, punctuation, pipes |, parentheses).

COLUMNS TO EXTRACT (index + name are canonical; copy these EXACT names in your output):
{columns_block}

RELEVANT PRE-EXTRACTED CHUNKS (filtered by planner page+type):
{chunks_block}

GUIDELINES:
- For each listed column, extract a value if explicitly present. If not found, set value=null.
- Provide evidence as an exact quote.
- Provide page number(s).
- Provide confidence high/medium/low.
- When referencing columns, use the EXACT names from the list above (copy-paste them).

Output format (free-form is OK), but for EACH column include a line like:
Column index <N>: "<Exact Column Name from list above>"
Value: <extracted value or null>
Evidence: "<exact quote>"
Page: <page number>
Confidence: <high/medium/low>
"""

    if provider == "openai":
        if openai_client is None or not openai_file_id:
            raise ValueError("OpenAI provider requires openai_client and openai_file_id")
        free_form = call_openai_extraction_with_file_id(
            openai_client, file_id=openai_file_id, prompt=prompt, model=model
        )
    elif provider == "gemini":
        free_form = call_gemini_extraction(gemini_client, pdf_part=gemini_pdf_part, prompt=prompt, model=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    # Save raw output to logs subdirectory with INPUT and OUTPUT sections
    stem = safe_stem(group_name)
    raw_path = logs_dir / f"{stem}_{provider}_raw.txt"
    raw_content = f"""{'='*80}
INPUT PROMPT
{'='*80}

{prompt}

{'='*80}
OUTPUT RESPONSE
{'='*80}

{free_form}
"""
    raw_path.write_text(raw_content, encoding="utf-8")

    # Ask local structurer for strict JSON keyed by column_index.
    expected = [(c.column_index, c.column_name) for c in found_cols]
    expected_block = "\n".join([f"{idx}. {name}" for idx, name in expected])
    expected_indices = [idx for idx, _ in expected]

    structuring_prompt = f"""Convert the following free-form extraction into STRICT JSON.

Group name: \"{group_name}\"

EXPECTED columns to output (ONLY these; do not add any others):
{expected_block}

⚠️⚠️⚠️ CRITICAL REQUIREMENT ⚠️⚠️⚠️
For each item, the column_name field MUST be an EXACT CHARACTER-FOR-CHARACTER match with the EXPECTED column name for that column_index.
This means:
- Same capitalization (e.g., "Median" not "median")
- Same spacing (e.g., "Age (years)" not "Age(years)")
- Same punctuation (e.g., "N (%)" not "N(%)" or "N %")
- Same separators (e.g., " | " not "|" or ":")

✅ CORRECT example (if EXPECTED index 1 = "Median Age (years) | Treatment"):
  {{"column_index": 1, "column_name": "Median Age (years) | Treatment", "value": 67, ...}}

❌ WRONG examples:
  {{"column_index": 1, "column_name": "Median Age Treatment", ...}}  # Missing (years) and |
  {{"column_index": 1, "column_name": "median age (years) | treatment", ...}}  # Wrong case

Rules:
- Output JSON with fields: group_name, extractions
- extractions must have EXACTLY {len(expected_indices)} items
- Each item must include:
  - column_index: one of {expected_indices}
  - column_name: EXACT name for that index (match the EXPECTED list above exactly!)
  - value: string/number/null
  - evidence: string/null
  - page: string (e.g. \"5\" or \"7-10\")
  - confidence: high/medium/low
- Before outputting, verify each column_name matches the EXPECTED list exactly.

Free-form extraction:
{free_form}

Return ONLY valid JSON.
"""

    # Try local structurer first (5 attempts)
    structured = structurer.structure(
        text=structuring_prompt,
        schema=GroupExtractionV2,
        max_retries=5,
        return_dict=False,
    )
    
    # If local structurer fails, try fallback with bigger model
    if not structured.success:
        logger.warning(f"⚠️  Local structurer failed for '{group_name}' after 5 attempts")
        logger.info(f"🔄 Trying fallback structurer ({provider} API)...")
        
        # Use fallback structurer matching the extraction provider
        if provider == "openai":
            structured = structure_with_openai(
                client=openai_client,
                prompt=structuring_prompt,
                schema=GroupExtractionV2,
                model="gpt-4.1",
                max_retries=3
            )
        elif provider == "gemini":
            structured = structure_with_gemini(
                client=gemini_client,
                prompt=structuring_prompt,
                schema=GroupExtractionV2,
                model="gemini-2.5-flash",
                max_retries=3
            )
        
        # Check if fallback succeeded
        if structured.success:
            logger.info(f"✅ Fallback structurer succeeded for '{group_name}' (attempt {structured.attempts}/3)")
        else:
            # Both structurers failed, write error and return null placeholders
            logger.error(f"❌ Both local and fallback structurers failed for '{group_name}'")
            err_path = logs_dir / f"{safe_stem(group_name)}_{provider}_structuring_error.txt"
            error_msg = f"Local structurer failed after 5 attempts.\nFallback structurer failed after 3 attempts.\nLast error: {structured.error or 'unknown'}"
            err_path.write_text(error_msg, encoding="utf-8")
            logger.warning(f"Wrote error details to: logs/{err_path.name}")
            
            placeholders = [
                ColumnExtractionV2(
                    column_index=idx,
                    column_name=expected_columns[idx - 1],
                    value=None,
                    evidence=None,
                    page="",
                    confidence="low",
                )
                for idx in expected_indices
            ]
            return GroupExtractionV2(group_name=group_name, extractions=placeholders)

    extraction: GroupExtractionV2 = structured.data
    extraction.group_name = group_name

    # Validate canonical identity and normalize ordering.
    extraction = validate_and_normalize_extraction(
        extraction=extraction,
        expected_columns=expected_columns,
        expected_indices=expected_indices,
        name_policy=name_policy,
    )
    return extraction


# -----------------------------
# Output generation
# -----------------------------


def generate_outputs(
    *,
    groups_dict: Dict[str, list],
    plans_by_group: Dict[str, GroupExtractionPlanV2],
    extractions_by_group: Dict[str, GroupExtractionV2],
    output_dir: Path,
) -> None:
    # Canonical column order (full table).
    all_columns: List[str] = []
    for group_cols in groups_dict.values():
        for c in group_cols:
            all_columns.append(c["Column Name"])

    csv_row: Dict[str, Union[str, int, float]] = {}
    metadata: Dict[str, dict] = {}

    # Initialize as empty.
    for col in all_columns:
        csv_row[col] = ""
        metadata[col] = {"value": None, "evidence": None, "chunk_id": "not_extracted", "page": None}

    # Fill from extractions.
    for group_name, extraction in extractions_by_group.items():
        # Map index->canonical name from definitions.
        expected_cols = expected_columns_for_group(groups_dict, group_name)
        for item in extraction.extractions:
            canonical_name = expected_cols[item.column_index - 1]
            csv_row[canonical_name] = item.value if item.value is not None else ""
            metadata[canonical_name] = {
                "value": item.value,
                "evidence": item.evidence,
                "chunk_id": f"{group_name}::{item.column_index}",
                "page": item.page,
                "column_index": item.column_index,  # Add for traceability
                "group_name": group_name,  # Add for traceability
            }
            # If extraction used a different name, store it for debugging
            if item.column_name_raw and item.column_name_raw != canonical_name:
                metadata[canonical_name]["extraction_column_name_raw"] = item.column_name_raw

    # Add plan info for transparency (even if not extracted).
    for group_name, plan in plans_by_group.items():
        expected_cols = expected_columns_for_group(groups_dict, group_name)
        for p in plan.columns:
            canonical_name = expected_cols[p.column_index - 1]
            meta = metadata.get(canonical_name, {})
            meta.setdefault("plan_found_in_pdf", p.found_in_pdf)
            meta.setdefault("plan_page", p.page)
            meta.setdefault("plan_source_type", p.source_type)
            meta.setdefault("plan_confidence", p.confidence)
            meta.setdefault("plan_extraction_plan", p.extraction_plan)
            meta.setdefault("column_index", p.column_index)  # Add for traceability
            meta.setdefault("group_name", group_name)  # Add for traceability
            # If plan used a different name, store it for debugging
            if p.column_name_raw and p.column_name_raw != canonical_name:
                meta["plan_column_name_raw"] = p.column_name_raw
            metadata[canonical_name] = meta

    csv_path = output_dir / "extracted_table.csv"
    df = pd.DataFrame([csv_row], columns=all_columns)
    df.to_csv(csv_path, index=False)

    meta_path = output_dir / "extraction_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


# -----------------------------
# Main
# -----------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Run extraction using canonical plans (V2).")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--chunks", required=True, help="Path to pdf_chunked.json")
    parser.add_argument(
        "--plans-dir",
        default=None,
        help="Directory with *_plan.json (default: experiment-scripts/results/{pdf}/extraction_plans)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: experiment-scripts/results/{pdf}/extractions)",
    )
    parser.add_argument("--groups", nargs="+", help="Only run these group names (default: all groups with plans)")
    parser.add_argument("--provider", choices=["openai", "gemini"], default="openai")
    parser.add_argument("--model", default="gpt-4.1", help="Provider model")
    parser.add_argument("--workers", type=int, default=10, help="Parallel groups to process")
    parser.add_argument("--name-policy", choices=["strict", "override"], default="strict")
    parser.add_argument("--validate-only", action="store_true", help="Only validate plans and exit")
    parser.add_argument("--reuse-openai-file", action="store_true", default=True)

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    chunks_path = Path(args.chunks)
    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return 1
    if not chunks_path.exists():
        logger.error(f"Chunks file not found: {chunks_path}")
        return 1

    pdf_name = pdf_path.stem
    results_root = Path(__file__).resolve().parent / "results"
    if args.plans_dir:
        plans_dir = Path(args.plans_dir)
    else:
        plans_dir = results_root / pdf_name / "extraction_plans"
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = results_root / pdf_name / "extractions"
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    groups_dict = load_definitions()

    plans_by_group = load_plans_v2(plans_dir)
    if args.groups:
        wanted = set(args.groups)
        plans_by_group = {k: v for k, v in plans_by_group.items() if k in wanted}
        if not plans_by_group:
            logger.error(f"No matching plans for groups: {args.groups}")
            return 1

    # Strict plan validation gate before any LLM calls.
    validated_plans: Dict[str, GroupExtractionPlanV2] = {}
    for group_name, plan in plans_by_group.items():
        expected_cols = expected_columns_for_group(groups_dict, group_name)
        validated_plans[group_name] = validate_and_normalize_plan(
            plan=plan, expected_columns=expected_cols, name_policy=args.name_policy
        )

    logger.info(f"Validated {len(validated_plans)} group plans successfully.")
    if args.validate_only:
        return 0

    provider = args.provider
    model = args.model

    # Clients / PDF parts (reused).
    openai_client: Optional[OpenAI] = None
    openai_file_id: Optional[str] = None
    gemini_client = None
    gemini_pdf_part = None

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        openai_client = OpenAI(api_key=api_key)
        openai_file_id = upload_pdf_openai(openai_client, pdf_path)
        logger.info(f"Uploaded PDF to OpenAI once: {openai_file_id}")
    else:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        gemini_client = genai.Client(api_key=api_key)
        pdf_bytes = pdf_path.read_bytes()
        gemini_pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    structurer = OutputStructurer(
        base_url="http://localhost:8001/v1",
        model="Qwen/Qwen3-8B",
        enable_thinking=False,
    )

    extractions_by_group: Dict[str, GroupExtractionV2] = {}

    try:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {}
            for group_name, plan in validated_plans.items():
                expected_cols = expected_columns_for_group(groups_dict, group_name)
                futures[executor.submit(
                    extract_group_v2,
                    group_name=group_name,
                    plan=plan,
                    expected_columns=expected_cols,
                    pdf_path=pdf_path,
                    chunks=chunks,
                    provider=provider,
                    model=model,
                    openai_client=openai_client,
                    openai_file_id=openai_file_id,
                    gemini_client=gemini_client,
                    gemini_pdf_part=gemini_pdf_part,
                    structurer=structurer,
                    output_dir=output_dir,
                    name_policy=args.name_policy,
                    groups_dict=groups_dict,
                )] = group_name

            for fut in as_completed(futures):
                group_name = futures[fut]
                try:
                    extraction = fut.result()
                except Exception as e:
                    # Soft-fail a group; keep going.
                    logger.error(f"Group failed: {group_name}: {e}")
                    extractions_by_group[group_name] = GroupExtractionV2(group_name=group_name, extractions=[])
                    continue
                extractions_by_group[group_name] = extraction
                logger.info(f"Done group: {group_name} (extractions={len(extraction.extractions)})")

        generate_outputs(
            groups_dict=groups_dict,
            plans_by_group=validated_plans,
            extractions_by_group=extractions_by_group,
            output_dir=output_dir,
        )
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ Extraction Complete!")
        logger.info(f"📂 Output Structure:")
        logger.info(f"   {output_dir}/")
        logger.info(f"   ├── extracted_table.csv")
        logger.info(f"   ├── extraction_metadata.json")
        logger.info(f"   └── logs/")
        logger.info(f"       ├── *_openai_raw.txt (or *_gemini_raw.txt)")
        logger.info(f"       └── *_structuring_error.txt (if any failures)")
        logger.info(f"{'='*80}")

    finally:
        if openai_client and openai_file_id:
            delete_openai_file_safely(openai_client, openai_file_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

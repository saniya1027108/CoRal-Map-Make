#!/usr/bin/env python3
"""Plan generation (V2) for hierarchical/map-based extraction.

Goal: produce one plan per canonical column, per group, with strict validation.

Key differences vs test_hierarchical_extraction.py:
- The local structurer must emit a column_index (1..N) for each column.
- We validate indices are complete (no missing/dupes/out-of-range) before saving.
- We verify column_name matches the canonical Definitions.csv name for that index.
  (strict by default; can override mismatches if desired).
- We always output one plan per column (even if found_in_pdf=false).

Usage:
  python experiment-scripts/test_hierarchical_extraction_v2.py \
      --pdf "test_results/new/NCT.../NCT....pdf" \
      --chunks "test_results/new/NCT.../pdf_chunked.json" \
      --groups "Median Age (years)"

  python experiment-scripts/test_hierarchical_extraction_v2.py \
      --pdf "test_results/new/NCT.../NCT....pdf" \
      --chunks "test_results/new/NCT.../pdf_chunked.json" \
      --all
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google import genai
from google.genai import types

from src.LLMProvider.structurer import OutputStructurer
from src.table_definitions.definitions import load_definitions
from src.utils.logging_utils import setup_logger

logger = setup_logger("hierarchical_extraction_v2")


# -----------------------------
# Data structures
# -----------------------------

@dataclass
class Column:
    name: str
    definition: str


@dataclass
class ColumnGroup:
    name: str
    columns: List[Column]


# -----------------------------
# Schemas
# -----------------------------

SourceType = Literal["table", "text", "figure", "not_applicable"]
Confidence = Literal["high", "medium", "low"]


class ColumnExtractionPlanV2(BaseModel):
    """Extraction plan for one canonical column."""

    column_index: int = Field(description="1-based index into the EXPECTED_COLUMNS list")
    column_name: str = Field(description="Must exactly match the canonical column name at column_index")

    found_in_pdf: bool = Field(
        description="True if the value exists in the PDF; False if not reported/available"
    )
    page: int = Field(description="Page number if found; -1 if not found")
    source_type: SourceType = Field(description="table/text/figure if found, else not_applicable")
    confidence: Confidence = Field(description="high/medium/low")
    extraction_plan: str = Field(description="How to extract, or why not reported")

    # Keep original model-provided name if we ever override for debugging.
    column_name_raw: Optional[str] = None


class GroupExtractionPlanV2(BaseModel):
    """Plans for all columns in a group."""

    # We set/override this in code; do not rely on the model.
    group_name: str
    columns: List[ColumnExtractionPlanV2]


# -----------------------------
# Helpers
# -----------------------------


def safe_stem(name: str) -> str:
    """Stable filename stem for group names."""
    # Keep consistent across scripts.
    return (
        name.replace(" ", "_")
        .replace("/", "_")
        .replace("|", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def load_column_groups() -> List[ColumnGroup]:
    groups_dict = load_definitions()
    out: List[ColumnGroup] = []
    for group_name, cols in groups_dict.items():
        out.append(
            ColumnGroup(
                name=group_name,
                columns=[Column(name=c["Column Name"], definition=c["Definition"]) for c in cols],
            )
        )
    return out


def format_chunk_summaries(chunks: list) -> str:
    summaries = []
    for i, chunk in enumerate(chunks):
        chunk_type = chunk.get("type", "unknown")
        page = chunk.get("page", "?")
        content_preview = (chunk.get("content", "") or "")[:120].replace("\n", " ")
        if chunk_type == "table":
            summary = f"Chunk {i}: TABLE on page {page} - {content_preview}..."
        elif chunk_type == "figure":
            summary = f"Chunk {i}: FIGURE on page {page} - {content_preview}..."
        else:
            summary = f"Chunk {i}: TEXT on pages {page} - {content_preview}..."
        summaries.append(summary)
    return "\n".join(summaries)


def build_expected_columns_block(group: ColumnGroup) -> str:
    lines = []
    for i, col in enumerate(group.columns, 1):
        # Include definition here to reduce ambiguity.
        lines.append(f"{i}. {col.name}\n   Definition: {col.definition}")
    return "\n".join(lines)


def _normalize_not_found(plan: ColumnExtractionPlanV2) -> ColumnExtractionPlanV2:
    if not plan.found_in_pdf:
        # Coerce invariants for downstream reliability.
        plan.page = -1
        plan.source_type = "not_applicable"
    return plan


def validate_and_normalize_group_plan(
    *,
    group_name: str,
    plan: GroupExtractionPlanV2,
    expected_columns: List[str],
    name_policy: Literal["strict", "override"] = "strict",
) -> GroupExtractionPlanV2:
    """Enforce canonical identity: indices + exact names."""

    n = len(expected_columns)

    # Validate indices and build index->plan map.
    by_idx = {}
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
            f"Invalid column_index set for group '{group_name}'. "
            f"dupes={sorted(set(dupes))}, out_of_range={sorted(set(out_of_range))}, missing_count={len(missing)}"
        )

    # Validate/override names and rebuild in canonical order.
    normalized: List[ColumnExtractionPlanV2] = []
    name_mismatches = []

    for idx in range(1, n + 1):
        item = by_idx[idx]
        canonical = expected_columns[idx - 1]
        if item.column_name != canonical:
            name_mismatches.append((idx, item.column_name, canonical))
            if name_policy == "override":
                item.column_name_raw = item.column_name
                item.column_name = canonical
        item = _normalize_not_found(item)
        normalized.append(item)

    if name_mismatches and name_policy == "strict":
        preview = "\n".join([f"  • Index {i}: Got '{got}'\n             Expected '{want}'" for i, got, want in name_mismatches[:5]])
        total = len(name_mismatches)
        more = f" (and {total - 5} more)" if total > 5 else ""
        raise ValueError(
            f"\n❌ Column name mismatch(es) for group '{group_name}':\n"
            f"The structurer output incorrect column names. This will cause downstream issues.\n"
            f"Fix: Improve the structuring prompt or use --name-policy=override.\n\n"
            f"Mismatches{more}:\n{preview}"
        )

    plan.group_name = group_name
    plan.columns = normalized
    return plan


# -----------------------------
# Planning
# -----------------------------


def generate_extraction_plan_for_group(
    *,
    group: ColumnGroup,
    chunks: list,
    pdf_part,
    gemini_client,
    structurer: OutputStructurer,
    output_dir: Path,
    gemini_model: str,
    structurer_debug: bool,
    name_policy: Literal["strict", "override"],
) -> GroupExtractionPlanV2:
    logger.info("\n" + "=" * 80)
    logger.info(f"📋 Planning extraction for group: {group.name}")
    logger.info(f"   Columns: {len(group.columns)}")
    logger.info("=" * 80)

    # Create logs subdirectory for individual column files
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    chunk_summaries = format_chunk_summaries(chunks)
    expected_block = build_expected_columns_block(group)

    # Free-form planning prompt (Gemini)
    prompt = f"""You are creating an extraction plan for a clinical trial data extraction task.

You have:
- The FULL PDF loaded (for structure + precise reference)
- A list of pre-extracted chunks (to orient you)

AVAILABLE CHUNKS:
{chunk_summaries}

TASK:
For EACH of the following canonical columns, decide whether the value is reported in this PDF.
If reported, identify WHERE and HOW to extract it.
If not reported, say it is not reported.

⚠️ CRITICAL INSTRUCTION:
When you refer to these columns in your response, you MUST use their EXACT names as listed below.
Do NOT paraphrase, abbreviate, or modify column names in ANY way.
Character-for-character match is REQUIRED (including spaces, punctuation, pipes |, parentheses).

CANONICAL COLUMNS (ORDERED; use these EXACT names in your response):
{expected_block}

Rules:
- Be honest: many columns will NOT be reported.
- If found_in_pdf=false, state why in extraction_plan.
- If found_in_pdf=true, include page number, source type (table/text/figure), and concrete instructions.
- ALWAYS refer to columns using their exact canonical names (copy-paste from the list above).
"""

    logger.info("🤖 Calling Gemini for free-form planning...")
    config = types.GenerateContentConfig(temperature=0.1)
    resp = gemini_client.models.generate_content(
        model=gemini_model,
        contents=[pdf_part, prompt],
        config=config,
    )
    free_form = (resp.text or "").strip()
    logger.info(f"   Gemini response length: {len(free_form)} chars")

    stem = safe_stem(group.name)
    raw_file = logs_dir / f"{stem}_raw.txt"
    raw_file.write_text(free_form, encoding="utf-8")
    logger.info(f"💾 Saved raw plan to: logs/{raw_file.name}")

    # Build structuring prompt for local model.
    expected_columns = [c.name for c in group.columns]
    expected_names_list = "\n".join([f"{i}. {name}" for i, name in enumerate(expected_columns, 1)])

    structuring_prompt = f"""Convert the following free-form extraction plan into STRICT JSON.

Group name (use exactly this, do not rename): "{group.name}"

EXPECTED_COLUMNS (ordered; index is canonical):
{expected_names_list}

⚠️⚠️⚠️ CRITICAL REQUIREMENT ⚠️⚠️⚠️
For each item, the column_name field MUST be an EXACT CHARACTER-FOR-CHARACTER match with EXPECTED_COLUMNS[column_index].
This means:
- Same capitalization (e.g., "Median" not "median")
- Same spacing (e.g., "Age (years)" not "Age(years)")
- Same punctuation (e.g., "N (%)" not "N(%)" or "N %")
- Same separators (e.g., " | " not "|" or ":")

✅ CORRECT example (column_index=1, EXPECTED="Median Age (years) | Treatment"):
  {{"column_index": 1, "column_name": "Median Age (years) | Treatment", ...}}

❌ WRONG examples:
  {{"column_index": 1, "column_name": "Median Age Treatment", ...}}  # Missing (years) and |
  {{"column_index": 1, "column_name": "median age (years) | treatment", ...}}  # Wrong case
  {{"column_index": 1, "column_name": "Age (years) | Treatment", ...}}  # Missing "Median"

Output rules (MUST follow exactly):
- Return JSON with fields: group_name, columns
- columns must be a list with EXACTLY {len(expected_columns)} items
- Each item must have:
  - column_index: integer from 1..{len(expected_columns)} (no duplicates, no missing)
  - column_name: EXACT string equal to EXPECTED_COLUMNS[column_index] (see warning above!)
  - found_in_pdf: true/false
  - page: integer (use -1 if not found)
  - source_type: one of table/text/figure/not_applicable
  - confidence: one of high/medium/low
  - extraction_plan: string

IMPORTANT:
- You MUST produce one plan per EXPECTED column.
- Do NOT invent extra columns.
- If found_in_pdf=false, set page=-1 and source_type=not_applicable.
- Before outputting, verify each column_name matches EXPECTED_COLUMNS exactly.

Free-form plan text:
{free_form}

Return ONLY valid JSON.
"""

    logger.info("🔧 Structuring plan with local LLM...")

    # Optional per-group debug file (in logs subdirectory).
    debug_file = logs_dir / f"{stem}_structurer_debug.txt" if structurer_debug else None
    if structurer_debug:
        structurer_local = OutputStructurer(
            base_url=structurer.base_url,
            model=structurer.model,
            enable_thinking=getattr(structurer, "enable_thinking", False),
            debug_file=str(debug_file),
        )
    else:
        structurer_local = structurer

    structured = structurer_local.structure(
        text=structuring_prompt,
        schema=GroupExtractionPlanV2,
        max_retries=5,
        return_dict=False,
    )

    if not structured.success:
        raise ValueError(f"Structuring failed for group '{group.name}': {structured.error}")

    plan: GroupExtractionPlanV2 = structured.data

    # Canonical normalization + strict validation gate.
    plan = validate_and_normalize_group_plan(
        group_name=group.name,
        plan=plan,
        expected_columns=expected_columns,
        name_policy=name_policy,
    )

    # Save structured plan to logs subdirectory
    plan_path = logs_dir / f"{stem}_plan.json"
    plan_path.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
    logger.info(f"💾 Saved structured plan to: logs/{plan_path.name}")

    # Summary
    found = sum(1 for c in plan.columns if c.found_in_pdf)
    logger.info(f"📊 Plan Summary: found_in_pdf=true for {found}/{len(plan.columns)}")

    return plan


# -----------------------------
# CLI
# -----------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate extraction plans (V2, strict canonical validation)")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--chunks", required=True, help="Path to pdf_chunked.json")
    parser.add_argument("--groups", nargs="+", help="Specific group names to run")
    parser.add_argument("--all", action="store_true", help="Run all groups")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save outputs (default: experiment-scripts/results/{pdf_name}/extraction_plans)",
    )
    parser.add_argument("--gemini-model", default="gemini-2.5-flash", help="Gemini model")
    parser.add_argument(
        "--name-policy",
        choices=["strict", "override"],
        default="strict",
        help="What to do if structurer column_name != canonical name for the index",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of groups to plan in parallel (default: 10)",
    )
    parser.add_argument(
        "--no-structurer-debug",
        action="store_true",
        help="Disable per-group structurer debug files",
    )

    args = parser.parse_args()

    if not args.groups and not args.all:
        parser.error("Must specify either --groups or --all")

    pdf_path = Path(args.pdf)
    chunks_path = Path(args.chunks)

    if not pdf_path.exists():
        logger.error(f"❌ PDF not found: {pdf_path}")
        return 1
    if not chunks_path.exists():
        logger.error(f"❌ Chunks file not found: {chunks_path}")
        return 1

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).resolve().parent / "results" / pdf_path.stem / "extraction_plans"
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    all_groups = load_column_groups()

    if args.all:
        selected = all_groups
    else:
        wanted = set(args.groups)
        selected = [g for g in all_groups if g.name in wanted]
        if not selected:
            logger.error(f"❌ No matching groups found for: {args.groups}")
            logger.info("Available groups:")
            for g in all_groups:
                logger.info(f" - {g.name}")
            return 1

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not set")
        return 1

    pdf_bytes = pdf_path.read_bytes()

    ok = 0
    failed = []

    def _plan_one(group: ColumnGroup) -> str:
        # Create per-task clients to avoid thread-safety surprises.
        gemini_client = genai.Client(api_key=api_key)
        pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
        structurer = OutputStructurer(
            base_url="http://localhost:8001/v1",
            model="Qwen/Qwen3-8B",
            enable_thinking=False,
        )
        generate_extraction_plan_for_group(
            group=group,
            chunks=chunks,
            pdf_part=pdf_part,
            gemini_client=gemini_client,
            structurer=structurer,
            output_dir=output_dir,
            gemini_model=args.gemini_model,
            structurer_debug=not args.no_structurer_debug,
            name_policy=args.name_policy,
        )
        return group.name

    logger.info(f"🚀 Planning {len(selected)} groups in parallel ({args.workers} workers)...")
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(_plan_one, group): group.name for group in selected}
        for fut in as_completed(futures):
            group_name = futures[fut]
            try:
                fut.result()
                ok += 1
                logger.info(f"✅ Planned: {group_name}")
            except Exception as e:
                logger.error(f"❌ Failed group '{group_name}': {e}")
                failed.append(group_name)

    logger.info("\n" + "=" * 80)
    logger.info(f"✅ Successful: {ok}/{len(selected)}")
    if failed:
        logger.info(f"❌ Failed: {len(failed)}")
        for g in failed:
            logger.info(f" - {g}")
    logger.info(f"📂 Output directory: {output_dir}")
    logger.info("=" * 80)

    # Create compiled plans file with all columns from all groups
    if ok > 0:
        logger.info("\n📦 Creating compiled plans file...")
        all_plans = []
        logs_dir = output_dir / "logs"
        plan_files = sorted(logs_dir.glob("*_plan.json"))
        
        for plan_file in plan_files:
            try:
                plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
                all_plans.append(plan_data)
            except Exception as e:
                logger.warning(f"Failed to read plan file {plan_file.name}: {e}")
        
        if all_plans:
            compiled_path = output_dir / "plans_all_columns.json"
            compiled_data = {
                "pdf_name": pdf_path.stem,
                "total_groups": len(all_plans),
                "total_columns": sum(len(p.get("columns", [])) for p in all_plans),
                "plans": all_plans
            }
            compiled_path.write_text(json.dumps(compiled_data, indent=2), encoding="utf-8")
            logger.info(f"💾 Saved compiled plans to: {compiled_path.name}")
            logger.info(f"   Total groups: {compiled_data['total_groups']}")
            logger.info(f"   Total columns: {compiled_data['total_columns']}")

    return 0 if ok == len(selected) else 2


if __name__ == "__main__":
    raise SystemExit(main())

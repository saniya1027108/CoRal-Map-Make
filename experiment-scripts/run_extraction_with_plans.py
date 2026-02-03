#!/usr/bin/env python3
"""
Run extraction using pre-generated extraction plans.

This script:
1. Loads extraction plans from results/{pdf_name}/extraction_plans/
2. Filters columns where found_in_pdf = true
3. Finds relevant chunks for each group
4. Calls gpt-4.1 with full PDF context + targeted chunks
5. Structures output with local LLM
6. Generates extracted_table.csv and extraction_metadata.json

Usage:
    python experiment-scripts/run_extraction_with_plans.py \
        --pdf "test_results/new/NCT.../NCT....pdf" \
        --chunks "test_results/new/NCT.../pdf_chunked.json" \
        --plans-dir "results/NCT.../extraction_plans" \
        --output-dir "results/NCT.../extractions"
"""

import argparse
import json
import sys
import os
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union, Literal
from dataclasses import dataclass
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from google import genai
from google.genai import types
from src.LLMProvider.structurer import OutputStructurer
from src.table_definitions.definitions import load_definitions
from src.utils.logging_utils import setup_logger
from extraction_providers import call_openai_extraction, call_gemini_extraction

logger = setup_logger("extraction_with_plans")


# ============== DATA STRUCTURES ==============

class ColumnExtraction(BaseModel):
    """Single column extraction result."""
    column_name: str
    value: Optional[Union[str, int, float]] = Field(description="Extracted value (string, number, percentage, etc.), or null if not found")
    evidence: Optional[str] = Field(description="Supporting text/quote from PDF")
    page: str = Field(description="Page number or range (e.g., '5' or '7-10')")
    confidence: Literal["high", "medium", "low"]
    
    @field_validator('confidence', mode='before')
    @classmethod
    def normalize_confidence(cls, v):
        """Convert confidence to lowercase for case-insensitive validation."""
        if isinstance(v, str):
            return v.lower()
        return v


class GroupExtraction(BaseModel):
    """Extraction results for one group."""
    group_name: str
    extractions: List[ColumnExtraction]


# ============== HELPER FUNCTIONS ==============

def load_extraction_plans(plans_dir: Path) -> dict:
    """Load all extraction plans from directory."""
    plans = {}
    plan_files = list(plans_dir.glob("*_plan.json"))
    
    logger.info(f"📂 Loading {len(plan_files)} extraction plans...")
    
    for plan_file in plan_files:
        with open(plan_file, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)
            group_name = plan_data["group_name"]
            
            # Fix: If group_name is the schema class name, infer from filename
            if group_name == "GroupExtractionPlan":
                # Extract from filename: "Add-on_Treatment_plan.json" -> "Add-on Treatment"
                inferred_name = plan_file.stem.replace("_plan", "").replace("_", " ")
                logger.warning(f"   ⚠️  Fixed bad group_name in {plan_file.name}: '{group_name}' -> '{inferred_name}'")
                plan_data["group_name"] = inferred_name
                group_name = inferred_name
            
            plans[group_name] = plan_data
    
    logger.info(f"   ✅ Loaded {len(plans)} plans")
    return plans


def find_relevant_chunks(col_plans: list, chunks: list) -> list:
    """
    Find chunks relevant to the extraction plan.
    
    Matches by:
    - source_type (table/text/figure)
    - page number (handles ranges for text chunks)
    """
    relevant = []
    seen_chunk_ids = set()
    
    for col_plan in col_plans:
        if not col_plan.get("found_in_pdf", False):
            continue
        
        source_type = col_plan.get("source_type", "").lower()
        target_page = col_plan.get("page", -1)
        
        if target_page == -1:
            continue
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{i}_{chunk.get('type', 'text')}"
            
            if chunk_id in seen_chunk_ids:
                continue
            
            chunk_type = chunk.get("type", "text").lower()
            chunk_page = chunk.get("page")
            
            # Match type
            if chunk_type != source_type:
                continue
            
            # Match page
            page_match = False
            
            if isinstance(chunk_page, int):
                page_match = (chunk_page == target_page)
            elif isinstance(chunk_page, str):
                # Handle ranges like "7-10" or "1-5"
                if "-" in str(chunk_page):
                    try:
                        parts = str(chunk_page).split("-")
                        start, end = int(parts[0]), int(parts[1])
                        page_match = (start <= target_page <= end)
                    except:
                        pass
                else:
                    try:
                        page_match = (int(chunk_page) == target_page)
                    except:
                        pass
            
            if page_match:
                relevant.append({
                    "chunk_id": i,
                    "type": chunk_type,
                    "page": chunk_page,
                    "content": chunk.get("content", "")[:1000]  # Truncate for display
                })
                seen_chunk_ids.add(chunk_id)
    
    return relevant


def format_column_definitions(col_plans: list, definitions_lookup: dict) -> str:
    """Format column definitions with extraction plans."""
    formatted = []
    
    for i, col_plan in enumerate(col_plans, 1):
        if not col_plan.get("found_in_pdf", False):
            continue
        
        col_name = col_plan["column_name"]
        page = col_plan["page"]
        source_type = col_plan["source_type"]
        confidence = col_plan["confidence"]
        extraction_plan = col_plan["extraction_plan"]
        
        # Get definition from lookup
        definition = definitions_lookup.get(col_name, "No definition available")
        
        formatted.append(f"""
{i}. Column: "{col_name}"
   Definition: {definition}
   Expected Location: Page {page} | {source_type}
   Planner Confidence: {confidence}
   Extraction Instructions:
   {extraction_plan}
""")
    
    return "\n".join(formatted)


def format_chunks(chunks: list) -> str:
    """Format chunks for prompt."""
    if not chunks:
        return "No relevant chunks found."
    
    formatted = []
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        chunk_type = chunk["type"].upper()
        page = chunk["page"]
        content_preview = chunk["content"][:500].replace("\n", " ")
        
        formatted.append(f"""
--- Chunk {chunk_id} ({chunk_type} on page {page}) ---
{content_preview}...
""")
    
    return "\n".join(formatted)


def extract_group(
    group_name: str,
    plan: dict,
    pdf_path: Path,
    chunks: list,
    llm_client,  # Can be OpenAI or Gemini client
    provider: str,  # "openai" or "gemini"
    model: str,  # Model name
    structurer: OutputStructurer,
    definitions_lookup: dict,
    output_dir: Path = None
) -> GroupExtraction:
    """
    Extract data for one column group using LLM + local structuring.
    Supports both OpenAI (GPT-4o) and Gemini.
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"🎯 Extracting group: {group_name}")
    logger.info(f"{'='*80}")
    
    col_plans = plan["columns"]
    
    # Filter: only columns found in PDF
    found_cols = [c for c in col_plans if c.get("found_in_pdf", False)]
    not_found_cols = [c for c in col_plans if not c.get("found_in_pdf", False)]
    
    logger.info(f"   Columns found in PDF: {len(found_cols)}/{len(col_plans)}")
    if not_found_cols:
        logger.info(f"   Skipping {len(not_found_cols)} columns not in PDF:")
        for col in not_found_cols[:3]:  # Show first 3
            logger.info(f"      - {col['column_name']}")
        if len(not_found_cols) > 3:
            logger.info(f"      ... and {len(not_found_cols) - 3} more")
    
    if not found_cols:
        logger.warning(f"   ⚠️  No columns to extract for this group!")
        return GroupExtraction(group_name=group_name, extractions=[])
    
    # Find relevant chunks
    logger.info(f"🔍 Finding relevant chunks...")
    relevant_chunks = find_relevant_chunks(col_plans, chunks)
    logger.info(f"   Found {len(relevant_chunks)} relevant chunks")
    
    # Create extraction prompt
    column_defs = format_column_definitions(found_cols, definitions_lookup)
    chunks_formatted = format_chunks(relevant_chunks)
    
    prompt = f"""You are extracting clinical trial data from a research paper.

TASK: Extract values for the following columns according to their extraction plans.

COLUMN DEFINITIONS AND EXTRACTION PLANS:
{column_defs}

RELEVANT PRE-EXTRACTED CHUNKS (filtered by type and page):
{chunks_formatted}

EXTRACTION GUIDELINES:
1. For EACH column, extract the value following its specific extraction plan
2. Provide supporting EVIDENCE as a direct quote from the PDF
3. Include the PAGE number where you found the value
4. Assess your CONFIDENCE (high/medium/low) based on:
   - high: Value is clearly stated and unambiguous
   - medium: Value is present but requires interpretation
   - low: Value is unclear or might be inferred
5. If a value is NOT found despite being expected, set value to null and explain why in evidence

IMPORTANT NOTES:
- You have access to the FULL PDF - use it for context
- The chunks above are pre-filtered to help you, but you can verify in the full PDF
- Some columns require AGGREGATION (e.g., summing subgroups) - follow the plan
- Be precise with numbers, percentages, and units
- Quote the exact text that supports your extraction

Think carefully about each column. Extract systematically and thoroughly.
"""
    
    # Call LLM (OpenAI or Gemini)
    if provider == "openai":
        free_form_extraction = call_openai_extraction(llm_client, pdf_path, prompt, model)
    elif provider == "gemini":
        free_form_extraction = call_gemini_extraction(llm_client, pdf_path, prompt, model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    
    logger.info(f"   ✅ {provider.upper()} response: {len(free_form_extraction)} chars")
    
    # Save raw LLM output
    if output_dir:
        safe_group_name = group_name.replace(' ', '_').replace('/', '_').replace('|', '_')
        raw_output_file = output_dir / f"{safe_group_name}_{provider}_raw.txt"
        raw_output_file.write_text(free_form_extraction, encoding='utf-8')
        logger.info(f"   💾 Saved raw {provider.upper()} output to: {raw_output_file.name}")
    
    # Structure with local LLM
    logger.info(f"🔧 Structuring output with local LLM...")
    
    # Add clear instructions about expected format in the text
    structuring_prompt = f"""The following is free-form extraction data that needs to be structured into JSON.

Group name: "{group_name}"

Expected JSON structure:
{{
  "group_name": "{group_name}",
  "extractions": [
    {{
      "column_name": "Column Name Here",
      "value": "extracted value or null",
      "evidence": "supporting quote from PDF",
      "page": "page_number_or_range",
      "confidence": "high"
    }}
  ]
}}

IMPORTANT:
- confidence must be lowercase: "high", "medium", or "low" (NOT "High", "Medium", "Low")
- page should be a string (e.g., "5" or "7-10")
- value can be string, number, a combination of both, or null
- evidence should be a direct quote from the PDF

Free-form extraction data:
{free_form_extraction}

Convert this to valid JSON matching the structure above. Output ONLY the JSON, no explanations."""
    
    structured_result = structurer.structure(
        text=structuring_prompt,
        schema=GroupExtraction,
        max_retries=5,  # Increased retries
        return_dict=False
    )
    
    if not structured_result.success:
        logger.error(f"   ❌ Structuring failed: {structured_result.error}")
        raise ValueError(f"Failed to structure extraction: {structured_result.error}")
    
    extraction = structured_result.data
    logger.info(f"   ✅ Structured {len(extraction.extractions)} extractions")
    
    # Log summary
    logger.info(f"\n📊 Extraction Summary:")
    extracted_count = sum(1 for e in extraction.extractions if e.value is not None)
    logger.info(f"   Extracted: {extracted_count}/{len(extraction.extractions)}")
    
    for extr in extraction.extractions[:5]:  # Show first 5
        value_preview = str(extr.value)[:50] if extr.value else "NULL"
        logger.info(f"   • {extr.column_name}: {value_preview}")
    
    if len(extraction.extractions) > 5:
        logger.info(f"   ... and {len(extraction.extractions) - 5} more")
    
    return extraction


def generate_outputs(extractions: dict, output_dir: Path, pdf_name: str):
    """
    Generate extracted_table.csv and extraction_metadata.json.
    
    Matches current pipeline output format.
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"📝 Generating output files...")
    logger.info(f"{'='*80}")
    
    # Collect all extractions
    all_extractions = []
    for group_name, extraction in extractions.items():
        all_extractions.extend(extraction.extractions)
    
    logger.info(f"   Total extractions: {len(all_extractions)}")
    
    # Build CSV row (single row with all columns)
    csv_row = {}
    metadata = {}
    
    for extr in all_extractions:
        col_name = extr.column_name
        value = extr.value
        
        # CSV: store value (or empty string if null)
        csv_row[col_name] = value if value is not None else ""
        
        # Metadata: store detailed info
        metadata[col_name] = {
            "value": value,
            "evidence": extr.evidence,
            "chunk_id": "gpt4o_extraction",  # Placeholder
            "page": extr.page
        }
    
    # Load all possible columns from definitions
    all_column_groups = load_definitions()
    all_columns = []
    for group_cols in all_column_groups.values():
        for col_def in group_cols:
            all_columns.append(col_def["Column Name"])
    
    # Fill missing columns with empty values
    for col in all_columns:
        if col not in csv_row:
            csv_row[col] = ""
            metadata[col] = {
                "value": None,
                "evidence": None,
                "chunk_id": "not_extracted",
                "page": None
            }
    
    # Generate CSV
    csv_path = output_dir / "extracted_table.csv"
    df = pd.DataFrame([csv_row], columns=all_columns)
    df.to_csv(csv_path, index=False)
    logger.info(f"   ✅ CSV saved: {csv_path.name}")
    logger.info(f"      Columns: {len(csv_row)}")
    logger.info(f"      With values: {sum(1 for v in csv_row.values() if v)}")
    
    # Generate metadata JSON
    metadata_path = output_dir / "extraction_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4)
    logger.info(f"   ✅ Metadata saved: {metadata_path.name}")
    
    logger.info(f"\n🎉 Output files generated successfully!")


# ============== MAIN ==============

def main():
    parser = argparse.ArgumentParser(
        description="Run extraction using pre-generated extraction plans",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python experiment-scripts/run_extraction_with_plans.py \\
      --pdf "test_results/new/NCT.../NCT....pdf" \\
      --chunks "test_results/new/NCT.../pdf_chunked.json" \\
      --plans-dir "results/NCT.../extraction_plans" \\
      --output-dir "results/NCT.../extractions"
        """
    )
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--chunks", required=True, help="Path to pdf_chunked.json")
    parser.add_argument("--plans-dir", default=None, 
                       help="Directory with extraction plans (default: auto-detect from PDF name)")
    parser.add_argument("--output-dir", default=None,
                       help="Output directory (default: results/{pdf_name}/extractions)")
    parser.add_argument("--groups", nargs="+", help="Specific group names to extract")
    parser.add_argument("--provider", choices=["openai", "gemini"], default="openai",
                       help="LLM provider for extraction (default: openai)")
    parser.add_argument("--model", default=None,
                       help="Model name (default: gpt-4o for openai, gemini-2.5-flash for gemini)")
    
    args = parser.parse_args()
    
    # Setup paths
    pdf_path = Path(args.pdf)
    chunks_path = Path(args.chunks)
    pdf_name = pdf_path.stem
    
    if args.plans_dir:
        plans_dir = Path(args.plans_dir)
    else:
        plans_dir = Path("results") / pdf_name / "extraction_plans"
    
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path("results") / pdf_name / "extractions"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate inputs
    logger.info("="*80)
    logger.info("🚀 EXTRACTION WITH PLANS")
    logger.info("="*80)
    logger.info(f"\n📂 Validating inputs...")
    
    if not pdf_path.exists():
        logger.error(f"❌ PDF not found: {pdf_path}")
        return 1
    
    if not chunks_path.exists():
        logger.error(f"❌ Chunks file not found: {chunks_path}")
        return 1
    
    if not plans_dir.exists():
        logger.error(f"❌ Plans directory not found: {plans_dir}")
        logger.error(f"   Did you run test_hierarchical_extraction.py first?")
        return 1
    
    logger.info(f"   ✅ PDF: {pdf_path.name}")
    logger.info(f"   ✅ Chunks: {chunks_path.name}")
    logger.info(f"   ✅ Plans dir: {plans_dir}")
    logger.info(f"   ✅ Output dir: {output_dir}")
    
    # Load data
    logger.info(f"\n📥 Loading data...")
    chunks = json.loads(chunks_path.read_text(encoding='utf-8'))
    plans = load_extraction_plans(plans_dir)
    
    # Load column definitions
    all_column_groups = load_definitions()
    definitions_lookup = {}
    for group_cols in all_column_groups.values():
        for col_def in group_cols:
            definitions_lookup[col_def["Column Name"]] = col_def["Definition"]
    
    logger.info(f"   ✅ Chunks: {len(chunks)}")
    logger.info(f"   ✅ Plans: {len(plans)} groups")
    logger.info(f"   ✅ Definitions: {len(definitions_lookup)} columns")
    
    # Filter groups if specified
    if args.groups:
        plans = {k: v for k, v in plans.items() if k in args.groups}
        logger.info(f"   → Filtered to {len(plans)} groups")
    
    # Initialize clients
    logger.info(f"\n🔧 Initializing clients...")
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("❌ OPENAI_API_KEY not set")
        return 1
    
    openai_client = OpenAI(api_key=openai_api_key)
    structurer = OutputStructurer(
        base_url="http://localhost:8001/v1",
        model="Qwen/Qwen3-8B"
    )
    
    logger.info("   ✅ OpenAI client initialized")
    logger.info("   ✅ Local structurer initialized")
    
    # Extract data (multithreaded)
    logger.info(f"\n{'='*80}")
    logger.info(f"🎯 Starting extraction (multithreaded)...")
    logger.info(f"{'='*80}")
    
    extractions = {}
    success_count = 0
    failed_groups = []
    
    # Use ThreadPoolExecutor for parallel extraction
    max_workers = min(20, len(plans))  # Max 5 concurrent API calls
    logger.info(f"   Using {max_workers} parallel workers")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all extraction tasks
        future_to_group = {
            executor.submit(
                extract_group,
                group_name=group_name,
                plan=plan,
                pdf_path=pdf_path,
                chunks=chunks,
                llm_client=llm_client,
                provider=provider,
                model=model,
                structurer=structurer,
                definitions_lookup=definitions_lookup,
                output_dir=output_dir
            ): group_name
            for group_name, plan in plans.items()
        }
        
        # Process completed tasks as they finish
        for i, future in enumerate(as_completed(future_to_group), 1):
            group_name = future_to_group[future]
            logger.info(f"\n[{i}/{len(plans)}] Processing result for: {group_name}")
            
            try:
                extraction = future.result()
                extractions[group_name] = extraction
                success_count += 1
                logger.info(f"✅ Success!")
            
            except Exception as e:
                logger.error(f"❌ Failed: {e}")
                failed_groups.append(group_name)
                import traceback
                logger.error(traceback.format_exc())
                continue
    
    # Generate output files
    if extractions:
        generate_outputs(extractions, output_dir, pdf_name)
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"✅ Successful: {success_count}/{len(plans)}")
    if failed_groups:
        logger.info(f"❌ Failed: {len(failed_groups)}")
        for name in failed_groups:
            logger.info(f"   - {name}")
    
    logger.info(f"\n💾 Output location: {output_dir}")
    logger.info(f"   - extracted_table.csv")
    logger.info(f"   - extraction_metadata.json")
    
    logger.info(f"\n🎨 Visualize results:")
    logger.info(f"   python visualizer/visualize_extraction.py {output_dir / 'extracted_table.csv'}")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ COMPLETE!")
    logger.info(f"{'='*80}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

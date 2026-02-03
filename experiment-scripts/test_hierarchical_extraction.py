#!/usr/bin/env python3
"""
Test hierarchical extraction with planning phase.

This script generates extraction plans for column groups by:
1. Asking Gemini to reason about where/how to extract (free-form)
2. Using local LLM to structure the response into JSON

Output: One JSON file per group with extraction plans.

Usage:
    python experiment-scripts/test_hierarchical_extraction.py \
        --pdf "test_results/new/NCT.../NCT....pdf" \
        --chunks "test_results/new/NCT.../pdf_chunked.json" \
        --groups "Median Age (years)" "Volume of disease - N (%)"
"""

import argparse
import json
import sys
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
from dataclasses import dataclass

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google import genai
from google.genai import types
from src.LLMProvider.structurer import OutputStructurer
from src.table_definitions.definitions import load_definitions
from src.utils.logging_utils import setup_logger

logger = setup_logger("hierarchical_extraction")


# ============== DATA STRUCTURES ==============

@dataclass
class Column:
    """Represents a single column."""
    name: str
    definition: str


@dataclass
class ColumnGroup:
    """Represents a group of related columns."""
    name: str
    columns: List[Column]


# ============== SCHEMAS ==============

class ColumnExtractionPlan(BaseModel):
    """Simple extraction plan for one column."""
    column_name: str
    found_in_pdf: bool = Field(description="Whether this column's data is present in the PDF (True) or not reported (False)")
    page: int = Field(description="Page number where value is located. Use -1 if not found in PDF.")
    source_type: str = Field(description="Source type: 'table', 'text', 'figure', or 'not_applicable' if not found")
    confidence: str = Field(description="Confidence level: 'high', 'medium', or 'low'")
    extraction_plan: str = Field(
        description="Free-form explanation of how to extract the value (if found) or why it's not available (if not found). "
                    "Include: synonyms used in the paper, aggregation needed, special notes, etc."
    )


class GroupExtractionPlan(BaseModel):
    """Plans for all columns in a group."""
    group_name: str
    columns: List[ColumnExtractionPlan]


# ============== HELPER FUNCTIONS ==============

def load_column_groups() -> List[ColumnGroup]:
    """Load column groups from definitions CSV."""
    groups_dict = load_definitions()
    column_groups = []
    
    for group_name, columns_list in groups_dict.items():
        columns = [
            Column(name=col["Column Name"], definition=col["Definition"])
            for col in columns_list
        ]
        column_groups.append(ColumnGroup(name=group_name, columns=columns))
    
    return column_groups


def format_chunk_summaries(chunks):
    """Format chunks for display in prompt."""
    summaries = []
    for i, chunk in enumerate(chunks):
        chunk_type = chunk.get("type", "unknown")
        page = chunk.get("page", "?")
        content_preview = chunk.get("content", "")[:120].replace("\n", " ")
        
        if chunk_type == "table":
            summary = f"Chunk {i}: TABLE on page {page} - {content_preview}..."
        elif chunk_type == "figure":
            summary = f"Chunk {i}: FIGURE on page {page} - {content_preview}..."
        else:
            summary = f"Chunk {i}: TEXT on pages {page} - {content_preview}..."
        
        summaries.append(summary)
    
    return "\n".join(summaries)


# ============== PLANNING FUNCTION ==============

def generate_extraction_plan(pdf_path, chunks, column_group, gemini_client, structurer, output_dir):
    """
    Generate extraction plan for one column group.
    
    Args:
        pdf_path: Path to PDF
        chunks: List of chunks
        column_group: ColumnGroup object
        gemini_client: Gemini client
        structurer: OutputStructurer instance
        output_dir: Directory to save outputs
    
    Returns:
        GroupExtractionPlan: Structured plan
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"📋 Planning extraction for group: {column_group.name}")
    logger.info(f"   Columns: {len(column_group.columns)}")
    logger.info(f"{'='*80}")
    
    # Upload PDF
    logger.info("📤 Uploading PDF to Gemini...")
    pdf_bytes = Path(pdf_path).read_bytes()
    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    logger.info(f"   Size: {len(pdf_bytes) / 1024 / 1024:.2f} MB")
    
    # Format chunks and columns
    chunk_summaries = format_chunk_summaries(chunks)
    column_defs = "\n".join([
        f'{i+1}. Column: "{col.name}"\n   Definition: {col.definition}'
        for i, col in enumerate(column_group.columns)
    ])
    
    # Create free-form planning prompt
    prompt = f"""You are creating an extraction plan for a clinical trial data extraction task.

CONTEXT:
- You have the full PDF loaded and can see its structure
- Below are {len(chunks)} pre-extracted chunks (text, tables, figures)
- Your goal: For each column, identify IF the data exists, and if so, WHERE and HOW to extract it

AVAILABLE CHUNKS:
{chunk_summaries}

TASK: Create extraction plan for column group "{column_group.name}"

COLUMNS TO EXTRACT:
{column_defs}

FOR EACH COLUMN, provide:

1. **found_in_pdf**: Is this data present in the PDF? (boolean: true/false)
   - true: The data is reported somewhere in the PDF
   - false: The data is NOT reported/available in this paper
   
   IMPORTANT: Be honest about data availability. Not all papers report all metrics.

2. **page**: Which page number has this information?
   - If found: actual page number (integer)
   - If NOT found: use -1

3. **source_type**: Where is it located?
   - If found: "table", "text", or "figure"
   - If NOT found: "not_applicable"

4. **confidence**: How confident are you?
   - "high": Very certain (whether it's present OR absent)
   - "medium": Probably correct but should verify
   - "low": Unsure about presence/location

5. **extraction_plan**: 
   - If FOUND: Explain HOW to extract the value (be specific!):
     * What terminology does the paper use? (e.g., "ADT" instead of "Androgen Deprivation")
     * Is the value direct or needs aggregation? (e.g., "Sum High Volume + Low Volume")
     * Any special formatting? (e.g., "Reported as median (IQR)")
     * Which table/section specifically? (e.g., "Table 1 - Demographics, treatment column")
     * Any synonyms or alternate names? (e.g., "ECOG PS" vs "Performance Status")
   
   - If NOT FOUND: Explain why it's not available:
     * "Not reported in this paper"
     * "Only reported for subgroups, not overall"
     * "Data collection method not described"
     * etc.

IMPORTANT CONSIDERATIONS:
- NOT ALL DATA IS ALWAYS REPORTED - be honest about what's missing
- Some tables report STRATIFIED results (by volume/risk) - if column asks for "Overall", you need to aggregate subgroups
- Some columns are SPECIFIC to subgroups (e.g., "High Volume | Treatment") - extract only that value
- Related columns often share the same page/table
- Trial metadata (NCT ID, Trial name) usually on page 1
- Demographics usually in "Table 1" or "Baseline Characteristics" 
- Outcomes (OS, PFS, ORR) usually in "Results" tables (Table 2, 3, etc.)
- Adverse events usually in separate AE tables

Think carefully about each column. Be specific in your extraction plans.
Explain your reasoning clearly so someone else can follow your instructions.
"""
    
    # Call Gemini (free-form reasoning)
    logger.info("🤖 Calling Gemini for free-form planning...")
    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=4000
    )
    
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[pdf_part, prompt],
        config=config
    )
    
    free_form_plan = response.text.strip()
    logger.info(f"   Response length: {len(free_form_plan)} chars")
    
    # Save raw response
    raw_file = output_dir / f"{column_group.name.replace(' ', '_').replace('/', '_')}_raw.txt"
    raw_file.write_text(free_form_plan, encoding='utf-8')
    logger.info(f"💾 Saved raw plan to: {raw_file.name}")
    
    # Structure with local LLM
    logger.info("🔧 Structuring plan with local LLM...")
    
    # Create debug file for this group
    debug_file = output_dir / f"{column_group.name.replace(' ', '_').replace('/', '_')}_structurer_debug.txt"
    
    # Temporarily create structurer with debug enabled
    debug_structurer = OutputStructurer(
        base_url="http://localhost:8001/v1",
        model="Qwen/Qwen3-8B",
        enable_thinking=False,
        debug_file=str(debug_file)
    )
    
    structured_result = debug_structurer.structure(
        text=free_form_plan,
        schema=GroupExtractionPlan,
        max_retries=3,
        return_dict=False
    )
    
    if not structured_result.success:
        logger.error(f"❌ Structuring failed: {structured_result.error}")
        logger.error(f"   Debug output saved to: {debug_file.name}")
        raise ValueError(f"Failed to structure plan: {structured_result.error}")
    
    plan = structured_result.data
    logger.info(f"✅ Structured plan successfully")
    logger.info(f"   Parsed {len(plan.columns)} columns")
    
    # Fix: Ensure group_name is correct (not the schema class name)
    if plan.group_name == "GroupExtractionPlan":
        logger.warning(f"   ⚠️  Fixing incorrect group_name (was schema class name)")
        plan.group_name = column_group.name
        logger.info(f"   ✅ Corrected to: {plan.group_name}")
    
    # Validate found_in_pdf logic
    logger.info(f"🔍 Validating data availability logic...")
    for col_plan in plan.columns:
        if not col_plan.found_in_pdf:
            # Assert that page is -1 when not found
            assert col_plan.page == -1, (
                f"Column '{col_plan.column_name}': found_in_pdf=False but page={col_plan.page} "
                f"(expected -1). Please check structurer output."
            )
            # Assert source_type is not_applicable
            assert col_plan.source_type == "not_applicable", (
                f"Column '{col_plan.column_name}': found_in_pdf=False but source_type='{col_plan.source_type}' "
                f"(expected 'not_applicable'). Please check structurer output."
            )
    logger.info(f"   ✅ All columns pass validation")
    
    # Log summary
    logger.info(f"\n📊 Plan Summary:")
    found_count = sum(1 for c in plan.columns if c.found_in_pdf)
    not_found_count = len(plan.columns) - found_count
    logger.info(f"   Found in PDF: {found_count}/{len(plan.columns)}")
    logger.info(f"   Not found: {not_found_count}/{len(plan.columns)}")
    logger.info(f"\n   Column Details:")
    for col_plan in plan.columns:
        status_icon = "✓" if col_plan.found_in_pdf else "✗"
        logger.info(f"   {status_icon} {col_plan.column_name}")
        if col_plan.found_in_pdf:
            logger.info(f"     Page {col_plan.page} | {col_plan.source_type} | Confidence: {col_plan.confidence}")
        else:
            logger.info(f"     NOT FOUND | Confidence: {col_plan.confidence}")
        preview = col_plan.extraction_plan[:100].replace("\n", " ")
        logger.info(f"     Plan: {preview}...")
    
    # Save structured plan
    plan_dict = plan.model_dump()
    plan_file = output_dir / f"{column_group.name.replace(' ', '_').replace('/', '_')}_plan.json"
    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(plan_dict, f, indent=2)
    logger.info(f"💾 Saved structured plan to: {plan_file.name}")
    
    return plan


# ============== MAIN ==============

def main():
    parser = argparse.ArgumentParser(
        description="Generate extraction plans for column groups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test on one group
  python experiment-scripts/test_hierarchical_extraction.py \\
      --pdf "test_results/new/NCT.../NCT....pdf" \\
      --chunks "test_results/new/NCT.../pdf_chunked.json" \\
      --groups "Median Age (years)"
  
  # Test on multiple groups
  python experiment-scripts/test_hierarchical_extraction.py \\
      --pdf "test_results/new/NCT.../NCT....pdf" \\
      --chunks "test_results/new/NCT.../pdf_chunked.json" \\
      --groups "ID" "Median Age (years)" "Volume of disease - N (%)"
  
  # Test all groups
  python experiment-scripts/test_hierarchical_extraction.py \\
      --pdf "test_results/new/NCT.../NCT....pdf" \\
      --chunks "test_results/new/NCT.../pdf_chunked.json" \\
      --all
        """
    )
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--chunks", required=True, help="Path to pdf_chunked.json")
    parser.add_argument("--groups", nargs="+", help="Specific group names to test")
    parser.add_argument("--all", action="store_true", help="Test all groups")
    parser.add_argument("--output-dir", default=None,
                       help="Directory to save outputs (default: results/{pdf_name}/extraction_plans)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.groups and not args.all:
        parser.error("Must specify either --groups or --all")
    
    # Setup output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Auto-generate: results/{pdf_name}/extraction_plans
        pdf_path = Path(args.pdf)
        pdf_name = pdf_path.stem  # e.g., NCT02799602_Hussain_ARASENS_JCO'23
        output_dir = Path("results") / pdf_name / "extraction_plans"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load inputs
    logger.info("="*80)
    logger.info("🚀 HIERARCHICAL EXTRACTION PLANNING TEST")
    logger.info("="*80)
    logger.info(f"\n📂 Loading inputs...")
    
    if not Path(args.pdf).exists():
        logger.error(f"❌ PDF not found: {args.pdf}")
        return 1
    
    if not Path(args.chunks).exists():
        logger.error(f"❌ Chunks file not found: {args.chunks}")
        return 1
    
    chunks = json.loads(Path(args.chunks).read_text(encoding='utf-8'))
    all_column_groups = load_column_groups()  # Uses our helper function
    
    logger.info(f"   ✅ PDF: {Path(args.pdf).name}")
    logger.info(f"   ✅ Chunks: {len(chunks)} loaded")
    logger.info(f"   ✅ Total groups available: {len(all_column_groups)}")
    
    # Filter groups
    if args.all:
        column_groups = all_column_groups
        logger.info(f"   → Testing ALL {len(column_groups)} groups")
    else:
        column_groups = [g for g in all_column_groups if g.name in args.groups]
        if not column_groups:
            logger.error(f"❌ No matching groups found for: {args.groups}")
            logger.info(f"\nAvailable groups:")
            for g in all_column_groups:
                logger.info(f"   - {g.name}")
            return 1
        logger.info(f"   → Testing {len(column_groups)} selected groups")
    
    # Initialize clients
    logger.info(f"\n🔧 Initializing LLM clients...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not set")
        return 1
    
    gemini_client = genai.Client(api_key=api_key)
    structurer = OutputStructurer(
        base_url="http://localhost:8001/v1",
        model="Qwen/Qwen3-8B",
        enable_thinking=False  # Disable <think> tags for cleaner JSON output
    )
    logger.info("   ✅ Gemini client initialized")
    logger.info("   ✅ Local structurer initialized (thinking disabled)")
    
    # Generate plans
    logger.info(f"\n{'='*80}")
    logger.info(f"🎯 Generating extraction plans...")
    logger.info(f"{'='*80}")
    
    success_count = 0
    failed_groups = []
    
    for i, group in enumerate(column_groups, 1):
        logger.info(f"\n[{i}/{len(column_groups)}] Processing: {group.name}")
        
        try:
            plan = generate_extraction_plan(
                pdf_path=args.pdf,
                chunks=chunks,
                column_group=group,
                gemini_client=gemini_client,
                structurer=structurer,
                output_dir=output_dir
            )
            success_count += 1
            logger.info(f"✅ Success!")
        
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            failed_groups.append(group.name)
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"✅ Successful: {success_count}/{len(column_groups)}")
    if failed_groups:
        logger.info(f"❌ Failed: {len(failed_groups)}")
        for name in failed_groups:
            logger.info(f"   - {name}")
    
    logger.info(f"\n💾 Output directory: {output_dir}")
    logger.info(f"   Raw plans: *_raw.txt")
    logger.info(f"   Structured plans: *_plan.json")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ COMPLETE!")
    logger.info(f"{'='*80}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

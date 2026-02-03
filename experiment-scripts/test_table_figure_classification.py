#!/usr/bin/env python3
"""
Test script: LLM-based PDF page classification for tables and figures.

This script:
1. Uploads PDF to Gemini
2. Uses multi-turn chat to identify tables and figures
3. Structures responses with local LLM
4. Outputs structured JSON metadata

Usage:
    python experiment-scripts/test_pdf_classification.py <pdf_path>
"""
import sys
import json
import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google import genai
from google.genai import types
from src.LLMProvider.structurer import OutputStructurer


# ============== PYDANTIC SCHEMAS ==============

class TableInfo(BaseModel):
    """Information about a table in the PDF."""
    page: int = Field(..., description="Page number where table is located")
    name: str = Field(..., description="Table name/number (e.g., 'Table 1')")
    description: str = Field(default="", description="Brief caption or description of table content")


class FigureInfo(BaseModel):
    """Information about a figure in the PDF."""
    page: int = Field(..., description="Page number where figure is located")
    name: str = Field(..., description="Figure name/number (e.g., 'Figure 1/Fig 1/'), Might be abbreviated as 'Fig'")
    description: str = Field(default="", description="Brief description (e.g., 'survival curve', 'forest plot')")


class TablesResponse(BaseModel):
    """Structured response for tables classification."""
    tables: List[TableInfo] = Field(default_factory=list, description="List of tables found in PDF")


class FiguresResponse(BaseModel):
    """Structured response for figures classification."""
    figures: List[FigureInfo] = Field(default_factory=list, description="List of figures found in PDF")


# ============== CLASSIFICATION FUNCTIONS ==============

def classify_tables_and_figures(pdf_path: str, verbose: bool = True):
    """
    Classify PDF pages for tables and figures using Gemini multi-turn chat.
    
    Args:
        pdf_path: Path to PDF file
        verbose: Print progress messages
    
    Returns:
        dict with "tables" and "figures" lists
    """
    if verbose:
        print("\n" + "="*80)
        print("STEP 1: Gemini Classification (Multi-turn Chat)")
        print("="*80)
    
    # Read PDF as bytes
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    if verbose:
        print(f"\n📄 Loading PDF: {pdf_path_obj.name}")
        print(f"   Size: {pdf_path_obj.stat().st_size / 1024 / 1024:.2f} MB")
    
    pdf_bytes = pdf_path_obj.read_bytes()
    
    # Initialize Gemini client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    client = genai.Client(api_key=api_key)
    
    # Create PDF part
    pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    
    if verbose:
        print("\n🤖 Starting Gemini chat session...")
    
    # TURN 1: Identify tables
    if verbose:
        print("\n📋 Turn 1: Asking about tables...")
    
    tables_prompt = """Analyze this clinical trial PDF and identify ALL pages that contain data tables.

For each table you find, provide:
- Page number (exact integer)
- Table name or number (e.g., "Table 1", "Table 2")
- Brief caption or description of what data the table contains

List them clearly, one per line, in this format:
Page X: Table Y - [brief description]

If no tables are found, respond with "No tables found".

Be thorough - check all pages."""
    
    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=2000
    )
    
    response_tables = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[pdf_part, tables_prompt],
        config=config
    )
    
    tables_free_form = response_tables.text.strip()
    
    if verbose:
        print(f"\n📤 Gemini response (tables):")
        print("-" * 80)
        print(tables_free_form[:500] + "..." if len(tables_free_form) > 500 else tables_free_form)
        print("-" * 80)
    
    # TURN 2: Identify figures
    # Note: For multi-turn, we need to create a new call with conversation history
    if verbose:
        print("\n📊 Turn 2: Asking about figures...")
    
    figures_prompt = """Now, identify ALL pages that contain figures, graphs, or diagrams.

For each figure you find, provide:
- Page number (exact integer)
- Figure name or number (e.g., "Figure 1", "Figure 2")
- Brief description of the figure type (e.g., "Kaplan-Meier survival curve", "Forest plot", "CONSORT diagram")

List them clearly, one per line, in this format:
Page X: Figure Y - [brief description]

If no figures are found, respond with "No figures found".

Be thorough - check all pages."""
    
    response_figures = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[pdf_part, figures_prompt],
        config=config
    )
    
    figures_free_form = response_figures.text.strip()
    
    if verbose:
        print(f"\n📤 Gemini response (figures):")
        print("-" * 80)
        print(figures_free_form[:500] + "..." if len(figures_free_form) > 500 else figures_free_form)
        print("-" * 80)
    
    return {
        "tables_free_form": tables_free_form,
        "figures_free_form": figures_free_form
    }


def structure_responses(responses: dict, verbose: bool = True):
    """
    Structure free-form responses using local LLM structurer.
    
    Args:
        responses: Dict with "tables_free_form" and "figures_free_form"
        verbose: Print progress messages
    
    Returns:
        dict with "tables" and "figures" lists
    """
    if verbose:
        print("\n" + "="*80)
        print("STEP 2: Local LLM Structuring")
        print("="*80)
    
    # Structure tables response
    if verbose:
        print("\n📋 Structuring tables response...")
    
    # DEBUG: Save input for tables too (for comparison)
    debug_tables_file = Path("debug_tables_structuring.txt")
    with open(debug_tables_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("INPUT TO STRUCTURER (Gemini's free-form response):\n")
        f.write("="*80 + "\n")
        f.write(responses["tables_free_form"])
        f.write("\n\n")
    
    tables_structurer = OutputStructurer(
        base_url="http://localhost:8001/v1",
        model="Qwen/Qwen3-8B",
        debug_file=str(debug_tables_file),
        enable_thinking=False  # Disable thinking for cleaner JSON
    )
    
    tables_result = tables_structurer.structure(
        text=responses["tables_free_form"],
        schema=TablesResponse,
        max_retries=3,
        return_dict=True
    )
    
    # DEBUG: Log output from tables structurer
    with open(debug_tables_file, 'a') as f:
        f.write("="*80 + "\n")
        f.write("OUTPUT FROM STRUCTURER:\n")
        f.write("="*80 + "\n")
        f.write(f"Success: {tables_result.success}\n")
        f.write(f"Attempts: {tables_result.attempts}\n")
        f.write(f"Error: {tables_result.error}\n")
        f.write(f"Data: {json.dumps(tables_result.data, indent=2)}\n")
    
    if not tables_result.success:
        print(f"❌ Failed to structure tables: {tables_result.error}")
        tables_data = []
    else:
        tables_data = tables_result.data.get("tables", [])
        if verbose:
            print(f"✅ Structured {len(tables_data)} tables (attempts: {tables_result.attempts})")
            print(f"🐛 Debug info saved to: {debug_tables_file}")
    
    # Structure figures response
    if verbose:
        print("\n📊 Structuring figures response...")
    
    # DEBUG: Save input to structurer and setup debug logging
    debug_file = Path("debug_figures_structuring.txt")
    with open(debug_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("INPUT TO STRUCTURER (Gemini's free-form response):\n")
        f.write("="*80 + "\n")
        f.write(responses["figures_free_form"])
        f.write("\n\n")
    
    # Create new structurer with debug enabled for figures
    figures_structurer = OutputStructurer(
        base_url="http://localhost:8001/v1",
        model="Qwen/Qwen3-8B",
        debug_file=str(debug_file),
        enable_thinking=False  # Disable thinking for cleaner JSON
    )
    
    figures_result = figures_structurer.structure(
        text=responses["figures_free_form"],
        schema=FiguresResponse,
        max_retries=3,
        return_dict=True
    )
    
    # DEBUG: Log output from structurer
    with open(debug_file, 'a') as f:
        f.write("="*80 + "\n")
        f.write("OUTPUT FROM STRUCTURER:\n")
        f.write("="*80 + "\n")
        f.write(f"Success: {figures_result.success}\n")
        f.write(f"Attempts: {figures_result.attempts}\n")
        f.write(f"Error: {figures_result.error}\n")
        f.write(f"Data: {json.dumps(figures_result.data, indent=2)}\n")
    
    if not figures_result.success:
        print(f"❌ Failed to structure figures: {figures_result.error}")
        figures_data = []
    else:
        figures_data = figures_result.data.get("figures", [])
        if verbose:
            print(f"✅ Structured {len(figures_data)} figures (attempts: {figures_result.attempts})")
            print(f"🐛 Debug info saved to: {debug_file}")
    
    return {
        "tables": tables_data,
        "figures": figures_data
    }


def print_results(metadata: dict):
    """Print formatted results."""
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    
    tables = metadata.get("tables", [])
    figures = metadata.get("figures", [])
    
    print(f"\n📋 TABLES FOUND: {len(tables)}")
    if tables:
        for table in tables:
            print(f"   Page {table['page']:2d}: {table['name']}")
            if table.get('description'):
                print(f"              {table['description'][:70]}...")
    else:
        print("   None")
    
    print(f"\n📊 FIGURES FOUND: {len(figures)}")
    if figures:
        for figure in figures:
            print(f"   Page {figure['page']:2d}: {figure['name']}")
            if figure.get('description'):
                print(f"              {figure['description'][:70]}...")
    else:
        print("   None")
    
    # Page summary
    table_pages = sorted(set(t['page'] for t in tables))
    figure_pages = sorted(set(f['page'] for f in figures))
    both_pages = sorted(set(table_pages) & set(figure_pages))
    
    print(f"\n📄 PAGE SUMMARY:")
    print(f"   Pages with tables: {table_pages}")
    print(f"   Pages with figures: {figure_pages}")
    if both_pages:
        print(f"   Pages with BOTH: {both_pages}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_pdf_classification.py <pdf_path>")
        print("\nExample:")
        print("  python experiment-scripts/test_pdf_classification.py dataset/NCT02799602_Hussain_ARASENS_JCO'23.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print("\n🧪 PDF Page Classification Test")
    print("="*80)
    print(f"PDF: {pdf_path}")
    print("="*80)
    
    try:
        # Step 1: Gemini classification
        responses = classify_tables_and_figures(pdf_path, verbose=True)
        
        # Step 2: Structure with local LLM
        metadata = structure_responses(responses, verbose=True)
        
        # Step 3: Print results
        print_results(metadata)
        
        # Step 4: Save output
        output_path = Path(pdf_path).parent / "page_metadata.json"
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_path}")
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETE!")
        print("="*80)
        
        return 0
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

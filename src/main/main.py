# main/main.py
import os
import sys
import shutil
import json
from pathlib import Path

# --------------------------------------------------------------
# 1. Resolve project root and fix sys.path
# --------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # Map_and_Make
SRC_FOLDER = PROJECT_ROOT / "src"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_FOLDER))
# --------------------------------------------------------------
# 2. Imports (now guaranteed to work)
# --------------------------------------------------------------
from src.chunking.chunking import process_pdf
from table_definitions.definitions import load_definitions
from src.fill_table.fill_table import fill_table_all_chunks
from src.utils.logging_utils import setup_logger

logger = setup_logger("main")


if __name__ == "__main__":
    pdf_path = input("Enter the full path of your local research paper PDF: ").strip()
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print("PDF not found.")
        sys.exit(1)

    # ------------------- Output folder -------------------
    out_dir = PROJECT_ROOT / "test_results" / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    copied_pdf   = out_dir / f"{pdf_path.stem}.pdf"
    chunk_json   = out_dir / "pdf_chunked.json"
    table_csv    = out_dir / "extracted_table.csv"
    meta_json    = out_dir / "extraction_metadata.json"

    # ------------------- Copy PDF -------------------
    shutil.copy2(pdf_path, copied_pdf)
    print(f"PDF copied to {copied_pdf}")

    # ------------------- Chunk -------------------
    logger.info("Chunking PDF...")
    process_pdf(str(pdf_path), output_path=str(chunk_json))
    with open(chunk_json, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Chunked JSON saved to {chunk_json}")

    # ------------------- Load groups (from config) -------------------
    groups = load_definitions()          # picks up DEFINITIONS_CSV_PATH from config
    logger.info(f"Loaded {len(groups)} column groups")

    # ------------------- Fill table -------------------
    logger.info("Running LLM extraction...")
    fill_table_all_chunks(
        chunks=chunks,
        groups=groups,
        pdf_path=str(pdf_path),
        output_path=str(table_csv),
        metadata_path=str(meta_json)
    )
    # print(f"Table CSV saved to {table_csv}")
    # print(f"Metadata JSON saved to {meta_json}")

    # ------------------- Summary -------------------
    print("\n" + "="*60)
    print("ALL DONE!")
    print(f"Folder : {out_dir}")
    print(f"   PDF : {copied_pdf.name}")
    print(f"   JSON: {chunk_json.name}")
    print(f"   CSV : {table_csv.name}")
    print(f"   Meta: {meta_json.name}")
    print("="*60)
# main/main.py
# (Updated to store context_text and integrate performance monitoring/logging flow)
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
from src.fill_table.fill_table import fill_table_all_chunks, fill_table_with_retrieval, extract_first_n_pages_text
from src.evaluation.evaluator import Evaluator
from src.config.config import GOLD_TABLE_PATH, USE_RETRIEVAL
from src.utils.logging_utils import setup_logger
from src.model_handling.llm_extraction import save_cost_metrics  # Adjusted import path

logger = setup_logger("main")


def prompt_menu():
    print("\nSelect pipeline stage to run:")
    print("1. Chunking only")
    print("2. Table filling only")
    print("3. Evaluation only")
    print("4. Complete pipeline (all steps)")
    while True:
        choice = input("Enter 1, 2, 3, or 4: ").strip()
        if choice in {"1", "2", "3", "4"}:
            return int(choice)
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    pdf_path = input("Enter the full path of your local research paper PDF: ").strip()
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        print("PDF not found.")
        sys.exit(1)

    # ------------------- Output folder -------------------
    out_dir = PROJECT_ROOT / "test_results" / "new" / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    copied_pdf   = out_dir / f"{pdf_path.stem}.pdf"
    chunk_json   = out_dir / "pdf_chunked.json"
    table_csv    = out_dir / "extracted_table.csv"
    meta_json    = out_dir / "extraction_metadata.json"
    context_txt  = out_dir / "context_text.txt"  # DEPRECATED - kept for backwards compatibility
    extraction_guide = out_dir / "extraction_guide.txt"  # NEW - structured extraction guide

    metrics_dir = out_dir / "metrics"
    metrics_dir.mkdir(exist_ok=True)

    # ------------------- Menu -------------------
    stage = prompt_menu()

    # ------------------- 1. Chunking -------------------
    if stage == 1 or stage == 4:
        shutil.copy2(pdf_path, copied_pdf)
        print(f"PDF copied to {copied_pdf}")
        logger.info("Chunking PDF...")
        process_pdf(str(pdf_path), output_path=str(chunk_json))
        with open(chunk_json, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        print(f"Chunked JSON saved to {chunk_json}")

        # Save context for downstream steps
        context_text = extract_first_n_pages_text(str(pdf_path), n=2)
        with open(context_txt, "w", encoding="utf-8") as f:
            f.write(context_text)
        logger.info(f"Context (first 2 pages) saved to {context_txt}")

    # ------------------- 2. Table Filling -------------------
    if stage == 2 or stage == 4:
        # Load chunks if not already loaded
        if not chunk_json.exists():
            print(f"Chunked JSON not found: {chunk_json}. Please run chunking first.")
            sys.exit(1)
        with open(chunk_json, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        groups = load_definitions()
        logger.info(f"Loaded {len(groups)} column groups")
        
        # Choose extraction method based on config
        if USE_RETRIEVAL:
            logger.info("🔍 Running RETRIEVAL-BASED extraction (one LLM call per group)...")
            output_data, metrics = fill_table_with_retrieval(
                chunks=chunks,
                groups=groups,
                pdf_path=str(pdf_path),
                output_path=str(table_csv),
                metadata_path=str(meta_json)
            )
        else:
            logger.info("🔄 Running BRUTE-FORCE extraction (all chunks, parallel)...")
            output_data, metrics = fill_table_all_chunks(
                chunks=chunks,
                groups=groups,
                pdf_path=str(pdf_path),
                output_path=str(table_csv),
                metadata_path=str(meta_json)
            )
        # Save LLM cost metrics
        cost_file = metrics_dir / "llm_cost_metrics.txt"
        try:
            from src.model_handling.llm_extraction import save_cost_metrics
            save_cost_metrics(str(cost_file), metrics)
            logger.info(f"💰 LLM metrics saved to {cost_file}")
            logger.info(f"   Total tokens: {metrics.get('input_tokens', 0)} input, {metrics.get('output_tokens', 0)} output")
        except Exception as e:
            logger.error(f"❌ Failed to save LLM cost metrics: {e}")

    # ------------------- 3. Evaluation -------------------
    if stage == 3 or stage == 4:
        if not table_csv.exists():
            print(f"Extracted table not found: {table_csv}. Please run table filling first.")
            sys.exit(1)
        gold_table = PROJECT_ROOT / GOLD_TABLE_PATH
        if gold_table.exists():
            try:
                logger.info("Running evaluation against gold labels...")
                evaluator = Evaluator(
                    extracted_csv=table_csv,
                    gold_csv=gold_table,
                    pdf_name=pdf_path.stem,
                    output_dir=metrics_dir
                )
                eval_results = evaluator.evaluate()
                logger.info(f"✅ Overall Accuracy: {eval_results['overall_accuracy']:.2f}%")
                logger.info(f"✅ Non-null Accuracy: {eval_results['non_null_accuracy']:.2f}%")
                print(f"\nEvaluation results saved in: {metrics_dir}")
                print(f"  - evaluation_results.txt (full LLM output)")
                print(f"  - evaluation_summary.json (metrics)")
                print(f"  - non_null_evaluation.txt (non-null columns only)")
            except ValueError as e:
                logger.warning(f"⚠️ Evaluation skipped: {e}")
            except Exception as e:
                logger.error(f"❌ Evaluation failed: {e}")
        else:
            logger.info("⚠️ No gold table found, skipping evaluation")

    # ------------------- Summary -------------------
    print("\n" + "="*60)
    print("ALL DONE!")
    print(f"Folder : {out_dir}")
    if copied_pdf.exists():
        print(f"   PDF : {copied_pdf.name}")
    if chunk_json.exists():
        print(f"   JSON: {chunk_json.name}")
    if table_csv.exists():
        print(f"   CSV : {table_csv.name}")
    if meta_json.exists():
        print(f"   Meta: {meta_json.name}")
    if extraction_guide.exists():
        print(f"   Guide: {extraction_guide.name}")
    if context_txt.exists():
        print(f"   Context (deprecated): {context_txt.name}")
    if metrics_dir.exists():
        print(f"   Eval: metrics/evaluation_summary.json")
        print(f"   Eval (full): metrics/evaluation_results.txt")
        print(f"   Eval (non-null): metrics/non_null_evaluation.txt")
    print("="*60)
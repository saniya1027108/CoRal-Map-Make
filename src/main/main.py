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
from src.fill_table.fill_table import fill_table_all_chunks, extract_first_n_pages_text  # Import extract_first_n_pages_text
from src.evaluation.evaluator import Evaluator
from src.config.config import GOLD_TABLE_PATH, COST_PER_1K_INPUT, COST_PER_1K_OUTPUT
from src.utils.logging_utils import setup_logger
from src.model_handling.llm_extraction import save_cost_metrics  # Adjusted import path

logger = setup_logger("main")


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
    context_txt  = out_dir / "context_text.txt"  # New: Store context

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

    # ------------------- Extract and store context -------------------
    context_text = extract_first_n_pages_text(str(pdf_path), n=2)
    with open(context_txt, "w", encoding="utf-8") as f:
        f.write(context_text)
    logger.info(f"Context (first 2 pages) saved to {context_txt}")

    # ------------------- Fill table -------------------
    logger.info("Running LLM extraction (parallel over group-chunk pairs)...")
    output_data, metrics = fill_table_all_chunks(
        chunks=chunks,
        groups=groups,
        pdf_path=str(pdf_path),
        output_path=str(table_csv),
        metadata_path=str(meta_json)
    )

    # ------------------- Evaluation -------------------
    gold_table = PROJECT_ROOT / GOLD_TABLE_PATH
    if gold_table.exists():
        try:
            logger.info("Running evaluation against gold labels...")
            evaluator = Evaluator(
                extracted_csv=table_csv,
                gold_csv=gold_table,
                pdf_name=pdf_path.stem,
                output_dir=out_dir / "metrics"
            )
            eval_results = evaluator.evaluate()
            
            logger.info(f"✅ Overall Accuracy: {eval_results['overall_accuracy']:.2f}%")
            logger.info(f"✅ Non-null Accuracy: {eval_results['non_null_accuracy']:.2f}%")
        except ValueError as e:
            logger.warning(f"⚠️ Evaluation skipped: {e}")
        except Exception as e:
            logger.error(f"❌ Evaluation failed: {e}")
    else:
        logger.info("⚠️ No gold table found, skipping evaluation")

    # ------------------- Save LLM Cost Metrics -------------------
    metrics_dir = out_dir / "metrics"
    metrics_dir.mkdir(exist_ok=True)   # Ensure folder exists

    cost_file = metrics_dir / "llm_cost_metrics.txt"
    try:
        # Compute total cost
        total_cost = (
            (metrics["input_tokens"] / 1000.0) * COST_PER_1K_INPUT +
            (metrics["output_tokens"] / 1000.0) * COST_PER_1K_OUTPUT
        )
        metrics["total_cost_usd"] = round(total_cost, 4)
        
        save_cost_metrics(str(cost_file), metrics)
        logger.info(f"💰 LLM cost metrics saved to {cost_file}")
    except Exception as e:
        logger.error(f"❌ Failed to save LLM cost metrics: {e}")
        
    # ------------------- Summary -------------------
    print("\n" + "="*60)
    print("ALL DONE!")
    print(f"Folder : {out_dir}")
    print(f"   PDF : {copied_pdf.name}")
    print(f"   JSON: {chunk_json.name}")
    print(f"   CSV : {table_csv.name}")
    print(f"   Meta: {meta_json.name}")
    print(f"   Context: {context_txt.name}")
    if (out_dir / "metrics").exists():
        print(f"   Eval: metrics/evaluation_summary.json")
    print("="*60)
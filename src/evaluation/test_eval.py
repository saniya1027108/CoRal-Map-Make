#!/usr/bin/env python
"""Quick script to run evaluation only on existing extraction results."""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.evaluator import Evaluator
from src.config.config import GOLD_TABLE_PATH
from src.utils.logging_utils import setup_logger

logger = setup_logger("test_eval")

if __name__ == "__main__":
    # Path to the extraction results
    pdf_name = "NCT00268476_James_STAMPEDE_NEJM'17"
    result_dir = PROJECT_ROOT / "test_results" / pdf_name
    
    extracted_csv = result_dir / "extracted_table.csv"
    output_dir = result_dir / "metrics"
    
    if not extracted_csv.exists():
        print(f"❌ Extracted CSV not found: {extracted_csv}")
        sys.exit(1)
    
    if not GOLD_TABLE_PATH.exists():
        print(f"❌ Gold table not found: {GOLD_TABLE_PATH}")
        sys.exit(1)
    
    logger.info(f"Running evaluation for: {pdf_name}")
    logger.info(f"Extracted CSV: {extracted_csv}")
    logger.info(f"Gold CSV: {GOLD_TABLE_PATH}")
    
    try:
        evaluator = Evaluator(
            extracted_csv=extracted_csv,
            gold_csv=GOLD_TABLE_PATH,
            pdf_name=pdf_name,
            output_dir=output_dir
        )
        
        results = evaluator.evaluate()
        
        print("\n" + "="*60)
        print("EVALUATION RESULTS")
        print("="*60)
        print(f"Overall Accuracy: {results['overall_accuracy']:.2f}%")
        print(f"  Correct: {results['correct_columns']}/{results['total_columns']}")
        print()
        print(f"Non-null Accuracy: {results['non_null_accuracy']:.2f}%")
        print(f"  Correct: {results['non_null_correct']}/{results['non_null_total']}")
        print("="*60)
        print(f"\nResults saved to: {output_dir}")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

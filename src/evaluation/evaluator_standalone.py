#!/usr/bin/env python3
"""
Standalone evaluation script for quick evaluation of extracted tables.

Usage (run from src directory):
    python evaluation/evaluator_standalone.py
"""
import sys
import json
from pathlib import Path

# Resolve project root and fix sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_FOLDER = PROJECT_ROOT / "src"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_FOLDER))

from src.evaluation.evaluator import Evaluator
from src.config.config import GOLD_TABLE_PATH
from src.utils.logging_utils import setup_logger

logger = setup_logger("evaluator_standalone")


def print_metrics(results: dict):
    """Print evaluation metrics to console."""
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    print(f"Provider: {results.get('evaluation_provider', 'N/A')}/{results.get('evaluation_model', 'N/A')}")
    print(f"\nOverall Accuracy:")
    print(f"  Total Columns: {results.get('total_columns', 0)}")
    print(f"  Correct Columns: {results.get('correct_columns', 0)}")
    print(f"  Accuracy: {results.get('overall_accuracy', 0.0):.2f}%")
    print(f"\nNon-null Accuracy:")
    print(f"  Non-null Gold Columns: {results.get('non_null_total', 0)}")
    print(f"  Non-null Correct Columns: {results.get('non_null_correct', 0)}")
    print(f"  Accuracy: {results.get('non_null_accuracy', 0.0):.2f}%")
    print(f"\nToken Usage:")
    print(f"  Input Tokens: {results.get('total_input_tokens', 0):,}")
    print(f"  Output Tokens: {results.get('total_output_tokens', 0):,}")
    if results.get('missing_columns', 0) > 0:
        print(f"\n⚠️  Missing Columns: {results.get('missing_columns', 0)}")
    print("="*60 + "\n")


def main():
    print("\n" + "="*60)
    print("STANDALONE EVALUATION")
    print("="*60)
    
    # Get PDF name
    pdf_name = input("\nEnter PDF name (without .pdf extension): ").strip()
    if not pdf_name:
        print("❌ Error: PDF name is required")
        sys.exit(1)
    
    # Get CSV path
    csv_path = input("Enter path to extracted CSV file: ").strip()
    if not csv_path:
        print("❌ Error: CSV path is required")
        sys.exit(1)
    
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Validate gold table exists
    if not GOLD_TABLE_PATH.exists():
        print(f"❌ Error: Gold table not found: {GOLD_TABLE_PATH}")
        sys.exit(1)
    
    # Create temporary output directory (we'll save to user-specified path later)
    temp_output = PROJECT_ROOT / "test_results" / "new" / pdf_name / "metrics"
    temp_output.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📊 Running evaluation...")
    print(f"   PDF Name: {pdf_name}")
    print(f"   Extracted CSV: {csv_path}")
    print(f"   Gold Table: {GOLD_TABLE_PATH}")
    
    try:
        # Create evaluator
        evaluator = Evaluator(
            extracted_csv=str(csv_path),
            gold_csv=str(GOLD_TABLE_PATH),
            pdf_name=pdf_name,
            output_dir=str(temp_output),
            batch_size=40
        )
        
        # Run evaluation
        results = evaluator.evaluate()
        
        # Print metrics to console
        print_metrics(results)
        
        # Ask user for output path
        output_path = input("\nEnter path to save results JSON (or press Enter to skip): ").strip()
        
        if output_path:
            output_path = Path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save results as JSON
            json_filename = f"standalone_eval_{pdf_name}.json"
            json_path = output_path / json_filename
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4)
            
            print(f"✅ Results saved to: {json_path}")
        else:
            print("⏭️  Skipping save (results are in temporary directory)")
        
        return 0
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        print(f"❌ Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())

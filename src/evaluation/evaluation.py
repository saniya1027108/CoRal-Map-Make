# src/evaluation/evaluation.py
"""
Legacy helper functions and utilities for evaluation.
"""
import re
import os
from pathlib import Path
from ..utils.logging_utils import setup_logger

logger = setup_logger("evaluation_utils")


def calculate_accuracy_from_file(file_path: str) -> dict:
    """
    Calculate accuracy metrics from an evaluation results file.
    
    Args:
        file_path: Path to evaluation results file
    
    Returns:
        dict with accuracy metrics
    """
    NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
    value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)

    correct = total = 0
    non_null_correct = non_null_total = 0

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        # Overall accuracy
        if "Not Equivalent" in line and "=>" in line:
            total += 1
        elif "Equivalent" in line and "=>" in line and "Not Equivalent" not in line:
            total += 1
            correct += 1

        # Non-null accuracy
        match = value_pattern.search(line)
        if match:
            gold_val = match.group(1).strip()
            if gold_val.lower() not in NULL_TOKENS:
                non_null_total += 1
                if "Equivalent" in line and "Not Equivalent" not in line:
                    non_null_correct += 1

    overall_acc = (correct / total * 100) if total else 0.0
    non_null_acc = (non_null_correct / non_null_total * 100) if non_null_total else 0.0

    return {
        "total": total,
        "correct": correct,
        "overall_accuracy": overall_acc,
        "non_null_total": non_null_total,
        "non_null_correct": non_null_correct,
        "non_null_accuracy": non_null_acc
    }


def verify_all_columns_evaluated(evaluation_file: str, expected_columns: list) -> dict:
    """
    Verify that all expected columns are present in the evaluation file.
    
    Args:
        evaluation_file: Path to evaluation results file
        expected_columns: List of column names that should be evaluated
    
    Returns:
        dict with verification results
    """
    with open(evaluation_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    evaluated_columns = set()
    
    # Extract column names from evaluation (format: "Column Name: ... => ...")
    for line in content.split('\n'):
        if "=>" in line:
            match = re.match(r"^([^:]+):", line)
            if match:
                col_name = match.group(1).strip()
                evaluated_columns.add(col_name)
    
    missing_columns = [col for col in expected_columns if col not in evaluated_columns]
    extra_columns = [col for col in evaluated_columns if col not in expected_columns]
    
    is_complete = len(missing_columns) == 0
    
    return {
        "is_complete": is_complete,
        "total_expected": len(expected_columns),
        "total_evaluated": len(evaluated_columns),
        "missing_columns": missing_columns,
        "missing_count": len(missing_columns),
        "extra_columns": extra_columns,
        "extra_count": len(extra_columns)
    }


def combine_batch_results(batch_files: list, output_file: str):
    """
    Combine multiple batch evaluation files into a single file.
    
    Args:
        batch_files: List of paths to batch evaluation files
        output_file: Path to save combined results
    """
    with open(output_file, "w", encoding="utf-8") as out_f:
        for i, batch_file in enumerate(batch_files):
            if i > 0:
                out_f.write("\n\n" + "="*60 + "\n\n")
            
            batch_num = i + 1
            out_f.write(f"BATCH {batch_num}\n")
            out_f.write("="*60 + "\n")
            
            with open(batch_file, "r", encoding="utf-8") as in_f:
                out_f.write(in_f.read())
    
    logger.info(f"Combined {len(batch_files)} batch files into {output_file}")


def extract_batch_metrics(evaluation_file: str) -> list:
    """
    Extract per-batch metrics from a combined evaluation file.
    
    Args:
        evaluation_file: Path to evaluation results file with batch markers
    
    Returns:
        List of dicts containing metrics for each batch
    """
    with open(evaluation_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split by batch markers
    batches = re.split(r"BATCH \d+\n=+\n", content)
    
    batch_metrics = []
    NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
    value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)
    
    for i, batch_content in enumerate(batches[1:], 1):  # Skip first split (before first batch)
        total = correct = 0
        non_null_total = non_null_correct = 0
        
        for line in batch_content.split('\n'):
            # Overall accuracy
            if "Not Equivalent" in line and "=>" in line:
                total += 1
            elif "Equivalent" in line and "=>" in line and "Not Equivalent" not in line:
                total += 1
                correct += 1
            
            # Non-null accuracy
            match = value_pattern.search(line)
            if match:
                gold_val = match.group(1).strip()
                if gold_val.lower() not in NULL_TOKENS:
                    non_null_total += 1
                    if "Equivalent" in line and "Not Equivalent" not in line:
                        non_null_correct += 1
        
        overall_acc = (correct / total * 100) if total > 0 else 0.0
        non_null_acc = (non_null_correct / non_null_total * 100) if non_null_total > 0 else 0.0
        
        batch_metrics.append({
            "batch_num": i,
            "total": total,
            "correct": correct,
            "overall_accuracy": overall_acc,
            "non_null_total": non_null_total,
            "non_null_correct": non_null_correct,
            "non_null_accuracy": non_null_acc
        })
    
    return batch_metrics
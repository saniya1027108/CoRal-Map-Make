# src/evaluation/evaluation.py
# Legacy helper functions - kept for backward compatibility
# Main evaluation logic moved to evaluator.py

import re
import os


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

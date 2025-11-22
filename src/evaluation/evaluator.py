# src/evaluation/evaluator.py
import re
import json
import pandas as pd
from pathlib import Path
from ..utils.llm_utils import ask_llm_text
from ..config.config import EVALUATION_MODEL, EVALUATION_PROMPT_PATH
from ..utils.logging_utils import setup_logger

logger = setup_logger("evaluator")


class Evaluator:
    """
    Evaluates extracted CSV against gold labels using LLM-as-judge.
    """
    
    def __init__(self, extracted_csv, gold_csv, pdf_name, output_dir):
        """
        Args:
            extracted_csv: Path to extracted table CSV
            gold_csv: Path to gold standard CSV
            pdf_name: Name of PDF (stem, without extension)
            output_dir: Directory to save evaluation results
        """
        self.extracted_csv = Path(extracted_csv)
        self.gold_csv = Path(gold_csv)
        self.pdf_name = pdf_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.extracted_data = None
        self.gold_data = None
        self.comparison_text = None
        self.llm_response = None
        self.results = {}
    
    def _load_data(self):
        """Load extracted and gold CSVs, match by document name."""
        logger.info(f"Loading extracted data from {self.extracted_csv}")
        extracted_df = pd.read_csv(self.extracted_csv)
        
        logger.info(f"Loading gold data from {self.gold_csv}")
        gold_df = pd.read_csv(self.gold_csv)
        
        # Match by document name (add .pdf extension if needed)
        doc_name = self.pdf_name if self.pdf_name.endswith('.pdf') else f"{self.pdf_name}.pdf"
        
        gold_row = gold_df[gold_df['Document Name'] == doc_name]
        
        if gold_row.empty:
            raise ValueError(f"No gold label found for document: {doc_name}")
        
        # Convert to dict (first row only)
        self.extracted_data = extracted_df.iloc[0].to_dict()
        self.gold_data = gold_row.iloc[0].to_dict()
        
        logger.info(f"Matched document: {doc_name}")
        logger.info(f"Extracted columns: {len(self.extracted_data)}")
        logger.info(f"Gold columns: {len(self.gold_data)}")
    
    def _build_comparison_prompt(self):
        """Build column-by-column comparison text."""
        lines = []
        
        # Only compare columns that exist in both datasets
        common_columns = set(self.extracted_data.keys()) & set(self.gold_data.keys())
        
        # Remove metadata columns
        exclude_cols = {'Document Name', 'NCT', 'PubMed ID', 'Trial Name', 'Author', 'Year'}
        common_columns = common_columns - exclude_cols
        
        for col in sorted(common_columns):
            gold_val = self.gold_data.get(col, "not present")
            extracted_val = self.extracted_data.get(col, "not present")
            
            # Handle NaN/None values
            if pd.isna(gold_val):
                gold_val = "not present"
            if pd.isna(extracted_val):
                extracted_val = "not present"
            
            lines.append(f"{col}: {gold_val}, {extracted_val}")
        
        self.comparison_text = "\n".join(lines)
        logger.info(f"Built comparison for {len(lines)} columns")
    
    def _call_llm_judge(self):
        """Call LLM to evaluate the comparison."""
        logger.info(f"Calling LLM judge ({EVALUATION_MODEL})...")
        
        self.llm_response = ask_llm_text(
            prompt_path=EVALUATION_PROMPT_PATH,
            text=self.comparison_text,
            model_type=EVALUATION_MODEL
        )
        
        if not self.llm_response:
            raise RuntimeError("LLM evaluation failed")
        
        logger.info("LLM evaluation completed")
    
    def _parse_evaluation(self):
        """Parse LLM response to extract metrics."""
        lines = self.llm_response.split('\n')
        
        total = 0
        correct = 0
        non_null_total = 0
        non_null_correct = 0
        
        NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
        
        # Pattern: "Column Name: Gold Value vs Predicted Value => Equivalent/Not Equivalent"
        value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)
        
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
        
        overall_acc = (correct / total * 100) if total > 0 else 0.0
        non_null_acc = (non_null_correct / non_null_total * 100) if non_null_total > 0 else 0.0
        
        self.results = {
            "total_columns": total,
            "correct_columns": correct,
            "overall_accuracy": overall_acc,
            "non_null_total": non_null_total,
            "non_null_correct": non_null_correct,
            "non_null_accuracy": non_null_acc
        }
        
        logger.info(f"Overall Accuracy: {overall_acc:.2f}% ({correct}/{total})")
        logger.info(f"Non-null Accuracy: {non_null_acc:.2f}% ({non_null_correct}/{non_null_total})")
    
    def _save_results(self):
        """Save evaluation results to files."""
        # 1. Full LLM output
        full_output_path = self.output_dir / "evaluation_results.txt"
        with open(full_output_path, "w", encoding="utf-8") as f:
            f.write(self.llm_response)
            f.write("\n\n" + "="*60 + "\n")
            f.write(f"Total Evaluated Columns: {self.results['total_columns']}\n")
            f.write(f"Correct Columns: {self.results['correct_columns']}\n")
            f.write(f"Overall Accuracy: {self.results['overall_accuracy']:.2f}%\n\n")
            f.write(f"Non-null Gold Columns: {self.results['non_null_total']}\n")
            f.write(f"Non-null Correct Columns: {self.results['non_null_correct']}\n")
            f.write(f"Non-null Accuracy: {self.results['non_null_accuracy']:.2f}%\n")
        
        logger.info(f"Saved full results to {full_output_path}")
        
        # 2. Structured metrics JSON
        metrics_path = self.output_dir / "evaluation_summary.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4)
        
        logger.info(f"Saved metrics to {metrics_path}")
        
        # 3. Non-null only results
        non_null_lines = []
        NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
        value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)
        
        for line in self.llm_response.split('\n'):
            match = value_pattern.search(line)
            if match:
                gold_val = match.group(1).strip()
                if gold_val.lower() not in NULL_TOKENS:
                    non_null_lines.append(line)
        
        non_null_path = self.output_dir / "non_null_evaluation.txt"
        with open(non_null_path, "w", encoding="utf-8") as f:
            f.write("\n".join(non_null_lines))
        
        logger.info(f"Saved non-null results to {non_null_path}")
    
    def evaluate(self):
        """Main evaluation pipeline."""
        try:
            self._load_data()
            self._build_comparison_prompt()
            self._call_llm_judge()
            self._parse_evaluation()
            self._save_results()
            
            return self.results
        
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise

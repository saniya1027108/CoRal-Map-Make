# src/evaluation/evaluator.py
'''Enhanced evaluator that processes columns in batches and verifie completeness'''
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
    Processes columns in batches of 40 and verifies completeness.
    """
    
    def __init__(self, extracted_csv, gold_csv, pdf_name, output_dir, batch_size=40):
        """
        Args:
            extracted_csv: Path to extracted table CSV
            gold_csv: Path to gold standard CSV
            pdf_name: Name of PDF (stem, without extension)
            output_dir: Directory to save evaluation results
            batch_size: Number of columns per batch (default: 40)
        """
        self.extracted_csv = Path(extracted_csv)
        self.gold_csv = Path(gold_csv)
        self.pdf_name = pdf_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        
        self.extracted_data = None
        self.gold_data = None
        self.comparison_batches = []
        self.llm_responses = []
        self.results = {}
        self.missing_columns = []
    
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
    
    def _build_comparison_batches(self):
        """Build column-by-column comparison text in batches."""
        # Only compare columns that exist in both datasets
        common_columns = set(self.extracted_data.keys()) & set(self.gold_data.keys())
        
        # Sort columns for consistent ordering
        sorted_columns = sorted(common_columns)
        
        logger.info(f"Total columns to evaluate: {len(sorted_columns)}")
        
        # Split into batches
        for i in range(0, len(sorted_columns), self.batch_size):
            batch_columns = sorted_columns[i:i + self.batch_size]
            batch_lines = []
            
            for col in batch_columns:
                gold_val = self.gold_data.get(col, "not present")
                extracted_val = self.extracted_data.get(col, "not present")
                
                # Handle NaN/None values
                if pd.isna(gold_val):
                    gold_val = "not present"
                if pd.isna(extracted_val):
                    extracted_val = "not present"
                
                batch_lines.append(f"{col}: {gold_val}, {extracted_val}")
            
            batch_text = "\n".join(batch_lines)
            batch_num = (i // self.batch_size) + 1
            
            self.comparison_batches.append({
                "batch_num": batch_num,
                "columns": batch_columns,
                "comparison_text": batch_text
            })
            
            logger.info(f"Batch {batch_num}: {len(batch_columns)} columns (columns {i+1}-{i+len(batch_columns)})")
    
    def _call_llm_judge(self):
        """Call LLM to evaluate each batch."""
        logger.info(f"Evaluating {len(self.comparison_batches)} batches with LLM judge ({EVALUATION_MODEL})...")
        
        for batch in self.comparison_batches:
            batch_num = batch["batch_num"]
            logger.info(f"Processing Batch {batch_num}/{len(self.comparison_batches)}...")
            
            llm_response = ask_llm_text(
                prompt_path=EVALUATION_PROMPT_PATH,
                text=batch["comparison_text"],
                model_type=EVALUATION_MODEL
            )
            
            if not llm_response:
                logger.error(f"LLM evaluation failed for Batch {batch_num}")
                raise RuntimeError(f"LLM evaluation failed for Batch {batch_num}")
            
            self.llm_responses.append({
                "batch_num": batch_num,
                "columns": batch["columns"],
                "response": llm_response
            })
            
            logger.info(f"Batch {batch_num} completed")
        
        logger.info("All batches evaluated successfully")
    
    def _verify_completeness(self):
        """Verify that all columns are present in the evaluation results."""
        logger.info("Verifying completeness of evaluation...")
        
        # Get all columns that should be evaluated
        common_columns = set(self.extracted_data.keys()) & set(self.gold_data.keys())
        expected_columns = sorted(common_columns)
        
        # Extract evaluated columns from LLM responses
        evaluated_columns = set()
        for response_data in self.llm_responses:
            for line in response_data["response"].split('\n'):
                # Extract column name from line (format: "Column Name: ... => ...")
                if "=>" in line:
                    match = re.match(r"^([^:]+):", line)
                    if match:
                        col_name = match.group(1).strip()
                        evaluated_columns.add(col_name)
        
        # Find missing columns
        self.missing_columns = [col for col in expected_columns if col not in evaluated_columns]
        
        if self.missing_columns:
            logger.warning(f"Missing {len(self.missing_columns)} columns in evaluation:")
            for col in self.missing_columns[:10]:  # Show first 10
                logger.warning(f"  - {col}")
            if len(self.missing_columns) > 10:
                logger.warning(f"  ... and {len(self.missing_columns) - 10} more")
        else:
            logger.info("✅ All columns present in evaluation")
        
        return len(self.missing_columns) == 0
    
    def _parse_evaluation(self):
        """Parse LLM responses to extract metrics."""
        logger.info("Parsing evaluation results...")
        
        total = 0
        correct = 0
        non_null_total = 0
        non_null_correct = 0
        
        batch_results = []
        
        NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
        value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)
        
        # Process each batch
        for response_data in self.llm_responses:
            batch_num = response_data["batch_num"]
            response = response_data["response"]
            
            batch_total = 0
            batch_correct = 0
            batch_non_null_total = 0
            batch_non_null_correct = 0
            
            for line in response.split('\n'):
                # Overall accuracy
                if "Not Equivalent" in line and "=>" in line:
                    total += 1
                    batch_total += 1
                elif "Equivalent" in line and "=>" in line and "Not Equivalent" not in line:
                    total += 1
                    correct += 1
                    batch_total += 1
                    batch_correct += 1
                
                # Non-null accuracy
                match = value_pattern.search(line)
                if match:
                    gold_val = match.group(1).strip()
                    if gold_val.lower() not in NULL_TOKENS:
                        non_null_total += 1
                        batch_non_null_total += 1
                        if "Equivalent" in line and "Not Equivalent" not in line:
                            non_null_correct += 1
                            batch_non_null_correct += 1
            
            # Calculate batch metrics
            batch_overall_acc = (batch_correct / batch_total * 100) if batch_total > 0 else 0.0
            batch_non_null_acc = (batch_non_null_correct / batch_non_null_total * 100) if batch_non_null_total > 0 else 0.0
            
            batch_results.append({
                "batch_num": batch_num,
                "total_columns": batch_total,
                "correct_columns": batch_correct,
                "overall_accuracy": batch_overall_acc,
                "non_null_total": batch_non_null_total,
                "non_null_correct": batch_non_null_correct,
                "non_null_accuracy": batch_non_null_acc
            })
            
            logger.info(f"Batch {batch_num} - Overall: {batch_overall_acc:.2f}%, Non-null: {batch_non_null_acc:.2f}%")
        
        # Calculate overall metrics
        overall_acc = (correct / total * 100) if total > 0 else 0.0
        non_null_acc = (non_null_correct / non_null_total * 100) if non_null_total > 0 else 0.0
        
        self.results = {
            "total_columns": total,
            "correct_columns": correct,
            "overall_accuracy": overall_acc,
            "non_null_total": non_null_total,
            "non_null_correct": non_null_correct,
            "non_null_accuracy": non_null_acc,
            "batch_results": batch_results,
            "missing_columns": self.missing_columns,
            "missing_columns_count": len(self.missing_columns)
        }
        
        logger.info("=" * 60)
        logger.info(f"OVERALL RESULTS:")
        logger.info(f"Overall Accuracy: {overall_acc:.2f}% ({correct}/{total})")
        logger.info(f"Non-null Accuracy: {non_null_acc:.2f}% ({non_null_correct}/{non_null_total})")
        logger.info(f"Missing Columns: {len(self.missing_columns)}")
        logger.info("=" * 60)
    
    def _save_results(self):
        """Save evaluation results to files."""
        # 1. Combined full output from all batches
        full_output_path = self.output_dir / "evaluation_results.txt"
        with open(full_output_path, "w", encoding="utf-8") as f:
            for i, response_data in enumerate(self.llm_responses):
                if i > 0:
                    f.write("\n\n" + "="*60 + "\n\n")
                f.write(f"BATCH {response_data['batch_num']}\n")
                f.write("="*60 + "\n")
                f.write(response_data["response"])
            
            # Add summary at the end
            f.write("\n\n" + "="*60 + "\n")
            f.write("SUMMARY\n")
            f.write("="*60 + "\n")
            f.write(f"Total Evaluated Columns: {self.results['total_columns']}\n")
            f.write(f"Correct Columns: {self.results['correct_columns']}\n")
            f.write(f"Overall Accuracy: {self.results['overall_accuracy']:.2f}%\n\n")
            f.write(f"Non-null Gold Columns: {self.results['non_null_total']}\n")
            f.write(f"Non-null Correct Columns: {self.results['non_null_correct']}\n")
            f.write(f"Non-null Accuracy: {self.results['non_null_accuracy']:.2f}%\n\n")
            
            if self.missing_columns:
                f.write(f"\n⚠️  MISSING COLUMNS ({len(self.missing_columns)}):\n")
                for col in self.missing_columns:
                    f.write(f"  - {col}\n")
        
        logger.info(f"Saved full results to {full_output_path}")
        
        # 2. Individual batch files
        for response_data in self.llm_responses:
            batch_num = response_data["batch_num"]
            batch_path = self.output_dir / f"evaluation_batch_{batch_num}.txt"
            with open(batch_path, "w", encoding="utf-8") as f:
                f.write(response_data["response"])
            logger.info(f"Saved Batch {batch_num} to {batch_path}")
        
        # 3. Structured metrics JSON
        metrics_path = self.output_dir / "evaluation_summary.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4)
        logger.info(f"Saved metrics to {metrics_path}")
        
        # 4. Non-null only results (combined)
        non_null_lines = []
        NULL_TOKENS = {"nan", "not present", "n/a", "na", ""}
        value_pattern = re.compile(r":\s*(.*?)\s*vs\s*(.*?)\s*=>", re.IGNORECASE)
        
        for response_data in self.llm_responses:
            for line in response_data["response"].split('\n'):
                match = value_pattern.search(line)
                if match:
                    gold_val = match.group(1).strip()
                    if gold_val.lower() not in NULL_TOKENS:
                        non_null_lines.append(line)
        
        non_null_path = self.output_dir / "non_null_evaluation.txt"
        with open(non_null_path, "w", encoding="utf-8") as f:
            f.write("\n".join(non_null_lines))
        logger.info(f"Saved non-null results to {non_null_path}")
        
        # 5. Missing columns report
        if self.missing_columns:
            missing_path = self.output_dir / "missing_columns.txt"
            with open(missing_path, "w", encoding="utf-8") as f:
                f.write(f"Missing Columns Report\n")
                f.write(f"Total Missing: {len(self.missing_columns)}\n")
                f.write("="*60 + "\n\n")
                for col in self.missing_columns:
                    f.write(f"{col}\n")
            logger.info(f"Saved missing columns report to {missing_path}")
    
    def evaluate(self):
        """Main evaluation pipeline."""
        try:
            logger.info("Starting evaluation pipeline...")
            
            # Step 1: Load data
            self._load_data()
            
            # Step 2: Build comparison batches
            self._build_comparison_batches()
            
            # Step 3: Call LLM for each batch
            self._call_llm_judge()
            
            # Step 4: Verify completeness
            is_complete = self._verify_completeness()
            if not is_complete:
                logger.warning("⚠️  Evaluation is incomplete - some columns are missing!")
            
            # Step 5: Parse results
            self._parse_evaluation()
            
            # Step 6: Save results
            self._save_results()
            
            logger.info("✅ Evaluation pipeline completed")
            
            return self.results
        
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise
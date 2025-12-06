# src/fill_table/fill_table.py
import json
import pandas as pd
import numpy as np
import fitz
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..utils.logging_utils import setup_logger
from ..model_handling.llm_extraction import extract_group_from_chunk  # Adjusted import path based on filename
# from ..model_handling.retriever import embed_texts, retrieve_top_chunks

logger = setup_logger("table_filling")

def _safe_json_value(val):
    """Convert numpy/pandas types to native Python types"""
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if pd.isna(val):
        return None
    return val


def save_metadata_safely(output_data, metadata_path):
    """
    Save metadata JSON without any NumPy/pandas type errors
    """
    safe_data = {}
    for col_name, info in output_data.items():
        safe_data[col_name] = {
            "value": _safe_json_value(info.get("value")),
            "evidence": info.get("evidence"),
            "chunk_id": _safe_json_value(info.get("chunk_id")),
            "page": _safe_json_value(info.get("page"))
        }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(safe_data, f, indent=4, ensure_ascii=False)


# extracting first 2 pages of the pdf(clinical trial) to pass as context
def extract_first_n_pages_text(pdf_path, n=2):
    """
    Extracts and concatenates the text from the first n pages of a PDF.
    """
    doc = fitz.open(pdf_path)
    texts = []
    for i in range(min(n, len(doc))):
        page = doc[i]
        texts.append(page.get_text())
    doc.close()
    return "\n\n".join(texts)


def process_group(group_label, group, chunks, context_text):
    """
    Process a single group: extract from all chunks sequentially, take first non-null values.
    Returns: (group_output_dict, local_metrics_dict)
    """
    group_output = {
        col["Column Name"]: {"value": None, "evidence": None, "chunk_id": None, "page": None}
        for col in group
    }
    local_metrics = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    for chunk_idx, chunk in enumerate(chunks):
        extracted, in_t, out_t = extract_group_from_chunk(chunk, group, context_text)
        local_metrics["calls"] += 1
        local_metrics["input_tokens"] += in_t
        local_metrics["output_tokens"] += out_t

        for col_name, data in extracted.items():
            if data["value"] is not None and group_output[col_name]["value"] is None:
                group_output[col_name].update({
                    "value": data["value"],
                    "evidence": data["evidence"],
                    "chunk_id": chunk_idx,
                    "page": chunk["page"]
                })

    logger.info(f"Group '{group_label}' processed: {local_metrics['calls']} LLM calls")
    return group_output, local_metrics


#function to extract values from the pdf to fill the table - without the retriever
def fill_table_all_chunks(chunks, groups, pdf_path, output_path="extracted_table.csv", metadata_path="extraction_metadata.json"):
    """
    Parallel version: Process each group in parallel using ThreadPoolExecutor.
    For each group, process chunks sequentially to respect API rate limits.
    Assumes column groups are disjoint (no overlapping columns).
    """
    context_text = extract_first_n_pages_text(pdf_path, n=2)
    
    # Initialize output
    output_data = {}
    total_metrics = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
    
    # Parallel processing over groups (max_workers=8 to avoid overwhelming OpenAI API)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(process_group, group_label, group, chunks, context_text)
            for group_label, group in groups.items()
        ]
        
        for future in as_completed(futures):
            group_output, local_metrics = future.result()
            
            # Merge group output (disjoint columns)
            for col_name, info in group_output.items():
                if col_name not in output_data:
                    output_data[col_name] = info
            
            # Accumulate metrics
            for key in total_metrics:
                total_metrics[key] += local_metrics[key]

    logger.info(f"Total LLM calls made: {total_metrics['calls']} (parallel over groups)")

    # Save results
    values = {col: _safe_json_value(info["value"]) for col, info in output_data.items()}
    pd.DataFrame([values]).to_csv(output_path, index=False)
    save_metadata_safely(output_data, metadata_path)

    total_columns = len(output_data)
    filled_columns = sum(1 for info in output_data.values() if info["value"] is not None)
    null_columns = total_columns - filled_columns
    logger.info(f"[INFO] Filled columns: {filled_columns}")
    logger.info(f"[INFO] Remaining null columns: {null_columns}")

    logger.info(f"Table saved to {output_path}")
    logger.info(f"Metadata JSON saved to {metadata_path}")
    
    return output_data, total_metrics
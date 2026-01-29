# src/fill_table/fill_table.py
# (Updated with multi-threading over group-chunk pairs, performance monitoring, and metrics accumulation)
import json
import pandas as pd
import numpy as np
import fitz
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from ..utils.logging_utils import setup_logger
from ..model_handling.llm_extraction import extract_group_from_chunk
from ..utils.performance_monitor import PerformanceMonitor
from ..retrieval.retriever import get_retriever, build_retrieval_query, combine_retrieved_chunks
from ..config.config import (
    USE_RETRIEVAL,
    RETRIEVAL_STRATEGY,
    RETRIEVAL_TOP_N,
    RETRIEVAL_BM25_WEIGHT,
    RETRIEVAL_SEMANTIC_WEIGHT,
    RETRIEVAL_MAX_COMBINED_CHUNKS,
    MAX_WORKERS
)

logger = setup_logger("table_filling")

def log_llm_response(metrics_dir, group_label, chunk_idx, prompt, response, extracted):
    """
    Log the LLM prompt, response, and extracted values for error analysis.
    """
    log_path = Path(metrics_dir) / "llm_responses.log"
    entry = {
        "group": group_label,
        "chunk_idx": chunk_idx,
        "prompt": prompt,
        "response": response,
        "extracted": extracted
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
def _safe_json_value(val):
    """Convert numpy/pandas types to native Python types"""
    # Handle None first
    if val is None:
        return None
    
    # Handle numpy/pandas numeric types
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    
    # Handle numpy arrays
    if isinstance(val, np.ndarray):
        return val.tolist()
    
    # Handle lists (convert to string if needed for JSON compatibility)
    if isinstance(val, list):
        return val
    
    # Check for pandas NA/NaN (only for scalar values)
    try:
        if pd.isna(val):
            return None
    except (ValueError, TypeError):
        # pd.isna() failed (e.g., on a list), just return the value
        pass
    
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
    
    DEPRECATED: Use get_or_generate_context() instead for better extraction guide.
    """
    doc = fitz.open(pdf_path)
    texts = []
    for i in range(min(n, len(doc))):
        page = doc[i]
        texts.append(page.get_text())
    doc.close()
    return "\n\n".join(texts)


def get_or_generate_context(pdf_path, output_dir, use_file_api=None):
    """
    Load cached extraction guide or generate new one using Gemini File API.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save/load extraction_guide.txt
        use_file_api: Override USE_FILE_API_CONTEXT config (optional)
    
    Returns:
        Formatted context text for system_prompt
    
    Raises:
        Exception: If generation fails
    """
    from ..config.config import USE_FILE_API_CONTEXT, CONTEXT_MAX_RETRIES
    from ..utils.context_generator import generate_trial_context
    
    # Check if we should use new File API approach
    if use_file_api is None:
        use_file_api = USE_FILE_API_CONTEXT
    
    if not use_file_api:
        # Fall back to old approach
        logger.info("Using legacy 2-page text context")
        return extract_first_n_pages_text(pdf_path, n=2)
    
    # Check for cached guide
    guide_path = Path(output_dir) / "context_text.txt"
    
    if guide_path.exists():
        logger.info(f"✅ Loading cached extraction guide from {guide_path}")
        try:
            context_text = guide_path.read_text(encoding='utf-8')
            logger.info(f"Loaded guide ({len(context_text)} chars)")
            return context_text
        except Exception as e:
            logger.warning(f"Failed to load cached guide: {e}. Regenerating...")
    
    # Generate new extraction guide
    logger.info("🔄 Generating new extraction guide via Gemini File API...")
    try:
        context_text = generate_trial_context(
            pdf_path=pdf_path,
            max_retries=CONTEXT_MAX_RETRIES
        )
        
        # Save to cache
        guide_path.write_text(context_text, encoding='utf-8')
        logger.info(f"✅ Extraction guide saved to {guide_path}")
        
        return context_text
        
    except Exception as e:
        logger.error(f"❌ Context generation failed: {e}")
        raise Exception(f"Failed to generate extraction guide: {e}")

def llm_call_and_log(chunk, group, context_text, metrics_dir, group_label, chunk_idx):
    # Only unpack 3 values as returned by extract_group_from_chunk
    extracted, in_t, out_t = extract_group_from_chunk(chunk, group, context_text, metrics_dir)
    # You may want to log only what you have (prompt/response not available)
    log_llm_response(metrics_dir, group_label, chunk_idx, None, None, extracted)
    return extracted, in_t, out_t

#function to extract values from the pdf to fill the table - without the retriever
def fill_table_all_chunks(chunks, groups, pdf_path, output_path="extracted_table.csv", metadata_path="extraction_metadata.json"):
    """
    Highly parallel version: Process all (group, chunk) pairs in parallel using ThreadPoolExecutor.
    For each group, collect results, sort by chunk order, and merge respecting the first non-null rule.
    Incorporates performance monitoring.
    """
    out_dir = Path(output_path).parent
    metrics_dir = out_dir / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    monitor = PerformanceMonitor(metrics_dir)
    monitor.start_monitoring()

    context_text = get_or_generate_context(pdf_path, out_dir)
    
    # Initialize output
    output_data = {}
    total_metrics = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
    
    # Parallel processing over all (group, chunk) pairs (max_workers=8 for balance between speed and API limits)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        
        for group_label, group in groups.items():
            monitor.record_group_start(group_label)
            group_futures = []
            for chunk_idx, chunk in enumerate(chunks):
                monitor.record_call_start(group_label, chunk_idx)
                

                future = executor.submit(
                        llm_call_and_log, chunk, group, context_text, metrics_dir, group_label, chunk_idx
                    )
                group_futures.append((chunk_idx, future))
                futures[group_label] = group_futures
        
        # Process results per group, respecting chunk order
        for group_label, group_futures in futures.items():
            group_output = {
                col["Column Name"]: {"value": None, "evidence": None, "chunk_id": None, "page": None}
                for col in groups[group_label]
            }
            local_metrics = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
            
            # Collect in chunk order
            for chunk_idx, future in sorted(group_futures, key=lambda x: x[0]):
                extracted, in_t, out_t = future.result()
                monitor.record_call_end(group_label, chunk_idx)
                
                local_metrics["calls"] += 1
                local_metrics["input_tokens"] += in_t
                local_metrics["output_tokens"] += out_t
                
                for col_name, data in extracted.items():
                    if data["value"] is not None and group_output[col_name]["value"] is None:
                        group_output[col_name].update({
                            "value": data["value"],
                            "evidence": data["evidence"],
                            "chunk_id": chunk_idx,
                            "page": chunks[chunk_idx]["page"]
                        })
            
            # Merge group output
            for col_name, info in group_output.items():
                output_data[col_name] = info
            
            # Accumulate metrics
            for key in total_metrics:
                total_metrics[key] += local_metrics[key]
            
            monitor.record_group_end(group_label)
            logger.info(f"Group '{group_label}' processed: {local_metrics['calls']} LLM calls")

    monitor.finish_monitoring()
    monitor.save_report()

    logger.info(f"Total LLM calls made: {total_metrics['calls']} (parallel over group-chunk pairs)")

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


def fill_table_with_retrieval(chunks, groups, pdf_path, output_path="extracted_table.csv", 
                               metadata_path="extraction_metadata.json", 
                               top_n=None, strategy=None):
    """
    Retrieval-based table filling: For each group, retrieve top-N relevant chunks,
    combine them into a single context, and make ONE LLM call per group.
    
    This is much faster and cheaper than processing all chunks.
    
    Args:
        chunks: List of document chunks
        groups: Dictionary of column groups {group_name: [col_defs...]}
        pdf_path: Path to PDF for context extraction
        output_path: Where to save CSV
        metadata_path: Where to save metadata JSON
        top_n: Number of chunks to retrieve per group (overrides config)
        strategy: Retrieval strategy (overrides config): "bm25", "semantic", "hybrid"
    
    Returns:
        (output_data, total_metrics)
    """
    # Use config values if not specified
    if top_n is None:
        top_n = RETRIEVAL_TOP_N
    if strategy is None:
        strategy = RETRIEVAL_STRATEGY
    
    out_dir = Path(output_path).parent
    metrics_dir = out_dir / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    monitor = PerformanceMonitor(metrics_dir)
    monitor.start_monitoring()
    
    # Extract context - use cached guide or generate new one
    context_text = get_or_generate_context(pdf_path, out_dir)
    
    # Initialize retriever (builds indices once)
    logger.info(f"Initializing {strategy} retriever with {len(chunks)} chunks...")
    retriever = get_retriever(
        chunks, 
        strategy=strategy,
        bm25_weight=RETRIEVAL_BM25_WEIGHT,
        semantic_weight=RETRIEVAL_SEMANTIC_WEIGHT
    )
    logger.info("Retriever initialized successfully")
    
    # Initialize output
    output_data = {}
    total_metrics = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
    
    # Helper function to process a single group (for parallelization)
    def process_group(group_label, group):
        """Process a single group: retrieve, combine, and extract."""
        monitor.record_group_start(group_label)
        logger.info(f"Processing group: {group_label}")
        
        try:
            # 1. Build retrieval query from column definitions
            query = build_retrieval_query(group)
            logger.info(f"Query: {query[:200]}...")  # Log first 200 chars
            
            # 2. Retrieve top-N relevant chunks
            top_chunks = retriever.retrieve(query, top_n=top_n)
            logger.info(f"Retrieved {len(top_chunks)} chunks for group '{group_label}'")
            
            # 3. Combine chunks into single structured context
            combined_chunk = combine_retrieved_chunks(
                top_chunks, 
                max_chunks=RETRIEVAL_MAX_COMBINED_CHUNKS
            )
            logger.info(f"Combined into {combined_chunk['source_chunks']} chunk(s)")
            
            # 4. Single LLM call for entire group
            monitor.record_call_start(group_label, 0)
            extracted, in_t, out_t = extract_group_from_chunk(
                combined_chunk, 
                group, 
                context_text, 
                metrics_dir
            )
            monitor.record_call_end(group_label, 0)
            
            # Log the extraction
            log_llm_response(metrics_dir, group_label, "combined", None, None, extracted)
            
            # Store extracted values for this group
            group_data = {}
            for col_name, data in extracted.items():
                group_data[col_name] = {
                    "value": data.get("value"),
                    "evidence": data.get("evidence"),
                    "chunk_id": "combined",
                    "page": combined_chunk.get("pages", [None])[0] if combined_chunk.get("pages") else None,
                    "retrieved_pages": combined_chunk.get("pages", [])
                }
            
            logger.info(f"Group '{group_label}' processed: 1 LLM call, "
                       f"{in_t} input tokens, {out_t} output tokens")
            
            monitor.record_group_end(group_label)
            return (group_label, group_data, in_t, out_t, None)
        
        except Exception as e:
            logger.error(f"Failed to extract group '{group_label}': {e}")
            # Initialize with null values
            group_data = {}
            for col in group:
                col_name = col["Column Name"]
                group_data[col_name] = {
                    "value": None,
                    "evidence": None,
                    "chunk_id": None,
                    "page": None,
                    "retrieved_pages": []
                }
            monitor.record_group_end(group_label)
            return (group_label, group_data, 0, 0, str(e))
    
    # Process all groups in parallel (max_workers=8 for balance between speed and API limits)
    logger.info(f"🚀 Processing {len(groups)} groups in parallel (8 workers)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_group, label, group): label 
                  for label, group in groups.items()}
        
        # Collect results as they complete
        for future in as_completed(futures):
            group_label, group_data, in_t, out_t, error = future.result()
            
            # Merge group data into output
            output_data.update(group_data)
            
            # Update metrics
            total_metrics["calls"] += 1
            total_metrics["input_tokens"] += in_t
            total_metrics["output_tokens"] += out_t
            
            if error:
                logger.warning(f"Group '{group_label}' completed with error: {error}")
    
    monitor.finish_monitoring()
    monitor.save_report()
    
    logger.info(f"Total LLM calls made: {total_metrics['calls']} (retrieval-based, one per group)")
    
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
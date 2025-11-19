# src/extraction/table_filling.py
import json
import pandas as pd
import numpy as np
from ..utils.logging_utils import setup_logger
from ..model_handling.llm_extraction import extract_group_from_chunk
from ..model_handling.retriever import embed_texts, retrieve_top_chunks

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

def fill_table_smart(chunks, groups, output_path="extracted_table.csv", metadata_path="extraction_metadata.json"):
    """
    Smart version: uses embeddings to pre-filter chunks → 10–30× fewer LLM calls
    """
    # ------------------------------------------------------------------
    # 1. Pre-compute embeddings ONCE
    # ------------------------------------------------------------------
    logger.info("Computing embeddings for all chunks...")
    chunk_texts = []
    for chunk in chunks:
        if chunk["type"] == "text":
            text = chunk["content"]
        elif chunk["type"] in ["table", "figure"]:
            text = chunk.get("table_content") or chunk.get("figure_content") or ""
        elif chunk["type"] == "image":
            text = "Image from clinical trial PDF"  # minimal signal
        else:
            text = ""
        chunk_texts.append(text)

    chunk_embeddings = embed_texts(chunk_texts)  # (N, dim)

    # ------------------------------------------------------------------
    # 2. Initialize output
    # ------------------------------------------------------------------
    output_data = {}
    for group in groups.values():
        for col in group:
            col_name = col["Column Name"]
            if col_name not in output_data:
                output_data[col_name] = {
                    "value": None, "evidence": None, "chunk_id": None, "page": None
                }

    # ------------------------------------------------------------------
    # 3. Process each group with smart retrieval
    # ------------------------------------------------------------------
    total_llm_calls = 0

    for group_label, group in groups.items():
        if all(output_data[col["Column Name"]]["value"] is not None for col in group):
            continue  # already filled

        logger.info(f"Retrieving top chunks for group: {group_label}")
        candidate_chunks = retrieve_top_chunks(chunks, group, chunk_embeddings, top_k=4)

        found = False
        for chunk in candidate_chunks:
            extracted = extract_group_from_chunk(chunk, group)
            total_llm_calls += 1

            for col_name, data in extracted.items():
                if data["value"] is not None and output_data[col_name]["value"] is None:
                    output_data[col_name].update({
                        "value": data["value"],
                        "evidence": data["evidence"],
                        "chunk_id": chunk.get("_chunk_id"),
                        "page": chunk["page"]
                    })
                    found = True

            if all(output_data[col["Column Name"]]["value"] is not None for col in group):
                logger.info(f"Group '{group_label}' fully filled")
                break

        if found:
            logger.info(f"Filled values in '{group_label}' with {len(candidate_chunks)} chunks")

    logger.info(f"Total LLM calls made: {total_llm_calls} (smart retrieval)")

    # ------------------------------------------------------------------
    # 4. Save results
    # ------------------------------------------------------------------
    values = {col: _safe_json_value(info["value"]) for col, info in output_data.items()}
    pd.DataFrame([values]).to_csv(output_path, index=False)

    # ← NEW SAFE SAVE
    save_metadata_safely(output_data, metadata_path)

    logger.info(f"Table saved to {output_path}")
    logger.info(f"Metadata JSON saved to {metadata_path}")
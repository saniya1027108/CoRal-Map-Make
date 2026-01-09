#!/usr/bin/env python3
"""
compare_by_parent_doc.py

- Hardcode GOLD_CSV_PATH and EXTRACTED_CSV_PATH (path to extracted_table.csv).
- Extract document name as the parent folder name of the extracted CSV file.
  Example: /.../NCT00268476_Attard_STAMPEDE_Lancet'23/extracted_table.csv
           -> doc_name = "NCT00268476_Attard_STAMPEDE_Lancet'23"
- Find the row in the gold CSV whose document column == doc_name.
- Compare that gold row to the first row of the extracted CSV and write OUTPUT_CSV_PATH.
  Each output cell contains two lines:
      extracted value = <value>
      gold value = <value>
"""

from pathlib import Path
import pandas as pd
import sys
import csv

# ============================
# HARDCODE THESE PATHS BELOW
# ============================
GOLD_CSV_PATH     = Path("/Users/saniyamulla/Documents/CoRAL/Map_and_Make/dataset/GoldTable.csv")
EXTRACTED_CSV_PATH = Path("/Users/saniyamulla/Documents/CoRAL/Map_and_Make/test_results/new/NCT00309985_Kriayako_CHAARTED_JCO'18")
OUTPUT_CSV_PATH   = Path("/Users/saniyamulla/Documents/CoRAL/Map_and_Make/analysis_for_mayo/gold_vs_extracted_comparison.csv")  # Single master file
# ============================

# Candidate column names in gold that might contain the document name
CANDIDATE_DOC_COL_NAMES = ["Document Name"]

def safe_str(x):
    if pd.isna(x):
        return ""
    return str(x)

def detect_doc_column(gold_df, doc_name):
    """
    1) Try candidate column names (case-insensitive).
    2) If none present, scan all columns for an exact string match to doc_name and return that column.
    3) If not found, raise ValueError.
    """
    lower_to_col = {col.lower(): col for col in gold_df.columns}
    for cand in CANDIDATE_DOC_COL_NAMES:
        if cand.lower() in lower_to_col:
            return lower_to_col[cand.lower()]

    # search for exact matches across all columns
    for col in gold_df.columns:
        matches = gold_df[col].astype(str).fillna("").eq(str(doc_name))
        if matches.any():
            return col

    raise ValueError(
        f"Could not detect document-name column or find document name '{doc_name}' in the gold CSV.\n"
        f"Gold CSV columns: {list(gold_df.columns)}"
    )

def build_comparison_row(gold_row, ext_row):
    """
    Return a one-row DataFrame where each column cell is:
        extracted value = <ext>
        gold value = <gold>
    Columns are the union of gold_row and ext_row indices.
    """
    gold_cols = list(gold_row.index)
    ext_cols = list(ext_row.index)
    all_cols = []
    for c in gold_cols + ext_cols:
        if c not in all_cols:
            all_cols.append(c)

    row_data = {}
    for col in all_cols:
        gval = safe_str(gold_row[col]) if col in gold_row.index else ""
        eval_ = safe_str(ext_row[col]) if col in ext_row.index else ""
        cell = f"extracted value = {eval_}\ngold value = {gval}"
        row_data[col] = [cell]

    return pd.DataFrame(row_data)

def main():
    # Basic checks
    if not GOLD_CSV_PATH.exists():
        print(f"Error: Gold CSV not found at: {GOLD_CSV_PATH}", file=sys.stderr)
        sys.exit(2)
    if not EXTRACTED_CSV_PATH.exists():
        print(f"Error: Extracted CSV not found at: {EXTRACTED_CSV_PATH}", file=sys.stderr)
        sys.exit(3)

    # The document name is the parent folder name of the extracted CSV path.
    # If the user passed a directory instead of a file, we derive doc_name from that dir's name.
    if EXTRACTED_CSV_PATH.is_file():
        doc_name = EXTRACTED_CSV_PATH.parent.name
        extracted_csv_file = EXTRACTED_CSV_PATH
    elif EXTRACTED_CSV_PATH.is_dir():
        # If they passed a directory, try to find a CSV inside and use that directory's name
        doc_name = EXTRACTED_CSV_PATH.name
        csvs = sorted([p for p in EXTRACTED_CSV_PATH.iterdir() if p.is_file() and p.suffix.lower() == ".csv"])
        if not csvs:
            print(f"Error: directory provided but no CSV found inside: {EXTRACTED_CSV_PATH}", file=sys.stderr)
            sys.exit(4)
        extracted_csv_file = csvs[0]
    else:
        # Path exists false; treat path's parent as doc name if user passed a path-like string that doesn't exist
        # but prefer to fail early: we need an existing extracted CSV file to compare.
        print(f"Error: extracted CSV path does not exist: {EXTRACTED_CSV_PATH}", file=sys.stderr)
        sys.exit(5)

    print(f"Derived document name from extracted path: {doc_name!r}")
    print(f"Using extracted CSV file: {extracted_csv_file}")

    # Load CSVs (read as objects to preserve formatting)
    gold_df = pd.read_csv(GOLD_CSV_PATH, dtype=object)
    ext_df = pd.read_csv(extracted_csv_file, dtype=object)

    # Detect document column in gold and find matching row
    try:
        doc_col = detect_doc_column(gold_df, doc_name)
    except ValueError as e:
        print("Error detecting document column:", e, file=sys.stderr)
        sys.exit(6)

    print(f"Detected document column in gold CSV: {doc_col}")

    # Try matching with and without .pdf extension
    doc_name_variants = [doc_name, f"{doc_name}.pdf"]
    matches = pd.DataFrame()
    for variant in doc_name_variants:
        matches = gold_df[ gold_df[doc_col].astype(str).fillna("").eq(str(variant)) ]
        if not matches.empty:
            break

    if matches.empty:
        print(f"No row in gold CSV has {doc_col} == '{doc_name}' or '{doc_name}.pdf'", file=sys.stderr)
        sys.exit(7)

    if len(matches) > 1:
        print(f"Warning: {len(matches)} rows match document name '{doc_name}' or '{doc_name}.pdf'. Using the first match.", file=sys.stderr)

    gold_row = matches.iloc[0]

    # For extracted CSV, use the first row (assumption: extracted CSV contains the values for that document)
    if ext_df.empty:
        print(f"Error: extracted CSV {extracted_csv_file} is empty", file=sys.stderr)
        sys.exit(8)
    if len(ext_df) > 1:
        print(f"Warning: extracted CSV has {len(ext_df)} rows — using the first row for comparison.", file=sys.stderr)
    ext_row = ext_df.iloc[0]

    # Build comparison DataFrame (one row)
    comparison_df = build_comparison_row(gold_row, ext_row)
    # Add document name as a column for identification, only if not present
    if "Document Name" not in comparison_df.columns:
        comparison_df.insert(0, "Document Name", doc_name)
    else:
        # Optionally, move it to the first column
        cols = list(comparison_df.columns)
        cols.insert(0, cols.pop(cols.index("Document Name")))
        comparison_df = comparison_df[cols]

    # If output file exists, append or update columns as needed
    if OUTPUT_CSV_PATH.exists():
        master_df = pd.read_csv(OUTPUT_CSV_PATH, dtype=str)
        # Ensure all columns are present in both DataFrames
        for col in comparison_df.columns:
            if col not in master_df.columns:
                master_df[col] = ""
        for col in master_df.columns:
            if col not in comparison_df.columns:
                comparison_df[col] = ""
        # Reorder columns to match master
        comparison_df = comparison_df[master_df.columns]
        # --- Remove any existing row for this doc_name ---
        master_df = master_df[master_df["Document Name"] != doc_name]
        # Append new row
        master_df = pd.concat([master_df, comparison_df], ignore_index=True)
    else:
        master_df = comparison_df

    # Write CSV, quoting all fields so newlines are preserved
    master_df.to_csv(OUTPUT_CSV_PATH, index=False, quoting=csv.QUOTE_ALL)
    print(f"Wrote/updated master comparison CSV: {OUTPUT_CSV_PATH}")

if __name__ == "__main__":
    main()

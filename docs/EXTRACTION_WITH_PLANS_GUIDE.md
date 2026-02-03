# Extraction with Plans - Usage Guide

This guide explains how to use the new hierarchical extraction pipeline with pre-generated extraction plans.

## Overview

The new pipeline has **two stages**:

### Stage 1: Generate Extraction Plans
- **Script**: `experiment-scripts/test_hierarchical_extraction.py`
- **What it does**: 
  - Analyzes the PDF with Gemini
  - Determines if each column's data exists in the PDF
  - Identifies WHERE (page, source type) and HOW to extract each value
  - Generates structured extraction plans
- **Output**: `results/{pdf_name}/extraction_plans/`

### Stage 2: Extract Data Using Plans
- **Script**: `experiment-scripts/run_extraction_with_plans.py`
- **What it does**:
  - Loads extraction plans
  - Filters columns found in PDF
  - Calls GPT-4o with full PDF + relevant chunks
  - Structures output with local LLM
  - Generates CSV and metadata
- **Output**: `results/{pdf_name}/extractions/`

---

## Prerequisites

1. **Local model running on localhost:8001**
   ```bash
   bash run_vllm.sh
   ```
   Wait until the server is ready.

2. **Environment variables set**
   - `GEMINI_API_KEY` (for planning stage)
   - `OPENAI_API_KEY` (for extraction stage)

3. **PDF already chunked**
   - Must have `pdf_chunked.json` available
   - Usually in `test_results/new/{pdf_name}/`

---

## Complete Workflow

### Step 1: Generate Extraction Plans

```bash
python experiment-scripts/test_hierarchical_extraction.py \
    --pdf "test_results/new/NCT00268476_Attard_STAMPEDE_Lancet'23/NCT00268476_Attard_STAMPEDE_Lancet'23.pdf" \
    --chunks "test_results/new/NCT00268476_Attard_STAMPEDE_Lancet'23/pdf_chunked.json" \
    --all
```

**Options:**
- `--all`: Process all column groups
- `--groups "Group 1" "Group 2"`: Process specific groups only
- `--output-dir`: Custom output directory (default: auto-generated)

**Output:**
```
results/NCT00268476_Attard_STAMPEDE_Lancet'23/extraction_plans/
├── Median_Age_(years)_plan.json
├── Median_Age_(years)_raw.txt
├── Gleason_score_-_N_(%)_plan.json
├── Gleason_score_-_N_(%)_raw.txt
└── ... (one pair per group)
```

**What each plan contains:**
```json
{
  "group_name": "Median Age (years)",
  "columns": [
    {
      "column_name": "Median Age (years) | Treatment",
      "found_in_pdf": true,
      "page": 5,
      "source_type": "table",
      "confidence": "high",
      "extraction_plan": "Found in Table 1 - Baseline Demographics..."
    }
  ]
}
```

---

### Step 2: Extract Data Using Plans

```bash
python experiment-scripts/run_extraction_with_plans.py \
    --pdf "test_results/new/NCT00268476_Attard_STAMPEDE_Lancet'23/NCT00268476_Attard_STAMPEDE_Lancet'23.pdf" \
    --chunks "test_results/new/NCT00268476_Attard_STAMPEDE_Lancet'23/pdf_chunked.json"
```

**Options:**
- `--plans-dir`: Custom plans directory (default: auto-detect)
- `--output-dir`: Custom output directory (default: `results/{pdf_name}/extractions`)
- `--groups "Group 1" "Group 2"`: Extract specific groups only

**Output:**
```
results/NCT00268476_Attard_STAMPEDE_Lancet'23/extractions/
├── extracted_table.csv       # Single-row CSV with all column values
└── extraction_metadata.json  # Evidence, page, chunk_id for each column
```

---

### Step 3: Visualize Results

```bash
python visualizer/visualize_extraction.py \
    results/NCT00268476_Attard_STAMPEDE_Lancet'23/extractions/extracted_table.csv
```

This opens an HTML visualization in your browser showing:
- ✅ Correctly extracted values
- ❌ Missing values
- ⚠️ Comparison with gold table (if available)

---

## Full Example

```bash
# 1. Start local model
bash run_vllm.sh &

# Wait for model to load...

# 2. Generate extraction plans (one-time per PDF)
python experiment-scripts/test_hierarchical_extraction.py \
    --pdf "test_results/new/NCT02799602_Hussain_ARASENS_JCO'23/NCT02799602_Hussain_ARASENS_JCO'23.pdf" \
    --chunks "test_results/new/NCT02799602_Hussain_ARASENS_JCO'23/pdf_chunked.json" \
    --all

# 3. Extract data using plans
python experiment-scripts/run_extraction_with_plans.py \
    --pdf "test_results/new/NCT02799602_Hussain_ARASENS_JCO'23/NCT02799602_Hussain_ARASENS_JCO'23.pdf" \
    --chunks "test_results/new/NCT02799602_Hussain_ARASENS_JCO'23/pdf_chunked.json"

# 4. Visualize
python visualizer/visualize_extraction.py \
    results/NCT02799602_Hussain_ARASENS_JCO\'23/extractions/extracted_table.csv
```

---

## Key Features

### 1. **Smart Filtering**
- Only extracts columns where `found_in_pdf: true`
- Skips columns not reported in the paper
- Saves API costs and time

### 2. **Guided Extraction**
- GPT-4o receives specific instructions per column
- Knows where to look (page, source type)
- Understands how to extract (aggregation, synonyms, etc.)

### 3. **Full PDF Context**
- GPT-4o has access to entire PDF via Assistants API
- Can verify chunk content against full document
- Better handling of cross-page information

### 4. **Local Structuring**
- Free-form GPT-4o reasoning → structured JSON
- Validation with Pydantic schemas
- Automatic retries on format errors

### 5. **Compatible Output**
- Matches existing pipeline format
- Works with current visualization tool
- Can compare against gold table

---

## Troubleshooting

### "GEMINI_API_KEY not set"
- Add to your `.env` file: `GEMINI_API_KEY=your_key_here`

### "OPENAI_API_KEY not set"
- Add to your `.env` file: `OPENAI_API_KEY=your_key_here`

### "Failed to connect to localhost:8001"
- Make sure `run_vllm.sh` is running
- Check server logs for errors
- Verify port 8001 is not blocked

### "Plans directory not found"
- Run Stage 1 (test_hierarchical_extraction.py) first
- Check that plans were generated successfully
- Verify path: `results/{pdf_name}/extraction_plans/`

### Validation errors from structurer
- Check `{group_name}_structurer_debug.txt` files
- Verify local model is producing valid JSON
- Try increasing `max_retries` in the script

---

## Cost Estimates

### Stage 1: Planning (per PDF, one-time)
- **Gemini 2.5 Flash**: ~$0.50-2.00 per PDF
  - Depends on PDF size and number of column groups
  - One API call per group with full PDF

### Stage 2: Extraction (per PDF)
- **GPT-4o**: ~$2-5 per PDF
  - Depends on number of groups and PDF size
  - Uses Assistants API with file search
- **Local LLM**: Free (runs on your hardware)

### Total per PDF: ~$3-7
- Much cheaper than processing all columns individually
- Smart filtering reduces unnecessary extractions

---

## Next Steps

After validating this pipeline:
1. Integrate into main workflow
2. Add batch processing for multiple PDFs
3. Add progress tracking and resumability
4. Optimize prompts based on results
5. Add evaluation metrics against gold table

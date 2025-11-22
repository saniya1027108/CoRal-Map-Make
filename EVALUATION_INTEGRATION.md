# Evaluation Integration - Complete

## What Was Added

### 1. New Evaluator Class (`src/evaluation/evaluator.py`)
- Clean class-based design matching `PDFChunker` pattern
- Loads extracted CSV and gold CSV
- Matches by document name (PDF stem)
- Builds column-by-column comparison
- Calls LLM judge (Gemini or GPT)
- Parses results and calculates metrics
- Saves 3 output files in `metrics/` folder

### 2. LLM Utilities (`src/utils/llm_utils.py`)
- Unified text-based LLM calls
- Supports both Gemini and GPT
- Loads prompt templates from files
- Reuses existing API configurations

### 3. Updated Configuration (`src/config/config.py`)
- Added `.env` support with `python-dotenv`
- Loads API keys from environment variables
- Added evaluation configs:
  - `EVALUATION_MODEL` - "gemini" or "gpt"
  - `GOLD_TABLE_PATH` - path to gold CSV
  - `EVALUATION_PROMPT_PATH` - path to judge prompt

### 4. Main Pipeline Integration (`src/main/main.py`)
- Automatically runs evaluation after extraction
- Gracefully skips if no gold label found
- Logs accuracy metrics
- Handles errors without breaking pipeline

### 5. Cleaned Up Legacy Code (`src/evaluation/evaluation.py`)
- Removed unused functions
- Kept minimal helper for backward compatibility

## Output Structure

```
test_results/{pdf_name}/
├── {pdf_name}.pdf
├── pdf_chunked.json
├── extracted_table.csv
├── extraction_metadata.json
└── metrics/
    ├── evaluation_results.txt          # Full LLM output + summary
    ├── evaluation_summary.json         # Structured metrics
    └── non_null_evaluation.txt         # Filtered to non-null gold values
```

## Metrics Calculated

1. **Overall Accuracy**: All columns (including nulls)
2. **Non-null Accuracy**: Only columns with gold values present

## How to Use

### Automatic (Default)
Just run the pipeline normally:
```bash
python src/main/main.py
```

If a gold label exists for the PDF, evaluation runs automatically.

### Configuration
Change evaluation model in `src/config/config.py`:
```python
EVALUATION_MODEL = "gemini"  # or "gpt"
```

### Gold Table Format
- Must have "Document Name" column
- Document name should match PDF filename (e.g., `NCT02799602_Hussain_ARASENS_JCO'23.pdf`)
- Located at `dataset/GoldTable.csv`

## Dependencies Added
- `python-dotenv` - for loading `.env` file

## API Keys Required
Set in `.env` file:
```
GEMINI_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

## Design Decisions

1. **LLM Choice**: Default to Gemini (free tier, already configured)
2. **Graceful Degradation**: Pipeline continues even if evaluation fails
3. **Minimal Changes**: Reused existing patterns and APIs
4. **Clean Separation**: Evaluation is independent module
5. **Structured Output**: JSON + text for both human and machine consumption

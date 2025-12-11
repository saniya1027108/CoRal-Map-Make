# src/config/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API keys and configurable settings
GROQ_API_KEY = os.getenv("LLAMA_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NOVITA_API_KEY = os.getenv("NOVITA_API_KEY", "")

# GEMINI 
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
GEMINI_MODEL_NAME = "gemini-2.5-flash"  # Or "gemini-1.5-pro" if preferred
OPEN_AI_MODEL = "gpt-4o"
OPENAI_TEMPERATURE = 0.0

# NOVITA AI
NOVITA_MODEL_NAME = "meta-llama/llama-3.1-8b-instruct"  # Or other models from novita.ai catalog

# Add path to definitions CSV
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS_CSV_PATH = PROJECT_ROOT / "src" / "table_definitions" / "Definitions.csv"

# Chunking configs
TEXT_CHUNK_MIN_SIZE = 1000 # Minimum characters per text chunk
# TEXT_CHUNK_MERGE_THRESHOLD = 0.75   # Similarity threshold for merging text chunks, not required now, was used for semantic text chunking

# Preprocessing configs
PATTERN_SAMPLE_PAGES = 5
TOP_MARGIN = 60
BOTTOM_MARGIN = 60
TOP_THRESHOLD_RATIO = 0.1
BOTTOM_THRESHOLD_RATIO = 0.9
HEURISTIC_MAX_LENGTH = 150

# Image processing configs
PIXMAP_RESOLUTION = 6

# Evaluation configs
EVALUATION_MODEL = "gpt"  # "gemini", "gpt", or "novita"
GOLD_TABLE_PATH = PROJECT_ROOT / "dataset" / "GoldTable.csv"
EVALUATION_PROMPT_PATH = PROJECT_ROOT / "src" / "evaluation" / "llm_judge.txt"

#LLM COST METRIC EVALUATION
COST_PER_1K_INPUT = 0.01  # Example: $0.01 per 1K input tokens (adjust for your model)
COST_PER_1K_OUTPUT = 0.03 # Example: $0.03 per 1K output tokens (adjust for your model)

# src/config/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============== API KEYS ==============
# These are loaded from .env file
# For Gemini, we use Vertex AI with service account (config.json in LLMProvider/)
GROQ_API_KEY = os.getenv("LLAMA_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NOVITA_API_KEY = os.getenv("NOVITA_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # <-- Add this if not present
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY", "")

# ============== GCP / VERTEX AI ==============
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_LOCATION = os.getenv("GCP_LOCATION", "")

# ============== PER-TASK LLM CONFIG ==============
# Each task can use a different provider and model
# Supported providers: "gemini", "openai", "novita", "groq", "deepinfra"

# Chunking (image/table analysis - requires multimodal)
CHUNKING_PROVIDER = "openai"
CHUNKING_MODEL = "gpt-4o-mini"

# Extraction (data extraction from text chunks)
EXTRACTION_PROVIDER = "openai"
EXTRACTION_MODEL = "gpt-4o-mini"

# Evaluation (LLM-as-judge)
EVALUATION_PROVIDER = "gemini"
EVALUATION_MODEL = "gemini-2.5-flash"

# ============== PATHS ==============
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS_CSV_PATH = PROJECT_ROOT / "src" / "table_definitions" / "Definitions.csv"
GOLD_TABLE_PATH = PROJECT_ROOT / "dataset" / "GoldTable.csv"
EVALUATION_PROMPT_PATH = PROJECT_ROOT / "src" / "evaluation" / "llm_judge.txt"

# ============== CHUNKING CONFIGS ==============
TEXT_CHUNK_MIN_SIZE = 1000  # Minimum characters per text chunk
PATTERN_SAMPLE_PAGES = 5
TOP_MARGIN = 60
BOTTOM_MARGIN = 60
TOP_THRESHOLD_RATIO = 0.1
BOTTOM_THRESHOLD_RATIO = 0.9
HEURISTIC_MAX_LENGTH = 150

# ============== IMAGE PROCESSING ==============
PIXMAP_RESOLUTION = 6

# ============== EMBEDDINGS ==============
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

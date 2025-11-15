# src/config/config.py
# API keys and configurable settings
GROQ_API_KEY = ""  # Replace with your actual key
GEMINI_API_KEY = ""  # Replace with your actual key

# Other configs (e.g., model names)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
GEMINI_MODEL_NAME = "gemini-2.5-flash"  # Or "gemini-1.5-pro" if preferred

# Chunking configs
TEXT_CHUNK_MIN_SIZE = 500
TEXT_CHUNK_MERGE_THRESHOLD = 0.75

# Preprocessing configs
PATTERN_SAMPLE_PAGES = 5
TOP_MARGIN = 60
BOTTOM_MARGIN = 60
TOP_THRESHOLD_RATIO = 0.1
BOTTOM_THRESHOLD_RATIO = 0.9
HEURISTIC_MAX_LENGTH = 150

# Image processing configs
PIXMAP_RESOLUTION = 6
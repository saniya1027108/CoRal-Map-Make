# src/chunking/utils_chunking.py
# Utility functions for text processing, embeddings, and external API calls
import re
import json
import base64
import pandas as pd
from PIL import Image
from io import BytesIO
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import pdfplumber
from collections import Counter
import fitz 

# Import config
from ..config.config import (
    EMBEDDING_MODEL_NAME,
    TEXT_CHUNK_MIN_SIZE,
    HEURISTIC_MAX_LENGTH,
    CHUNKING_PROVIDER,
    CHUNKING_MODEL
)
from ..utils.logging_utils import setup_logger
from ..LLMProvider import LLMProvider

# Load models (shared across the codebase)
nlp = spacy.load("en_core_web_sm")
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

logger = setup_logger("utils")

# Lazy-loaded chunking provider
_chunking_provider = None

def _get_chunking_provider():
    """Get or initialize the chunking LLM provider."""
    global _chunking_provider
    if _chunking_provider is None:
        _chunking_provider = LLMProvider(provider=CHUNKING_PROVIDER, model=CHUNKING_MODEL)
        logger.info(f"Initialized chunking provider: {CHUNKING_PROVIDER}/{CHUNKING_MODEL}")
    return _chunking_provider


def looks_like_inline_table(text):
    """Check if text resembles an inline table based on digit and pattern density."""
    lines = text.split("\n")
    if len(lines) < 3:
        return False
    digit_lines = sum(1 for line in lines if re.search(r'\d', line) and re.search(r'\(.+\)', line))
    return digit_lines / len(lines) > 0.5


def is_table_caption_or_footnote(text):
    """Check if text is a table caption or footnote based on regex keywords."""
    return bool(
        re.search(r'^\s*(Table|Fig|Figure)\s+\d+', text, re.IGNORECASE)
        or 'TD$FIG' in text
        or re.search(r'\b[A-Z]{2,}\s*=', text)
    )


def text_chunking(text, max_size=TEXT_CHUNK_MIN_SIZE):
    """
    Simple sentence-based text chunking.
    
    Args:
        text: Input text to chunk
        max_size: Maximum size of each chunk in characters
    
    Returns:
        List of text chunks
    """
    doc = nlp(text)
    chunks = []
    current_chunk = ""
    
    for sent in doc.sents:
        sentence = sent.text.strip()
        
        # Skip sentences that look like tables or metadata
        if looks_like_inline_table(sentence) or is_table_caption_or_footnote(sentence):
            continue
        
        # Skip if sentence looks like header/footer
        if is_header_or_footer_by_heuristics(sentence):
            continue
        
        # Check if adding this sentence would exceed max_size
        if current_chunk and len(current_chunk) + len(sentence) + 1 > max_size:
            # Save current chunk and start new one
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            # Add sentence to current chunk
            current_chunk += (" " + sentence) if current_chunk else sentence
    
    # Add the last chunk if it exists
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def extract_caption_from_gemini(text: str) -> str:
    """Extract caption from LLM output."""
    if not text:
        return "Table"

    match = re.search(r"##\s*(Table|Figure)\s*\d*", text, re.IGNORECASE)
    if match:
        start = match.end()
        rest = text[start:].lstrip()
        sentence = rest.split("\n")[0].strip()
        if sentence.endswith(('.', '!', '?')):
            return sentence
        else:
            return sentence + "."

    first_sentence = re.split(r'[.!?]\s*', text)[0].strip()
    return first_sentence + "." if first_sentence else "Table"


def extract_tables_pdfplumber(page) -> list:
    """Extract tables from a pdfplumber page and return as markdown strings."""
    try:
        tables = page.extract_tables()
        md_tables = []
        for tbl in tables:
            if not tbl or len(tbl) < 2:
                continue
            df = pd.DataFrame(tbl[1:], columns=tbl[0])
            md = df.to_markdown(index=False)
            md_tables.append(md.strip())
        return md_tables
    except Exception as e:
        logger.warning(f"[pdfplumber] Error: {e}")
        return []


def extract_images_fitz(page, page_num) -> list:
    """Extract embedded images from a PDF page using PyMuPDF."""
    
    img_chunks = []
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            base = page.parent.extract_image(xref)
            b64 = base64.b64encode(base["image"]).decode()
            img_chunks.append({
                "type": "image",
                "content": f"Image of size {len(b64)} characters (Base64)",
                "page": page_num,
                "length": len(b64),
                "source": "image",
                "image_base64": b64
            })
        except Exception as e:
            logger.warning(f"[Image] Failed XREF {xref}: {e}")
    return img_chunks


def analyze_image_with_llm(image_pil, prompt_text=None):
    """
    Analyze image using configured LLM provider (multimodal).
    
    Uses CHUNKING_PROVIDER and CHUNKING_MODEL from config.
    Supports: Gemini (default), GPT-4V
    
    Args:
        image_pil: PIL Image object
        prompt_text: Optional custom prompt
    
    Returns:
        tuple: (text_response, input_tokens, output_tokens)
    """
    if not prompt_text:
        prompt_text = (
            "Analyze this image from a research paper.\n"
            "If it's a table, return:\n"
            "## Table X\n"
            "Caption sentence.\n"
            "| Header | ...\n\n"
            "If it's a figure, return:\n"
            "## Figure X\n"
            "Description in 2-3 sentences.\n"
            "Return ONLY the content, no JSON."
        )
    
    provider = _get_chunking_provider()
    response = provider.generate_with_image(prompt_text, image_pil)
    
    if response.success:
        return response.text, response.input_tokens, response.output_tokens
    else:
        logger.warning(f"[LLM] Failed: {response.error}")
        return None, 0, 0


# Keep old function name as alias for backward compatibility
def ask_gemini_with_image(image_pil, prompt_text=None):
    """
    Legacy function name. Use analyze_image_with_llm instead.
    
    Returns:
        str: Text response (for backward compatibility, does not return tokens)
    """
    text, _, _ = analyze_image_with_llm(image_pil, prompt_text)
    return text


def save_chunks_to_json(chunks, output_path):
    """Save chunks to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=4)
    logger.info(f"✅ Chunks saved to {output_path}")


def is_header_or_footer_by_heuristics(text):
    """
    Use general heuristics to detect headers/footers.
    This catches common patterns across different journals.
    """
    text_lower = text.lower().strip()
    
    # Common characteristics of headers/footers:
    # 1. Very short (< HEURISTIC_MAX_LENGTH chars)
    if len(text.strip()) > HEURISTIC_MAX_LENGTH:
        return False
    
    # 2. Contains common header/footer keywords
    header_footer_keywords = [
        'copyright', 'downloaded from', 'all rights reserved',
        'massachusetts medical society', 'nejm.org', 'doi:',
        'page', 'vol', 'volume', 'issue', 'published',
        'elsevier', 'wiley', 'springer', 'nature',
        'journal of', 'american', 'society',
        'training, and similar technologies'  # Common copyright clause
    ]
    
    if any(keyword in text_lower for keyword in header_footer_keywords):
        return True
    
    # 3. Pattern: Journal abbreviation + volume/issue + page numbers
    # e.g., "n engl j med 377;4  nejm.org  July 27, 2017"
    if re.search(r'[a-z\s]+\d+[;:]\d+', text_lower):
        return True
    
    # 4. Mostly numbers, dates, or page markers
    # e.g., "339", "July 27, 2017"
    if re.search(r'^\s*\d+\s*$', text):  # Standalone numbers
        return True
    
    # 5. Date patterns
    if re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d+,\s+\d{4}\b', text_lower):
        return True
    
    # 6. URL patterns
    if re.search(r'\b[a-z]+\.(org|com|edu|gov)\b', text_lower):
        return True
    
    # 7. Copyright symbols and years
    if re.search(r'©\s*\d{4}|copyright.*\d{4}', text_lower):
        return True
    
    return False

# src/chunking/chunking.py
# Main chunking logic for PDF processing
import fitz  # PyMuPDF
import re
import json
from PIL import Image
import pdfplumber
from io import BytesIO
from ..config.config import PIXMAP_RESOLUTION
from ..preprocessing.pdf_margin_preprocessing import (
    detect_repeating_patterns,
    clean_page_text_advanced
)
from ..chunking.utils_chunking import (
    text_chunking,
    extract_tables_pdfplumber,
    ask_gemini_with_image,
    extract_images_fitz,
    extract_caption_from_gemini,
    parse_table_extraction_response,
    save_chunks_to_json
)
from ..utils.logging_utils import setup_logger

logger = setup_logger("chunking")


class PDFChunker:
    """
    Class for chunking PDF content into text, tables, figures, and images.
    Orchestrates preprocessing, extraction, and chunk generation.
    """
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.chunks = []
        self.accumulated_text = []  # Accumulate all text from pages
    
    def _process_page_text(self, page, page_num, patterns):
        """Process text content for a single page and accumulate it."""
        page_height = page.rect.height
        raw_text = clean_page_text_advanced(page, page_height, patterns)
        
        # Stop at References
        ref_match = re.search(r'(?i)\b(references|bibliography)\b', raw_text)
        if ref_match:
            raw_text = raw_text[:ref_match.start()].strip()
        
        # Accumulate text from this page (will be chunked later)
        if raw_text.strip():
            self.accumulated_text.append({
                "text": raw_text,
                "page": page_num + 1
            })
    
    def _process_tables(self, page, page_num, pdf_path):
        """Extract and process tables for a single page using LLM with retry logic."""
        try:
            # Use page screenshot for LLM analysis
            pix = page.get_pixmap(matrix=fitz.Matrix(PIXMAP_RESOLUTION, PIXMAP_RESOLUTION))
            img_bytes = pix.tobytes("png")
            img_pil = Image.open(BytesIO(img_bytes))
            
            # Load table extraction prompt
            from pathlib import Path
            prompt_path = Path(__file__).parent / "table_extraction.txt"
            if not prompt_path.exists():
                logger.warning(f"[Table] Prompt file not found: {prompt_path}, using default")
                prompt_text = None
            else:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_text = f.read()
            
            # Retry logic: try up to 3 times to get valid table extraction
            max_retries = 3
            markdown_table = None
            caption = "Table"
            
            for attempt in range(1, max_retries + 1):
                # Call LLM to extract table and caption
                llm_response = ask_gemini_with_image(img_pil, prompt_text=prompt_text)
                
                if not llm_response:
                    logger.warning(f"[Table] Page {page_num + 1}, attempt {attempt}/{max_retries}: No LLM response")
                    if attempt < max_retries:
                        continue
                    else:
                        break
                
                # Parse LLM response to extract markdown table and caption
                parsed = parse_table_extraction_response(llm_response)
                markdown_table = parsed.get("markdown_table")
                caption = parsed.get("caption") or "Table"
                
                if markdown_table:
                    logger.info(f"[Table] Page {page_num + 1}: Successfully extracted table on attempt {attempt}")
                    break
                else:
                    logger.warning(f"[Table] Page {page_num + 1}, attempt {attempt}/{max_retries}: Could not extract table from LLM response")
                    if attempt < max_retries:
                        logger.info(f"[Table] Page {page_num + 1}: Retrying...")
            
            # If all retries failed, fallback to pdfplumber
            if not markdown_table:
                logger.warning(f"[Table] Page {page_num + 1}: All {max_retries} LLM attempts failed, trying pdfplumber fallback")
                try:
                    with pdfplumber.open(pdf_path) as plumber:
                        pl_page = plumber.pages[page_num]
                        md_tables = extract_tables_pdfplumber(pl_page)
                        if md_tables:
                            markdown_table = md_tables[0]
                            logger.info(f"[Table] Page {page_num + 1}: Using pdfplumber fallback")
                        else:
                            logger.warning(f"[Table] Page {page_num + 1}: pdfplumber found no tables")
                            return
                except Exception as e:
                    logger.warning(f"[Table] Page {page_num + 1}: pdfplumber fallback failed: {e}")
                    return
            
            # Create table chunk with LLM-generated content (or pdfplumber fallback)
            self.chunks.append({
                "type": "table",
                "content": caption,
                "page": page_num + 1,
                "length": len(img_bytes),
                "source": "image",
                "table_content": f"##Markdown Table##\n\n{markdown_table}\n\n##Caption##\n\n{caption}"
            })
            
        except Exception as e:
            logger.warning(f"[Table] Page {page_num + 1} failed: {e}")
    
    def _process_figures(self, raw_text, page, page_num):
        """Extract and process figures if detected on the page."""
        if re.search(r"\bfig(?:ure)?s?[ .:-]*\d+", raw_text, re.IGNORECASE):
            pix = page.get_pixmap(matrix=fitz.Matrix(PIXMAP_RESOLUTION, PIXMAP_RESOLUTION))
            img_bytes = pix.tobytes("png")
            img_pil = Image.open(BytesIO(img_bytes))
            gemini_raw = ask_gemini_with_image(img_pil)
            description = gemini_raw.strip() if gemini_raw else "Figure"
            
            block = f"```\n##Figure Descriptions##\n\n{description}\n```"
            self.chunks.append({
                "type": "figure",
                "content": block,
                "page": page_num + 1,
                "length": len(img_bytes),
                "source": "image",
                "figure_content": block
            })
    
    def _process_embedded_images(self, page, page_num):
        """Extract embedded images from the page."""
        img_chunks = extract_images_fitz(page, page_num + 1)
        self.chunks.extend(img_chunks)
    
    def _create_large_text_chunks(self):
        """Create 4-5 large text chunks from all accumulated text."""
        if not self.accumulated_text:
            return
        
        # Combine all text from all pages
        all_text = "\n\n".join([item["text"] for item in self.accumulated_text])
        
        # Get the page range for reference
        page_numbers = [item["page"] for item in self.accumulated_text]
        min_page = min(page_numbers) if page_numbers else 1
        max_page = max(page_numbers) if page_numbers else 1
        
        # Generate large text chunks (4-5 chunks total)
        text_chunks = text_chunking(all_text)
        
        logger.info(f"📝 Created {len(text_chunks)} large text chunks from {len(self.accumulated_text)} pages")
        
        # Add text chunks to the chunks list
        for idx, txt in enumerate(text_chunks, 1):
            self.chunks.append({
                "type": "text",
                "content": txt,
                "page": f"{min_page}-{max_page}",  # Show page range
                "chunk_number": idx,
                "length": len(txt)
            })
    
    def chunk(self):
        """Main method to process the entire PDF and generate chunks."""
        try:
            # Step 0: Learn header/footer patterns
            logger.info("🔍 Analyzing PDF for header/footer patterns...")
            patterns = detect_repeating_patterns(self.pdf_path)
            logger.info(f"   Found {len(patterns['top_patterns'])} top patterns and {len(patterns['bottom_patterns'])} bottom patterns")
            
            doc = fitz.open(self.pdf_path)
            stop_processing = False

            for page_num in range(len(doc)):
                if stop_processing:
                    break

                page = doc[page_num]
                
                # Accumulate text (will be chunked later)
                raw_text = clean_page_text_advanced(page, page.rect.height, patterns)
                self._process_page_text(page, page_num, patterns)
                
                # Process tables (as before - no changes)
                self._process_tables(page, page_num, self.pdf_path)
                
                # Process figures (as before - no changes)
                self._process_figures(raw_text, page, page_num)
                
                # Process embedded images (as before - no changes)
                self._process_embedded_images(page, page_num)

            doc.close()
            
            # After processing all pages, create large text chunks (4-5 per PDF)
            self._create_large_text_chunks()
            
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
        
        return self.chunks


def process_pdf(pdf_path, output_path="pdf_chunks.json"):
    """Entry point function to process PDF using the PDFChunker class."""
    logger.info(f"\n🔄 Processing PDF: {pdf_path} ...\n")
    chunker = PDFChunker(pdf_path)
    chunks = chunker.chunk()
    logger.info(f"✅ Extracted {len(chunks)} chunks.")
    save_chunks_to_json(chunks, output_path)
    logger.info("\n📄 Sample Chunk:\n")
    logger.info(json.dumps(chunks[0] if chunks else {}, indent=4, ensure_ascii=False))
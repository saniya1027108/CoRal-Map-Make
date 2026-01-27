# src/utils/context_generator.py
"""
Generate plain text extraction guide from clinical trial PDF using Gemini.
Reads PDF as bytes and sends directly to Gemini for analysis.
Creates comprehensive context to improve extraction accuracy.
"""
import time
from pathlib import Path
from typing import Optional
from google.genai import types
from ..LLMProvider import LLMProvider
from .logging_utils import setup_logger

logger = setup_logger("context_generator")


# Comprehensive prompt for context generation (plain text output)
CONTEXT_GENERATION_PROMPT = """=== TASK: GENERATE EXTRACTION GUIDE ===

You are analyzing a clinical trial publication to create an extraction guide.
Your job is to BRIDGE the gap between generic column definitions and this paper's specific terminology and structure.


=== COLUMNS TO EXTRACT (Categories) ===
1. Trial Metadata: NCT ID, Author, Year, Phase, Trial Name
2. Study Design: Arms, regimens, sample sizes, follow-up
3. Demographics: Age, race, region BY ARM (Treatment vs Control)
4. Disease Characteristics BY ARM:
   - Mode of metastases: Synchronous, Metachronous
   - Volume: High, Low
   - Sites: Liver, Lung, Bone, Nodal
   - Gleason score, Performance status
5. Outcomes BY ARM AND SUBGROUP:
   - OS: Overall, High/Low volume, Synchronous/Metachronous
   - PFS: Overall, High/Low volume
   - ORR, Response rates
6. Safety: Adverse events (Grade 3+, Grade 5), Deaths

=== WHAT TO GENERATE ===

Create a comprehensive plain text guide with these sections:

**SECTION 1: TRIAL IDENTITY**
- NCT ID, Trial name (short and full), First author, Year, Phase, Design

**SECTION 2: ARM MAPPING**
For each arm (Treatment and Control):
- Official name
- How it's referred to in the text, and tables.

**SECTION 3: DATA ORGANIZATION**
Describe how data is organized in the paper:
- Patient stratification: How are patients grouped? (by volume, metastases type, both?)
- How are the results reported? (by arm, by subgroup, by both?)


=== CRITICAL INSTRUCTIONS ===

1. BE EXHAUSTIVE with synonyms - list ALL variations you see in tables and text
2. BE EXPLICIT with aggregation rules - show exact calculations with numbers
3. IDENTIFY table structures precisely - which table contains what data
4. WARN about edge cases - implicit zeros, overlapping categories, missing stratification
5. Use EXACT terminology from the paper (quote table headers, figure labels)
6. For arm mapping: Check abstract, methods, tables, figure legends for ALL references
7. Do not return references to tables or figures in the guide. This is supposed to be a general guide which can be passed with chunks of the paper as additional context to perform the extraction.

=== OUTPUT FORMAT ===
Return a clear, well-organized plain text guide following the sections above. Use headers, bullet points, and clear formatting. Be comprehensive and specific."""


def generate_trial_context(
    pdf_path: str,
    provider: Optional[LLMProvider] = None,
    max_retries: int = 3,
    api_key: Optional[str] = None
) -> str:
    """
    Generate plain text extraction guide by reading PDF as bytes.
    
    Args:
        pdf_path: Path to PDF file
        provider: LLMProvider instance (creates new if None)
        max_retries: Number of retry attempts for API failures
        api_key: Gemini API key (optional, unused but kept for compatibility)
    
    Returns:
        Plain text extraction guide ready for system_prompt
    
    Raises:
        Exception: If generation fails after all retries
    """
    logger.info(f"Generating extraction guide for: {Path(pdf_path).name}")
    
    # Initialize provider if not provided
    if provider is None:
        from ..config.config import CONTEXT_GENERATION_PROVIDER, CONTEXT_GENERATION_MODEL
        provider = LLMProvider(
            provider=CONTEXT_GENERATION_PROVIDER,
            model=CONTEXT_GENERATION_MODEL
        )
        logger.info(f"Using provider: {CONTEXT_GENERATION_PROVIDER}/{CONTEXT_GENERATION_MODEL}")
    
    # Read PDF as bytes (fast, local operation)
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    logger.info(f"Reading PDF as bytes ({pdf_path_obj.stat().st_size / 1024 / 1024:.2f} MB)...")
    pdf_bytes = pdf_path_obj.read_bytes()
    
    # Create PDF Part for Gemini
    pdf_part = types.Part.from_bytes(
        data=pdf_bytes,
        mime_type="application/pdf"
    )
    logger.info("PDF loaded into memory, ready for analysis")
    
    # Generate context with retries (for API failures only)
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Generating context (attempt {attempt}/{max_retries})...")
            
            # Build config with system instruction
            config = types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=32000,
                system_instruction="You are an expert clinical trial analyzer. Generate comprehensive extraction guides in clear, well-organized plain text format."
            )
            
            # Call Gemini API directly with PDF bytes
            # NOTE: PDF part comes FIRST, then the prompt (order matters!)
            raw_response = provider._client.models.generate_content(
                model=provider.model,
                contents=[
                    pdf_part,  # PDF bytes (FIRST!)
                    f"""Analyze the uploaded PDF clinical trial paper.

{CONTEXT_GENERATION_PROMPT}"""  # Prompt (SECOND!)
                ],
                config=config
            )
            
            # Extract usage metadata
            usage = getattr(raw_response, 'usage_metadata', None)
            input_tokens = getattr(usage, 'prompt_token_count', 0) if usage else 0
            output_tokens = getattr(usage, 'candidates_token_count', 0) if usage else 0
            cost = provider._calculate_cost(input_tokens, output_tokens)
            
            # Get plain text response
            context_text = raw_response.text.strip()
            
            # Clean markdown code blocks if wrapped (just in case)
            if context_text.startswith("```"):
                lines = context_text.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]  # Remove opening ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # Remove closing ```
                context_text = '\n'.join(lines).strip()
            
            # Basic validation - should be substantial
            if len(context_text) < 500:
                logger.warning(f"Generated context seems too short ({len(context_text)} chars)")
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            
            logger.info("✅ Context generated successfully")
            logger.info(f"Context length: {len(context_text)} characters")
            logger.info(f"Tokens used: {input_tokens} in, {output_tokens} out")
            logger.info(f"Cost: ${cost:.4f}")
            
            return context_text
        
        except Exception as e:
            logger.warning(f"Context generation attempt {attempt} failed: {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Context generation failed after {max_retries} attempts: {e}")

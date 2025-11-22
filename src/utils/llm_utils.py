# src/utils/llm_utils.py
import google.generativeai as genai
import openai
from pathlib import Path
from ..config.config import GEMINI_API_KEY, GEMINI_MODEL_NAME, OPENAI_API_KEY, OPEN_AI_MODEL
from ..utils.logging_utils import setup_logger

logger = setup_logger("llm_utils")

# Configure APIs
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
openai.api_key = OPENAI_API_KEY


def ask_llm_text(prompt_path, text, model_type="gemini"):
    """
    Send text prompt to LLM and get response.
    
    Args:
        prompt_path: Path to prompt template file
        text: Text content to append to prompt
        model_type: "gemini" or "gpt"
    
    Returns:
        str: LLM response
    """
    # Load prompt template
    prompt_template = Path(prompt_path).read_text(encoding="utf-8")
    full_prompt = f"{prompt_template}\n\n{text}"
    
    try:
        if model_type.lower() == "gemini":
            response = gemini_model.generate_content(full_prompt)
            return response.text.strip()
        
        elif model_type.lower() == "gpt":
            response = openai.chat.completions.create(
                model=OPEN_AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert evaluator for clinical trial data extraction."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.0,
                max_tokens=4000
            )
            return response.choices[0].message.content.strip()
        
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    except Exception as e:
        logger.error(f"LLM call failed ({model_type}): {e}")
        return None

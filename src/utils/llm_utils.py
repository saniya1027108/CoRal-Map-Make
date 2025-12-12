# src/utils/llm_utils.py
import google.generativeai as genai
from groq import Groq
import openai
from openai import OpenAI
from pathlib import Path
from ..config.config import (
    GEMINI_API_KEY, GEMINI_MODEL_NAME, 
    OPENAI_API_KEY, OPEN_AI_MODEL, OPENAI_TEMPERATURE,
    NOVITA_API_KEY, NOVITA_MODEL_NAME,
    GROQ_API_KEY, GROQ_MODEL_NAME
)
from ..utils.logging_utils import setup_logger

logger = setup_logger("llm_utils")

# Configure APIs
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
openai.api_key = OPENAI_API_KEY

# Groq client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Novita AI client (OpenAI-compatible)
novita_client = OpenAI(
    base_url="https://api.novita.ai/v3/openai",
    api_key=NOVITA_API_KEY
) if NOVITA_API_KEY else None


def ask_llm_text(prompt_path, text, model_type="gemini"):
    """
    Send text prompt to LLM and get response.
    
    Args:
        prompt_path: Path to prompt template file
        text: Text content to append to prompt
        model_type: "gemini", "gpt", "novita", "groq"
    
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
                temperature=OPENAI_TEMPERATURE,
                max_tokens=4000
            )
            return response.choices[0].message.content.strip()
        
        elif model_type.lower() == "novita":
            response = novita_client.chat.completions.create(
                model=NOVITA_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert evaluator for clinical trial data extraction."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.0,
                max_tokens=4000
            )
            return response.choices[0].message.content.strip()
        
        elif model_type.lower() == "groq" and groq_client:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL_NAME,
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
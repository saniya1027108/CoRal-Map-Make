# src/LLMProvider/provider.py
"""
Unified LLM Provider for all inference tasks.
Supports: Gemini (Vertex AI), OpenAI, Novita, Groq
"""
import os
from dataclasses import dataclass
from typing import Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from io import BytesIO
from pathlib import Path

from vertexai import init as vertex_init
from vertexai.generative_models import GenerativeModel, Part
from openai import OpenAI
from groq import Groq
from dotenv import load_dotenv

from .models import get_model_pricing

load_dotenv()

# Vertex AI initialization flag
_VERTEX_INITIALIZED = False


def _ensure_vertex_init():
    """Initialize Vertex AI once (lazy initialization)."""
    global _VERTEX_INITIALIZED
    if not _VERTEX_INITIALIZED:
        project_id = os.getenv("GCP_PROJECT_ID", "")
        location = os.getenv("GCP_LOCATION", "")
        
        # Set credentials path if config.json exists
        config_json_path = Path(__file__).parent / "config.json"
        if config_json_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(config_json_path)
        
        vertex_init(project=project_id, location=location)
        _VERTEX_INITIALIZED = True


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    cost: float
    success: bool
    error: Optional[str] = None


class LLMProvider:
    """
    Unified interface for LLM providers.
    
    Usage:
        provider = LLMProvider(provider="gemini", model="gemini-2.5-flash")
        response = provider.generate("Hello, world!")
        response = provider.generate_with_image("Describe this", image_pil)
        responses = provider.batch_generate(["prompt1", "prompt2"])
    
    Supported providers:
        - gemini: Google Gemini via Vertex AI
        - openai: OpenAI GPT models
        - novita: Novita AI (OpenAI-compatible)
        - groq: Groq (fast inference)
    """
    
    def __init__(self, provider: str = "gemini", model: str = None):
        """
        Initialize LLM provider.
        
        Args:
            provider: "gemini", "openai", "novita", "groq"
            model: Specific model name (uses default if not provided)
        """
        self.provider = provider.lower()
        self.model = model or self._get_default_model()
        self._client = None
        self._init_client()
    
    def _get_default_model(self) -> str:
        """Get default model for provider."""
        defaults = {
            "gemini": "gemini-2.5-flash",
            "openai": "gpt-4o",
            "novita": "meta-llama/llama-3.1-8b-instruct",
            "groq": "llama-3.1-70b-versatile"
        }
        return defaults.get(self.provider, "gemini-2.5-flash")
    
    def _init_client(self):
        """Initialize the appropriate client based on provider."""
        if self.provider == "gemini":
            _ensure_vertex_init()
            self._client = GenerativeModel(self.model)
        
        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self._client = OpenAI(api_key=api_key)
        
        elif self.provider == "novita":
            api_key = os.getenv("NOVITA_API_KEY")
            if not api_key:
                raise ValueError("NOVITA_API_KEY environment variable not set")
            self._client = OpenAI(
                base_url="https://api.novita.ai/v3/openai",
                api_key=api_key
            )
        
        elif self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLAMA_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY or LLAMA_KEY environment variable not set")
            self._client = Groq(api_key=api_key)
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Supported: gemini, openai, novita, groq")
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        pricing = get_model_pricing(self.provider, self.model)
        return (input_tokens * pricing["input"] / 1000) + (output_tokens * pricing["output"] / 1000)
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.0,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """
        Generate text response.
        
        Args:
            prompt: User prompt
            system_prompt: System instruction (optional)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum output tokens
        
        Returns:
            LLMResponse with text, tokens, cost, and success status
        """
        try:
            if self.provider == "gemini":
                return self._generate_gemini(prompt, system_prompt, temperature, max_tokens)
            else:
                return self._generate_openai_compatible(prompt, system_prompt, temperature, max_tokens)
        
        except Exception as e:
            return LLMResponse(
                text="",
                input_tokens=0,
                output_tokens=0,
                model=self.model,
                provider=self.provider,
                cost=0.0,
                success=False,
                error=str(e)
            )
    
    def _generate_gemini(
        self, 
        prompt: str, 
        system_prompt: str, 
        temperature: float, 
        max_tokens: int
    ) -> LLMResponse:
        """Generate using Vertex AI Gemini."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        response = self._client.generate_content(
            full_prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )
        
        # Extract token counts from usage metadata
        usage = getattr(response, 'usage_metadata', None)
        input_tokens = getattr(usage, 'prompt_token_count', 0) if usage else 0
        output_tokens = getattr(usage, 'candidates_token_count', 0) if usage else 0
        
        return LLMResponse(
            text=response.text.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            provider=self.provider,
            cost=self._calculate_cost(input_tokens, output_tokens),
            success=True
        )
    
    def _generate_openai_compatible(
        self, 
        prompt: str, 
        system_prompt: str, 
        temperature: float, 
        max_tokens: int
    ) -> LLMResponse:
        """Generate using OpenAI-compatible API (OpenAI, Novita, Groq)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        usage = getattr(response, 'usage', None)
        input_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
        output_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
        
        return LLMResponse(
            text=response.choices[0].message.content.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            provider=self.provider,
            cost=self._calculate_cost(input_tokens, output_tokens),
            success=True
        )
    
    def generate_with_image(
        self,
        prompt: str,
        image: Union[Image.Image, bytes],
        temperature: float = 0.0,
        max_tokens: int = 4000
    ) -> LLMResponse:
        """
        Generate response with image input (multimodal).
        
        Supported:
            - Gemini models (all have vision)
            - OpenAI GPT-4 models (gpt-4o, gpt-4-turbo)
        
        Args:
            prompt: Text prompt
            image: PIL Image or bytes
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        
        Returns:
            LLMResponse
        """
        try:
            if self.provider == "gemini":
                return self._generate_gemini_with_image(prompt, image, temperature, max_tokens)
            elif self.provider == "openai" and "gpt-4" in self.model:
                return self._generate_openai_with_image(prompt, image, temperature, max_tokens)
            else:
                raise ValueError(f"Multimodal not supported for {self.provider}/{self.model}")
        
        except Exception as e:
            return LLMResponse(
                text="",
                input_tokens=0,
                output_tokens=0,
                model=self.model,
                provider=self.provider,
                cost=0.0,
                success=False,
                error=str(e)
            )
    
    def _generate_gemini_with_image(
        self, 
        prompt: str, 
        image: Union[Image.Image, bytes], 
        temperature: float, 
        max_tokens: int
    ) -> LLMResponse:
        """Generate with image using Gemini."""
        # Convert PIL to bytes if needed
        if isinstance(image, Image.Image):
            buf = BytesIO()
            image.save(buf, format="PNG")
            image_bytes = buf.getvalue()
        else:
            image_bytes = image
        
        image_part = Part.from_data(image_bytes, mime_type="image/png")
        
        response = self._client.generate_content(
            [prompt, image_part],
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )
        
        usage = getattr(response, 'usage_metadata', None)
        input_tokens = getattr(usage, 'prompt_token_count', 0) if usage else 0
        output_tokens = getattr(usage, 'candidates_token_count', 0) if usage else 0
        
        return LLMResponse(
            text=response.text.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            provider=self.provider,
            cost=self._calculate_cost(input_tokens, output_tokens),
            success=True
        )
    
    def _generate_openai_with_image(
        self, 
        prompt: str, 
        image: Union[Image.Image, bytes], 
        temperature: float, 
        max_tokens: int
    ) -> LLMResponse:
        """Generate with image using GPT-4V."""
        import base64
        
        if isinstance(image, Image.Image):
            buf = BytesIO()
            image.save(buf, format="PNG")
            image_bytes = buf.getvalue()
        else:
            image_bytes = image
        
        b64_image = base64.b64encode(image_bytes).decode()
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                ]
            }],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        usage = getattr(response, 'usage', None)
        input_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
        output_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0
        
        return LLMResponse(
            text=response.choices[0].message.content.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            provider=self.provider,
            cost=self._calculate_cost(input_tokens, output_tokens),
            success=True
        )
    
    def batch_generate(
        self,
        prompts: list,
        system_prompt: str = None,
        max_workers: int = 5,
        temperature: float = 0.0,
        max_tokens: int = 4000
    ) -> list:
        """
        Generate responses for multiple prompts in parallel.
        
        Args:
            prompts: List of prompts
            system_prompt: System instruction (applied to all)
            max_workers: Number of parallel threads
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        
        Returns:
            List of LLMResponse in same order as prompts
        """
        results = [None] * len(prompts)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(
                    self.generate, prompt, system_prompt, temperature, max_tokens
                ): i
                for i, prompt in enumerate(prompts)
            }
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = LLMResponse(
                        text="",
                        input_tokens=0,
                        output_tokens=0,
                        model=self.model,
                        provider=self.provider,
                        cost=0.0,
                        success=False,
                        error=str(e)
                    )
        
        return results
    
    def __repr__(self) -> str:
        return f"LLMProvider(provider='{self.provider}', model='{self.model}')"


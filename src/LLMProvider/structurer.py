# src/LLMProvider/structurer.py
"""
Output Structurer for converting free-form LLM reasoning into structured JSON.
Uses a local model (localhost:8001) with OpenAI-compatible API.
"""
import json
import re
from typing import Type, TypeVar, Union, Optional
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError
from openai import OpenAI

T = TypeVar('T', bound=BaseModel)


@dataclass
class StructurerResponse:
    """Response from the output structurer."""
    data: Union[BaseModel, dict]
    success: bool
    attempts: int
    error: Optional[str] = None


class OutputStructurer:
    """
    Structures free-form text into JSON using a local LLM.
    
    Usage:
        structurer = OutputStructurer(base_url="http://localhost:8001")
        result = structurer.structure(
            text="Patient is 65 years old with prostate cancer...",
            schema=PatientDataModel,
            max_retries=3
        )
        
        if result.success:
            patient_data = result.data  # Pydantic model instance
            print(patient_data.age)
    """
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8001/v1",
        model: str = "Qwen/Qwen3-8B",  # Full HuggingFace path
        api_key: str = "not-needed",  # Local models don't need real API keys
        debug_file: Optional[str] = None  # Path to debug file for logging
    ):
        """
        Initialize the output structurer.
        
        Args:
            base_url: Base URL for the local model API (default: http://localhost:8001/v1)
            model: Model name (default: Qwen/Qwen3-8B)
            api_key: API key (not needed for local, but required by OpenAI SDK)
            debug_file: Optional path to file for logging raw LLM responses
        """
        self.base_url = base_url
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.debug_file = debug_file
    
    def structure(
        self,
        text: str,
        schema: Type[T],
        max_retries: int = 3,
        temperature: float = 0.0,
        return_dict: bool = False
    ) -> StructurerResponse:
        """
        Structure free-form text into JSON matching the provided schema.
        
        Args:
            text: Free-form reasoning text from LLM
            schema: Pydantic BaseModel class defining the expected structure
            max_retries: Number of retry attempts if validation fails (default: 3)
            temperature: Sampling temperature (default: 0.0 for deterministic)
            return_dict: If True, return dict instead of Pydantic instance (default: False)
        
        Returns:
            StructurerResponse with structured data (Pydantic model or dict)
        """
        # Generate JSON schema from Pydantic model
        json_schema = schema.model_json_schema()
        
        # Create prompt for structuring
        prompt = self._create_structuring_prompt(text, json_schema)
        
        # Attempt to structure with retries
        for attempt in range(1, max_retries + 1):
            try:
                # Call local model
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a JSON structuring assistant. Extract and structure information from the given text into valid JSON matching the provided schema. Output ONLY valid JSON, no explanations."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=temperature,
                )
                
                # Extract response text
                response_text = response.choices[0].message.content.strip()
                
                # DEBUG: Log raw LLM response
                if self.debug_file:
                    with open(self.debug_file, 'a') as f:
                        f.write(f"\n{'='*80}\n")
                        f.write(f"RAW LOCAL LLM RESPONSE (Attempt {attempt}):\n")
                        f.write(f"{'='*80}\n")
                        f.write(response_text)
                        f.write("\n")
                
                # Try to parse JSON (returns list or dict)
                structured_json = self._extract_json(response_text)
                
                # DEBUG: Log what we extracted
                if self.debug_file:
                    with open(self.debug_file, 'a') as f:
                        f.write(f"\n📦 Extracted JSON type: {type(structured_json).__name__}\n")
                        f.write(f"📦 Extracted JSON: {json.dumps(structured_json, indent=2)[:200]}...\n")
                
                # Auto-wrap if needed:
                # Option 1: LLM returned array → wrap with schema's array field key
                # Option 2: LLM returned dict with correct key → use as-is
                if isinstance(structured_json, list):
                    array_field = self._find_array_field(schema)
                    if array_field:
                        if self.debug_file:
                            with open(self.debug_file, 'a') as f:
                                f.write(f"⚠️  Auto-wrapping bare array with key '{array_field}'\n")
                        structured_json = {array_field: structured_json}
                    else:
                        raise ValueError(f"Schema has no array field, but LLM returned array")
                
                # Validate against Pydantic schema
                structured_data = schema.model_validate(structured_json)
                
                # Success!
                return StructurerResponse(
                    data=structured_data.model_dump() if return_dict else structured_data,
                    success=True,
                    attempts=attempt
                )
            
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt == max_retries:
                    # Final attempt failed
                    return StructurerResponse(
                        data={},
                        success=False,
                        attempts=attempt,
                        error=f"Failed after {max_retries} attempts. Last error: {str(e)}"
                    )
                # Continue to next retry
                continue
            
            except Exception as e:
                # Unexpected error (network, API, etc.)
                return StructurerResponse(
                    data={},
                    success=False,
                    attempts=attempt,
                    error=f"Unexpected error: {str(e)}"
                )
        
        # Should not reach here, but just in case
        return StructurerResponse(
            data={},
            success=False,
            attempts=max_retries,
            error="Unknown error occurred"
        )
    
    def _find_array_field(self, schema: Type[T]) -> Optional[str]:
        """
        Find the first List field name in the Pydantic schema.
        Used to auto-wrap bare arrays when LLM outputs [...] instead of {"field": [...]}.
        
        Args:
            schema: Pydantic BaseModel class
        
        Returns:
            Field name (str) or None if no List field found
        """
        for field_name, field_info in schema.model_fields.items():
            # Check if field annotation is a List type
            annotation = field_info.annotation
            
            # Handle typing.List, list, and Optional[List] cases
            if hasattr(annotation, '__origin__'):
                origin = annotation.__origin__
                # Check for list or List
                if origin is list:
                    return field_name
                # Handle Union types (e.g., Optional[List[...]] = Union[List, None])
                if origin is Union:
                    for arg in annotation.__args__:
                        if hasattr(arg, '__origin__') and arg.__origin__ is list:
                            return field_name
        
        return None
    
    def _create_structuring_prompt(self, text: str, json_schema: dict) -> str:
        """Create the structuring prompt with text and schema."""
        # Simplified prompt: just ask for array of objects
        return f"""Extract information from the following text and return a JSON array.

Each item in the array should have these fields:
- page: integer (page number)
- name: string (table/figure name or number)
- description: string (brief description of content)

Example format:
[
  {{"page": 3, "name": "Table 1", "description": "Patient demographics"}},
  {{"page": 5, "name": "Figure 2", "description": "Survival curves"}}
]

TEXT:
{text}

Output ONLY the JSON array. No explanations, no markdown formatting."""
    
    def _strip_think_tags(self, text: str) -> str:
        """
        Remove <think>...</think> blocks from LLM response.
        Some models output reasoning in think tags before the actual response.
        """
        # Remove everything between <think> and </think> (including tags)
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()
    
    def _extract_json(self, text: str):
        """
        Extract and parse JSON from response text.
        After stripping think tags, this should be clean JSON (array or object).
        Returns dict or list.
        """
        # STEP 1: Strip <think> tags
        text = self._strip_think_tags(text)
        
        # STEP 2: Parse the JSON directly - should be clean after stripping tags
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # If it fails, log for debugging and re-raise
            if self.debug_file:
                with open(self.debug_file, 'a') as f:
                    f.write(f"\n❌ JSON Parse Error: {e}\n")
                    f.write(f"Text after think tag stripping:\n{text[:500]}\n")
            raise
    
    
    def __repr__(self) -> str:
        return f"OutputStructurer(base_url='{self.base_url}', model='{self.model}')"

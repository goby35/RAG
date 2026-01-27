# services/llm_service.py
"""
LLM Service - Handles interactions with Language Models.
"""

from typing import Optional, Dict, Any, List
import json
import logging

from core.base import BaseService
from core.interfaces import ILLMClient
from core.exceptions import LLMError
from config.models import ModelConfig, LLMModelConfig, LLMProviderType

logger = logging.getLogger(__name__)


class OpenAIClient(ILLMClient):
    """OpenAI API client implementation."""
    
    def __init__(self, config: LLMModelConfig, api_key: str):
        self._config = config
        self._api_key = api_key
        self._client = None
    
    @property
    def client(self):
        """Lazy load the OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text response."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self._config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(
                f"Failed to generate response: {e}",
                model=self._config.model_name,
                provider="openai"
            )
    
    def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON response."""
        # Add JSON instruction to prompt
        json_prompt = f"""{prompt}

Respond ONLY with valid JSON. No explanation text before or after."""
        
        try:
            response = self.generate(
                json_prompt,
                max_tokens=self._config.max_tokens,
                temperature=0.3  # Lower temperature for structured output
            )
            
            # Extract JSON from response
            response = response.strip()
            
            # Try to find JSON in response
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Failed to parse JSON response: {e}",
                model=self._config.model_name,
                provider="openai"
            )
    
    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._config.model_name


class LLMService(BaseService):
    """
    Service for LLM operations.
    
    Manages:
    - Text generation
    - Structured output (JSON)
    - Prompt templates
    """
    
    def __init__(
        self,
        config: Optional[LLMModelConfig] = None,
        api_key: Optional[str] = None
    ):
        super().__init__("LLMService")
        self._config = config or ModelConfig.DEFAULT_LLM
        self._api_key = api_key
        self._client: Optional[ILLMClient] = None
    
    def initialize(self) -> None:
        """Initialize the LLM service."""
        if self._api_key is None:
            from config.settings import get_settings
            self._api_key = get_settings().openai_api_key
        
        if self._config.provider == LLMProviderType.OPENAI:
            self._client = OpenAIClient(self._config, self._api_key)
        else:
            raise LLMError(f"Unsupported LLM provider: {self._config.provider}")
        
        super().initialize()
    
    @property
    def client(self) -> ILLMClient:
        """Get the LLM client."""
        self._ensure_initialized()
        return self._client
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text response."""
        self._ensure_initialized()
        
        return self._client.generate(
            prompt=prompt,
            max_tokens=max_tokens or self._config.max_tokens,
            temperature=temperature or self._config.temperature,
            system_prompt=system_prompt
        )
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate structured JSON response."""
        self._ensure_initialized()
        return self._client.generate_json(prompt, schema)
    
    def generate_with_context(
        self,
        query: str,
        context: List[str],
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate response with context documents."""
        context_str = "\n\n".join(context)
        
        prompt = f"""Based on the following context, answer the question.

Context:
{context_str}

Question: {query}

Answer:"""
        
        return self.generate(prompt, system_prompt=system_prompt)


# Backward compatibility function
def generate_response(prompt: str) -> str:
    """Generate response (backward compatibility)."""
    from openai import OpenAI
    from config.settings import get_openai_api_key
    from config.models import LLM_MODEL, MAX_TOKENS_RESPONSE
    
    client = OpenAI(api_key=get_openai_api_key())
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=MAX_TOKENS_RESPONSE
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Lỗi khi gọi OpenAI API: {str(e)}"

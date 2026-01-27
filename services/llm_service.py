# services/llm_service.py
"""
LLM Service - Handles interactions with Language Models.

Main Model: Cerebras (Llama 3.1-70B) - Super fast for chatbot, reasoning, RAG
Fallback Model: Groq (Llama 3-70B) - When Cerebras is overloaded
"""

from typing import Optional, Dict, Any, List
import json
import logging

from core.base import BaseService
from core.interfaces import ILLMClient
from core.exceptions import LLMError
from config.models import ModelConfig, LLMModelConfig, LLMProviderType

logger = logging.getLogger(__name__)


class BaseLLMClient(ILLMClient):
    """Base LLM client with common functionality."""
    
    def __init__(self, config: LLMModelConfig, api_key: str, provider_name: str):
        self._config = config
        self._api_key = api_key
        self._provider_name = provider_name
        self._client = None
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from response, handling markdown code blocks."""
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()
    
    def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON response."""
        json_prompt = f"""{prompt}

Respond ONLY with valid JSON. No explanation text before or after."""
        
        try:
            response = self.generate(
                json_prompt,
                max_tokens=self._config.max_tokens,
                temperature=0.3
            )
            return json.loads(self._extract_json_from_response(response))
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Failed to parse JSON response: {e}",
                model=self._config.model_name,
                provider=self._provider_name
            )
    
    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._config.model_name


class CerebrasClient(BaseLLMClient):
    """Cerebras API client - Main model for super fast inference."""
    
    def __init__(self, config: LLMModelConfig, api_key: str):
        super().__init__(config, api_key, "cerebras")
    
    @property
    def client(self):
        """Lazy load the Cerebras client."""
        if self._client is None:
            from cerebras.cloud.sdk import Cerebras
            self._client = Cerebras(api_key=self._api_key)
        return self._client
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text response using Cerebras."""
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
                f"Cerebras failed: {e}",
                model=self._config.model_name,
                provider="cerebras"
            )


class GroqClient(BaseLLMClient):
    """Groq API client - Fallback model when Cerebras is overloaded."""
    
    def __init__(self, config: LLMModelConfig, api_key: str):
        super().__init__(config, api_key, "groq")
    
    @property
    def client(self):
        """Lazy load the Groq client."""
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=self._api_key)
        return self._client
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text response using Groq."""
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
                f"Groq failed: {e}",
                model=self._config.model_name,
                provider="groq"
            )


class OpenAIClient(BaseLLMClient):
    """OpenAI API client implementation (Legacy support)."""
    
    def __init__(self, config: LLMModelConfig, api_key: str):
        super().__init__(config, api_key, "openai")
    
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
                f"OpenAI failed: {e}",
                model=self._config.model_name,
                provider="openai"
            )


class LLMService(BaseService):
    """
    Service for LLM operations.
    
    Main Model: Cerebras (Llama 3.1-70B) - Super fast for demo
    Fallback Model: Groq (Llama 3-70B) - When Cerebras is overloaded
    
    Manages:
    - Text generation with automatic fallback
    - Structured output (JSON)
    - Prompt templates
    """
    
    def __init__(
        self,
        config: Optional[LLMModelConfig] = None,
        fallback_config: Optional[LLMModelConfig] = None
    ):
        super().__init__("LLMService")
        self._config = config or ModelConfig.DEFAULT_LLM
        self._fallback_config = fallback_config or ModelConfig.FALLBACK_LLM
        self._client: Optional[ILLMClient] = None
        self._fallback_client: Optional[ILLMClient] = None
    
    def _create_client(self, config: LLMModelConfig) -> ILLMClient:
        """Create an LLM client based on provider type."""
        from config.settings import get_settings
        settings = get_settings()
        
        if config.provider == LLMProviderType.CEREBRAS:
            return CerebrasClient(config, settings.cerebras_api_key)
        elif config.provider == LLMProviderType.GROQ:
            return GroqClient(config, settings.groq_api_key)
        elif config.provider == LLMProviderType.OPENAI:
            return OpenAIClient(config, settings.openai_api_key)
        else:
            raise LLMError(f"Unsupported LLM provider: {config.provider}")
    
    def initialize(self) -> None:
        """Initialize the LLM service with main and fallback clients."""
        self._client = self._create_client(self._config)
        self._fallback_client = self._create_client(self._fallback_config)
        
        logger.info(f"LLM Service initialized with main: {self._config.provider.value} ({self._config.model_name})")
        logger.info(f"Fallback: {self._fallback_config.provider.value} ({self._fallback_config.model_name})")
        
        super().initialize()
    
    @property
    def client(self) -> ILLMClient:
        """Get the LLM client."""
        self._ensure_initialized()
        return self._client
    
    def _generate_with_fallback(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate response with automatic fallback on failure."""
        try:
            # Try main client (Cerebras)
            return self._client.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt
            )
        except LLMError as e:
            logger.warning(f"Main LLM failed ({self._config.provider.value}): {e}. Trying fallback...")
            try:
                # Fallback to Groq
                return self._fallback_client.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt=system_prompt
                )
            except LLMError as fallback_error:
                logger.error(f"Fallback LLM also failed ({self._fallback_config.provider.value}): {fallback_error}")
                raise LLMError(
                    f"All LLM providers failed. Main: {e}, Fallback: {fallback_error}",
                    model=self._config.model_name,
                    provider="all"
                )
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text response with automatic fallback."""
        self._ensure_initialized()
        
        return self._generate_with_fallback(
            prompt=prompt,
            max_tokens=max_tokens or self._config.max_tokens,
            temperature=temperature or self._config.temperature,
            system_prompt=system_prompt
        )
    
    def _generate_json_with_fallback(
        self,
        prompt: str,
        schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate JSON response with automatic fallback."""
        try:
            return self._client.generate_json(prompt, schema)
        except LLMError as e:
            logger.warning(f"Main LLM JSON failed ({self._config.provider.value}): {e}. Trying fallback...")
            try:
                return self._fallback_client.generate_json(prompt, schema)
            except LLMError as fallback_error:
                logger.error(f"Fallback LLM JSON also failed: {fallback_error}")
                raise
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate structured JSON response with automatic fallback."""
        self._ensure_initialized()
        return self._generate_json_with_fallback(prompt, schema)
    
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
    """Generate response using Cerebras with Groq fallback (backward compatibility)."""
    from config.settings import get_settings
    from config.models import MAX_TOKENS_RESPONSE
    
    settings = get_settings()
    
    # Try Cerebras first (main model)
    try:
        from cerebras.cloud.sdk import Cerebras
        client = Cerebras(api_key=settings.cerebras_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=MAX_TOKENS_RESPONSE
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"Cerebras failed: {e}. Trying Groq fallback...")
    
    # Fallback to Groq
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=MAX_TOKENS_RESPONSE
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Lỗi khi gọi LLM API: {str(e)}"

# config/models.py
"""
Model configurations for LLM and Embedding models.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class EmbeddingModelType(str, Enum):
    """Supported embedding model types."""
    SENTENCE_TRANSFORMER = "sentence_transformer"
    OPENAI = "openai"


class LLMProviderType(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


@dataclass
class EmbeddingModelConfig:
    """Configuration for embedding models."""
    model_name: str
    model_type: EmbeddingModelType
    dimension: int
    max_sequence_length: int = 512
    
    # Additional options
    options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}


@dataclass
class LLMModelConfig:
    """Configuration for LLM models."""
    model_name: str
    provider: LLMProviderType
    max_tokens: int = 512
    temperature: float = 0.7
    
    # API configuration
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    
    # Additional options
    options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}


class ModelConfig:
    """
    Central configuration for all models.
    
    Provides default configurations and factory methods.
    """
    
    # Default embedding model
    DEFAULT_EMBEDDING = EmbeddingModelConfig(
        model_name="paraphrase-mpnet-base-v2",
        model_type=EmbeddingModelType.SENTENCE_TRANSFORMER,
        dimension=768,
        max_sequence_length=512
    )
    
    # Default LLM model
    DEFAULT_LLM = LLMModelConfig(
        model_name="gpt-4o-mini",
        provider=LLMProviderType.OPENAI,
        max_tokens=512,
        temperature=0.7
    )
    
    # Alternative models
    EMBEDDING_MODELS = {
        "paraphrase-mpnet-base-v2": EmbeddingModelConfig(
            model_name="paraphrase-mpnet-base-v2",
            model_type=EmbeddingModelType.SENTENCE_TRANSFORMER,
            dimension=768
        ),
        "all-MiniLM-L6-v2": EmbeddingModelConfig(
            model_name="all-MiniLM-L6-v2",
            model_type=EmbeddingModelType.SENTENCE_TRANSFORMER,
            dimension=384
        ),
        "text-embedding-3-small": EmbeddingModelConfig(
            model_name="text-embedding-3-small",
            model_type=EmbeddingModelType.OPENAI,
            dimension=1536
        ),
    }
    
    LLM_MODELS = {
        "gpt-4o-mini": LLMModelConfig(
            model_name="gpt-4o-mini",
            provider=LLMProviderType.OPENAI,
            max_tokens=512
        ),
        "gpt-4o": LLMModelConfig(
            model_name="gpt-4o",
            provider=LLMProviderType.OPENAI,
            max_tokens=1024
        ),
        "gpt-3.5-turbo": LLMModelConfig(
            model_name="gpt-3.5-turbo",
            provider=LLMProviderType.OPENAI,
            max_tokens=512
        ),
    }
    
    @classmethod
    def get_embedding_config(cls, model_name: Optional[str] = None) -> EmbeddingModelConfig:
        """Get embedding model configuration."""
        if model_name is None:
            return cls.DEFAULT_EMBEDDING
        return cls.EMBEDDING_MODELS.get(model_name, cls.DEFAULT_EMBEDDING)
    
    @classmethod
    def get_llm_config(cls, model_name: Optional[str] = None) -> LLMModelConfig:
        """Get LLM model configuration."""
        if model_name is None:
            return cls.DEFAULT_LLM
        return cls.LLM_MODELS.get(model_name, cls.DEFAULT_LLM)


# Backward compatibility exports
EMBEDDING_MODEL = ModelConfig.DEFAULT_EMBEDDING.model_name
LLM_MODEL = ModelConfig.DEFAULT_LLM.model_name
MAX_TOKENS_RESPONSE = ModelConfig.DEFAULT_LLM.max_tokens
MAX_TOKENS_SUMMARY = 200
DEFAULT_TOP_K = 5

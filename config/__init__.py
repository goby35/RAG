# config/__init__.py
"""
Configuration module for RAG Application.

Organized into separate config files for different concerns:
- settings.py: General application settings
- models.py: Model configurations (LLM, Embedding)
- access.py: Access control settings
- paths.py: File paths and directories
- entities.py: Entity types and claim topics
"""

# Settings exports
from .settings import (
    Settings, 
    get_settings, 
    init_api_keys, 
    get_openai_api_key,
    SEMANTIC_WEIGHT,
    CONFIDENCE_WEIGHT,
    FRESHNESS_WEIGHT
)

# Model exports
from .models import (
    ModelConfig,
    EmbeddingModelConfig,
    LLMModelConfig,
    EmbeddingModelType,
    LLMProviderType,
    EMBEDDING_MODEL,
    LLM_MODEL,
    MAX_TOKENS_RESPONSE,
    MAX_TOKENS_SUMMARY,
    DEFAULT_TOP_K
)

# Access control exports
from .access import (
    AccessConfig,
    REBAC_MATRIX,
    CONFIDENCE_SCORES,
    VERIFIED_STATUSES,
    MIN_CONFIDENCE_FOR_RAG
)

# Path exports
from .paths import PathConfig, CACHE_TTL, DATA_COLUMNS

# Entity exports
from .entities import (
    EntityConfig,
    ENTITY_TYPES,
    CLAIM_TOPICS,
    EVIDENCE_TYPES,
    ACCESS_LEVELS,
    STATUS_OPTIONS
)

__all__ = [
    # Settings
    'Settings',
    'get_settings',
    'init_api_keys',
    'get_openai_api_key',
    'SEMANTIC_WEIGHT',
    'CONFIDENCE_WEIGHT',
    'FRESHNESS_WEIGHT',
    
    # Models
    'ModelConfig',
    'EmbeddingModelConfig',
    'LLMModelConfig',
    'EmbeddingModelType',
    'LLMProviderType',
    'EMBEDDING_MODEL',
    'LLM_MODEL',
    'MAX_TOKENS_RESPONSE',
    'MAX_TOKENS_SUMMARY',
    'DEFAULT_TOP_K',
    
    # Access Control
    'AccessConfig',
    'REBAC_MATRIX',
    'CONFIDENCE_SCORES',
    'VERIFIED_STATUSES',
    'MIN_CONFIDENCE_FOR_RAG',
    
    # Paths
    'PathConfig',
    'CACHE_TTL',
    'DATA_COLUMNS',
    
    # Entities
    'EntityConfig',
    'ENTITY_TYPES',
    'CLAIM_TOPICS',
    'EVIDENCE_TYPES',
    'ACCESS_LEVELS',
    'STATUS_OPTIONS',
]

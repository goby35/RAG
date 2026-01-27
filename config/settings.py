# config/settings.py
"""
Main settings configuration using Pydantic for validation.
"""

import os
from typing import Optional
from functools import lru_cache
from dataclasses import dataclass, field

import streamlit as st


@dataclass
class Settings:
    """
    Main application settings.
    
    Centralized configuration with environment variable support.
    """
    
    # API Keys
    openai_api_key: str = field(default_factory=lambda: os.environ.get('OPENAI_API_KEY', ''))
    
    # Neo4j Configuration
    neo4j_uri: str = field(default_factory=lambda: os.environ.get('NEO4J_URI', 'bolt://localhost:7687'))
    neo4j_user: str = field(default_factory=lambda: os.environ.get('NEO4J_USER', 'neo4j'))
    neo4j_password: str = field(default_factory=lambda: os.environ.get('NEO4J_PASSWORD', 'neo4jpassword'))
    
    # Application Settings
    debug: bool = field(default_factory=lambda: os.environ.get('DEBUG', 'false').lower() == 'true')
    cache_ttl: int = 60  # seconds
    
    # RAG Settings
    default_top_k: int = 5
    max_tokens_summary: int = 200
    max_tokens_response: int = 512
    
    # Temporal Ranking
    semantic_weight: float = 0.40
    confidence_weight: float = 0.40
    freshness_weight: float = 0.20
    fresh_period_days: int = 180
    half_life_days: int = 365
    min_freshness_score: float = 0.1
    
    # Presence Management
    inactivity_threshold_seconds: int = 300  # 5 minutes
    
    def __post_init__(self):
        """Validate settings after initialization."""
        # Ensure weights sum to 1.0
        total_weight = self.semantic_weight + self.confidence_weight + self.freshness_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight}")
    
    @classmethod
    def from_streamlit_secrets(cls) -> 'Settings':
        """Create settings from Streamlit secrets."""
        settings = cls()
        
        try:
            if 'OPENAI_API_KEY' in st.secrets:
                settings.openai_api_key = st.secrets['OPENAI_API_KEY']
                os.environ['OPENAI_API_KEY'] = settings.openai_api_key
            
            if 'NEO4J_URI' in st.secrets:
                settings.neo4j_uri = st.secrets['NEO4J_URI']
            
            if 'NEO4J_USER' in st.secrets:
                settings.neo4j_user = st.secrets['NEO4J_USER']
            
            if 'NEO4J_PASSWORD' in st.secrets:
                settings.neo4j_password = st.secrets['NEO4J_PASSWORD']
        except Exception:
            # Streamlit secrets not available (e.g., in tests)
            pass
        
        return settings


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.from_streamlit_secrets()
    return _settings


def init_api_keys():
    """Initialize API keys from settings (backward compatibility)."""
    settings = get_settings()
    os.environ['OPENAI_API_KEY'] = settings.openai_api_key


def get_openai_api_key() -> str:
    """Get OpenAI API key (backward compatibility)."""
    return get_settings().openai_api_key


# Backward compatibility - scoring weights
SEMANTIC_WEIGHT = 0.40
CONFIDENCE_WEIGHT = 0.40
FRESHNESS_WEIGHT = 0.20
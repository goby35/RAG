# config.py - Configuration và Constants cho Graph-based RAG
"""
BACKWARD COMPATIBILITY FILE.

This file re-exports from the new config module for backward compatibility.
New code should import from the config package directly.

Example:
    # Old way (still works)
    from config import EMBEDDING_MODEL, init_api_keys
    
    # New way (recommended)
    from config.models import ModelConfig
    from config.settings import get_settings
"""

import os
import streamlit as st

# Import from new config module
from config.settings import get_settings, init_api_keys, get_openai_api_key
from config.access import (
    ACCESS_LEVELS, ACCESS_TAGS, REBAC_MATRIX, STATUS_OPTIONS,
    VERIFIED_STATUSES, CONFIDENCE_SCORES, MIN_CONFIDENCE_FOR_RAG, MIN_CONFIDENCE_TRUSTED
)
from config.models import (
    EMBEDDING_MODEL, LLM_MODEL, MAX_TOKENS_RESPONSE, MAX_TOKENS_SUMMARY, DEFAULT_TOP_K
)
from config.paths import (
    DATA_FILE, USERS_FILE, CLAIMS_FILE, ENTITIES_FILE, EVIDENCE_FILE, DATA_COLUMNS
)
from config.entities import (
    ENTITY_TYPES, CLAIM_TOPICS, CATEGORY_TO_TOPIC, EVIDENCE_TYPES, USER_ROLES
)

# ============================================================================
# NEO4J CONFIGURATION (kept here for backward compatibility)
# ============================================================================
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'neo4jpassword')

# ============================================================================
# TEMPORAL RANKING SETTINGS (kept here for backward compatibility)
# ============================================================================
SEMANTIC_WEIGHT = 0.40
CONFIDENCE_WEIGHT = 0.40
FRESHNESS_WEIGHT = 0.20
FRESH_PERIOD_DAYS = 180
HALF_LIFE_DAYS = 365
MIN_FRESHNESS_SCORE = 0.1

# ============================================================================
# CACHE SETTINGS
# ============================================================================
CACHE_TTL = 60  # seconds

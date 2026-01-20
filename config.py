# config.py - Configuration và Constants
import os
import streamlit as st

# ============================================================================
# API CONFIGURATION
# ============================================================================
def init_api_keys():
    """Initialize API keys từ Streamlit secrets."""
    os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']


def get_openai_api_key():
    """Get OpenAI API key."""
    return os.environ.get('OPENAI_API_KEY', '')


# ============================================================================
# APP CONSTANTS
# ============================================================================
# File paths
DATA_FILE = 'data_mock.csv'

# Data schema
DATA_COLUMNS = ['Source', 'Relation', 'Target', 'Evidence', 'Access_Level', 'Status']

# Access levels
ACCESS_LEVELS = ['public', 'private', 'connections_only', 'recruiter']

# Status options
STATUS_OPTIONS = ['self_declared', 'attested', 'pending']

# Verified statuses
VERIFIED_STATUSES = ['attested', 'self_declared']

# Model configurations
EMBEDDING_MODEL = 'paraphrase-mpnet-base-v2'
LLM_MODEL = 'gpt-4o-mini'

# RAG settings
DEFAULT_TOP_K = 3
MAX_TOKENS_SUMMARY = 150
MAX_TOKENS_RESPONSE = 512

# Cache settings
CACHE_TTL = 60  # seconds

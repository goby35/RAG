# utils/__init__.py
"""
Utility modules for RAG application.

NOTE: This module provides backward compatibility with existing code.
New code should use the services and repositories packages directly.

Migration guide:
    # Old way
    from utils import load_data, simple_rag
    
    # New way
    from repositories import ClaimRepository
    from services import RAGService
"""

# Backward compatibility imports
from .data_loader import load_data, get_unique_user_ids, save_data
from .document_processor import create_docs_and_metadata
from .embeddings import load_embedder, create_embeddings_and_index
from .gatekeeper import gatekeeper_filter
from .rag_engine import simple_rag
from .triple_extractor import extract_triples, preview_triples

# Re-export from new services for gradual migration
try:
    from services.embedding_service import EmbeddingService
    from services.llm_service import LLMService
    from services.rag_service import RAGService
    from services.access_control_service import AccessControlService
except ImportError:
    # Services module not available
    pass

__all__ = [
    # Legacy exports (backward compatibility)
    'load_data',
    'get_unique_user_ids', 
    'save_data',
    'create_docs_and_metadata',
    'load_embedder',
    'create_embeddings_and_index',
    'gatekeeper_filter',
    'simple_rag',
    'extract_triples',
    'preview_triples',
    # New service exports
    'EmbeddingService',
    'LLMService',
    'RAGService',
    'AccessControlService',
]


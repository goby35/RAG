# app_refactored.py - Refactored Main Entry Point
"""
Multi-user Interactive RAG Application (Refactored)
===================================================

Clean architecture implementation with:
- Dependency Injection
- Service Layer Pattern
- Repository Pattern
- Proper Error Handling

Entry point that bootstraps the application and starts Streamlit.
"""

import streamlit as st
import numpy as np
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_application():
    """Bootstrap and configure the application."""
    from config.settings import get_settings, init_api_keys
    from core.container import configure_container, get_container
    
    # Initialize API keys
    settings = get_settings()
    init_api_keys()
    
    # Configure dependency injection container
    container = configure_container(settings)
    
    return container, settings


def load_data_for_rag(container):
    """Load data from repositories for RAG."""
    from repositories.claim_repository import ClaimRepository
    from repositories.user_repository import UserRepository
    
    # Get repositories
    claim_repo = container.resolve(ClaimRepository)
    user_repo = container.resolve(UserRepository)
    
    # Get documents and metadata for RAG
    documents, metadata = claim_repo.get_documents_and_metadata()
    
    # Get user IDs
    user_ids = user_repo.get_user_ids()
    
    # Fallback to legacy data if no users in JSON
    if not user_ids:
        from utils.data_loader import load_data, get_unique_user_ids
        data_df = load_data()
        user_ids = get_unique_user_ids(data_df)
    
    return documents, metadata, user_ids


def create_embeddings(container, documents):
    """Create embeddings for documents."""
    from services.embedding_service import EmbeddingService
    
    embedding_service = container.resolve(EmbeddingService)
    embedding_service.initialize()
    
    if documents:
        embeddings = embedding_service.encode(documents)
        return embeddings, embedding_service.embedder
    
    return np.array([]), embedding_service.embedder


def render_app(container, documents, metadata, user_ids, embeddings, embedder):
    """Render the Streamlit application."""
    from utils.data_loader import load_data
    from ui.sidebar import render_sidebar
    from ui.main_content import render_main_content
    
    # Header
    st.title("🔍 Multi-user Interactive RAG Application")
    st.markdown("*Graph-based RAG với Confidence Scoring - Refactored*")
    st.markdown("---")
    
    # Render sidebar
    render_sidebar()
    
    # Load legacy data for compatibility
    data_df = load_data()
    
    # Render main content
    render_main_content(
        data_df=data_df,
        user_ids=user_ids,
        embedder=embedder,
        documents=documents,
        metadata=metadata,
        doc_embeddings=embeddings
    )


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="Multi-user RAG App",
        page_icon="🔍",
        layout="wide"
    )
    
    try:
        # Bootstrap application
        container, settings = setup_application()
        
        # Load data
        documents, metadata, user_ids = load_data_for_rag(container)
        
        # Create embeddings
        embeddings, embedder = create_embeddings(container, documents)
        
        # Render application
        render_app(container, documents, metadata, user_ids, embeddings, embedder)
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        st.error(f"An error occurred: {str(e)}")
        
        # Show debug info in development
        from config.settings import get_settings
        if get_settings().debug:
            st.exception(e)


if __name__ == "__main__":
    main()

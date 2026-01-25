# app.py - Main Entry Point (Multi-user Interactive RAG Application)
"""
Multi-user Interactive RAG Application
=====================================

Ứng dụng RAG cho phép nhiều người dùng truy vấn thông tin với hệ thống
phân quyền dựa trên Viewer ID và Target User ID.

Sử dụng Graph Schema mới với:
- data/claims.json: Claims với confidence scoring
- data/users.json: User profiles
- data/entities.json: Entity knowledge base
- data/evidence.json: Evidence links

Cấu trúc project:
- config.py: Configuration và constants
- utils/
    - data_loader.py: Data loading functions (CSV + JSON)
    - document_processor.py: Document processing với OpenAI
    - embeddings.py: Embedding và FAISS index
    - gatekeeper.py: Access control logic với confidence
    - rag_engine.py: RAG pipeline với confidence scoring
- ui/
    - sidebar.py: Sidebar components
    - main_content.py: Main content components
"""

import streamlit as st
import numpy as np

# Local imports
from config import init_api_keys
from utils.data_loader import (
    load_data, get_unique_user_ids, 
    get_documents_and_metadata, get_all_user_ids
)
from utils.embeddings import load_embedder, create_embeddings_and_index
from ui.sidebar import render_sidebar
from ui.main_content import render_main_content


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="Multi-user RAG App",
        page_icon="🔍",
        layout="wide"
    )
    
    # Initialize API keys
    init_api_keys()
    
    # Header
    st.title("🔍 Multi-user Interactive RAG Application")
    st.markdown("*Graph-based RAG với Confidence Scoring*")
    st.markdown("---")
    
    # Load data từ JSON schema mới (fallback to CSV nếu không có)
    documents, metadata = get_documents_and_metadata(use_json=True)
    
    # Get user IDs từ cả JSON và CSV
    user_ids = get_all_user_ids()
    
    # Fallback: nếu không có user nào từ JSON, dùng CSV
    if not user_ids:
        data_df = load_data()
        user_ids = get_unique_user_ids(data_df)
    
    # Load embedder
    embedder = load_embedder()
    
    # Create embeddings và index
    if documents:
        doc_embeddings, index = create_embeddings_and_index(embedder, documents)
    else:
        doc_embeddings, index = np.array([]), None
    
    # Render sidebar (Ingestion)
    render_sidebar()
    
    # Load legacy data for compatibility with sidebar
    data_df = load_data()
    
    # Render main content
    render_main_content(
        data_df=data_df,
        user_ids=user_ids,
        embedder=embedder,
        documents=documents,
        metadata=metadata,
        doc_embeddings=doc_embeddings
    )


if __name__ == "__main__":
    main()

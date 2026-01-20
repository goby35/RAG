# app.py - Main Entry Point (Multi-user Interactive RAG Application)
"""
Multi-user Interactive RAG Application
=====================================

Ứng dụng RAG cho phép nhiều người dùng truy vấn thông tin với hệ thống
phân quyền dựa trên Viewer ID và Target User ID.

Cấu trúc project:
- config.py: Configuration và constants
- utils/
    - data_loader.py: Data loading functions
    - document_processor.py: Document processing với OpenAI
    - embeddings.py: Embedding và FAISS index
    - gatekeeper.py: Access control logic
    - rag_engine.py: RAG pipeline
- ui/
    - sidebar.py: Sidebar components
    - main_content.py: Main content components
"""

import streamlit as st
import numpy as np

# Local imports
from config import init_api_keys
from utils.data_loader import load_data, get_unique_user_ids
from utils.document_processor import create_docs_and_metadata
from utils.embeddings import load_embedder, create_embeddings_and_index
from ui.sidebar import render_sidebar
from ui.main_content import render_main_content


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="Multi-user RAG App",
        page_icon="",
        layout="wide"
    )
    
    # Initialize API keys
    init_api_keys()
    
    # Header
    st.title("🔍 Multi-user Interactive RAG Application")
    st.markdown("---")
    
    # Load data
    data_df = load_data()
    user_ids = get_unique_user_ids(data_df)
    
    # Load embedder
    embedder = load_embedder()
    
    # Create documents và metadata
    documents, metadata = create_docs_and_metadata(data_df)
    
    # Create embeddings và index
    if documents:
        doc_embeddings, index = create_embeddings_and_index(embedder, documents)
    else:
        doc_embeddings, index = np.array([]), None
    
    # Render sidebar (Ingestion)
    render_sidebar()
    
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

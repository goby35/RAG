# utils/embeddings.py - Embedding & Index Functions
import numpy as np
import faiss
import streamlit as st
from sentence_transformers import SentenceTransformer

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMBEDDING_MODEL


@st.cache_resource
def load_embedder() -> SentenceTransformer:
    """
    Load SentenceTransformer model.
    Cached để tránh load lại mỗi lần rerun.
    
    Returns:
        SentenceTransformer model
    """
    return SentenceTransformer(EMBEDDING_MODEL)


def create_embeddings(embedder: SentenceTransformer, docs: list) -> np.ndarray:
    """
    Tạo embeddings từ list documents.
    
    Args:
        embedder: SentenceTransformer model
        docs: List các documents
        
    Returns:
        Numpy array chứa embeddings
    """
    if not docs:
        return np.array([])
    return embedder.encode(docs)


def create_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatL2:
    """
    Tạo FAISS index từ embeddings.
    
    Args:
        embeddings: Numpy array chứa embeddings
        
    Returns:
        FAISS IndexFlatL2
    """
    if len(embeddings) == 0:
        return None
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype('float32'))
    return index


def create_embeddings_and_index(embedder: SentenceTransformer, docs: list) -> tuple:
    """
    Tạo embeddings và FAISS index từ documents.
    
    Args:
        embedder: SentenceTransformer model
        docs: List các documents
        
    Returns:
        Tuple (doc_embeddings, faiss_index)
    """
    if not docs:
        return np.array([]), None
    
    doc_embeddings = create_embeddings(embedder, docs)
    index = create_faiss_index(doc_embeddings)
    
    return doc_embeddings, index


def search_similar(embedder: SentenceTransformer, 
                   query: str, 
                   doc_embeddings: np.ndarray,
                   allowed_indices: list,
                   top_k: int = 3) -> tuple:
    """
    Tìm kiếm documents tương tự với query.
    
    Args:
        embedder: SentenceTransformer model
        query: Câu query
        doc_embeddings: Embeddings của tất cả documents
        allowed_indices: List các indices được phép truy cập
        top_k: Số lượng kết quả trả về
        
    Returns:
        Tuple (distances, indices) trong không gian allowed_indices
    """
    # Embed query
    query_emb = embedder.encode([query])[0]
    
    # Tạo sub-index từ allowed documents
    allowed_embs = np.array([doc_embeddings[i] for i in allowed_indices]).astype('float32')
    allowed_index = faiss.IndexFlatL2(allowed_embs.shape[1])
    allowed_index.add(allowed_embs)
    
    # Search
    k = min(top_k, len(allowed_indices))
    distances, indices = allowed_index.search(
        np.array([query_emb]).astype('float32'), 
        k=k
    )
    
    return distances, indices

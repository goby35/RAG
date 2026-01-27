# utils/document_processor.py - Document Processing Functions
import pandas as pd
import streamlit as st
from openai import OpenAI

import sys
import os

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Try importing from new config module, fallback to old
try:
    from config.settings import get_openai_api_key
    from config.models import LLM_MODEL, MAX_TOKENS_SUMMARY
    from config.paths import CACHE_TTL
    from config.access import VERIFIED_STATUSES
except ImportError:
    from config import (
        get_openai_api_key, 
        LLM_MODEL, 
        MAX_TOKENS_SUMMARY, 
        CACHE_TTL,
        VERIFIED_STATUSES
    )


def generate_document_summary(client: OpenAI, row: pd.Series) -> str:
    """
    Tạo summary cho một dòng dữ liệu sử dụng OpenAI.
    
    Args:
        client: OpenAI client
        row: Dòng dữ liệu từ DataFrame
        
    Returns:
        Summary string
    """
    prompt = f"""
    Dựa trên dữ liệu sau, hãy tạo một câu tóm tắt mượt mà, tự nhiên (bằng tiếng Việt hoặc Anh tùy theo nội dung):
    - Source: {row['Source']}
    - Relation: {row['Relation']}
    - Target: {row['Target']}
    - Evidence: {row['Evidence']}
    Ví dụ output: "{row['Source']} {row['Relation']} {row['Target']}: {row['Evidence']} (với giải thích ngắn gọn)."
    """
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=MAX_TOKENS_SUMMARY
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback nếu API lỗi
        return f"{row['Source']} {row['Relation']} {row['Target']}: {row['Evidence']}"


def create_metadata_entry(idx: int, row: pd.Series) -> dict:
    """
    Tạo metadata entry cho một dòng dữ liệu.
    
    Args:
        idx: Index của dòng
        row: Dòng dữ liệu từ DataFrame
        
    Returns:
        Dictionary chứa metadata
    """
    return {
        "source": row['Source'],
        "access_level": row['Access_Level'],
        "verified": row['Status'] in VERIFIED_STATUSES,
        "original_index": idx
    }


@st.cache_data(ttl=CACHE_TTL)
def create_docs_and_metadata(df: pd.DataFrame) -> tuple:
    """
    Tạo documents và metadata từ DataFrame.
    Sử dụng OpenAI để generate summary cho mỗi document.
    
    Args:
        df: DataFrame chứa dữ liệu
        
    Returns:
        Tuple (documents, metadata)
    """
    if df.empty:
        return [], []
    
    client = OpenAI(api_key=get_openai_api_key())
    documents = []
    metadata = []
    
    for idx, row in df.iterrows():
        # Generate summary
        summary = generate_document_summary(client, row)
        documents.append(summary)
        
        # Create metadata
        meta = create_metadata_entry(idx, row)
        metadata.append(meta)
    
    return documents, metadata

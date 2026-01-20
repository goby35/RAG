# utils/rag_engine.py - RAG Engine
import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_openai_api_key, LLM_MODEL, MAX_TOKENS_RESPONSE, DEFAULT_TOP_K
from utils.gatekeeper import gatekeeper_filter
from utils.embeddings import search_similar


def build_rag_prompt(target_user_id: str, context_str: str, query: str) -> str:
    """
    Xây dựng prompt cho RAG.
    
    Args:
        target_user_id: ID người được hỏi về
        context_str: Context từ retrieved documents
        query: Câu hỏi của user
        
    Returns:
        Prompt string
    """
    return f"""Bạn là trợ lý AI giúp trả lời câu hỏi dựa trên thông tin được cung cấp.

Thông tin về '{target_user_id}':
{context_str}

Câu hỏi: {query}

Hãy trả lời dựa trên thông tin trên. Nếu không có đủ thông tin, hãy nói rõ."""


def generate_response(prompt: str) -> str:
    """
    Generate response từ OpenAI.
    
    Args:
        prompt: Prompt đã được build
        
    Returns:
        Response string
    """
    client = OpenAI(api_key=get_openai_api_key())
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=MAX_TOKENS_RESPONSE
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Lỗi khi gọi OpenAI API: {str(e)}"


def simple_rag(
    query: str,
    embedder: SentenceTransformer,
    doc_embeddings: np.ndarray,
    documents: list,
    metadata: list,
    target_user_id: str,
    viewer_id: str,
    viewer_role: str = "Default",
    top_k: int = DEFAULT_TOP_K
) -> str:
    """
    RAG function với Multi-user logic.
    
    Quy trình:
    1. Filter documents dựa trên gatekeeper logic
    2. Tìm kiếm documents tương tự với query
    3. Build context từ retrieved documents
    4. Generate response với OpenAI
    
    Args:
        query: Câu hỏi của người dùng
        embedder: SentenceTransformer model
        doc_embeddings: Embeddings của tất cả documents
        documents: List tất cả documents
        metadata: List metadata
        target_user_id: ID người bị soi
        viewer_id: ID người đang xem
        viewer_role: Role đặc biệt
        top_k: Số lượng documents retrieve
    
    Returns:
        Câu trả lời từ OpenAI
    """
    # Validate input
    if len(documents) == 0:
        return "Không có dữ liệu trong hệ thống."
    
    # Step 1: Filter indices dựa trên gatekeeper logic
    allowed_indices = gatekeeper_filter(metadata, target_user_id, viewer_id, viewer_role)
    
    if not allowed_indices:
        return f"Không có dữ liệu nào của '{target_user_id}' mà bạn được phép truy cập với quyền hiện tại."
    
    # Step 2: Search similar documents
    distances, indices = search_similar(
        embedder=embedder,
        query=query,
        doc_embeddings=doc_embeddings,
        allowed_indices=allowed_indices,
        top_k=top_k
    )
    
    # Step 3: Build context
    contexts = [documents[allowed_indices[i]] for i in indices[0] if i != -1]
    context_str = "\n".join(contexts)
    
    # Step 4: Generate response
    prompt = build_rag_prompt(target_user_id, context_str, query)
    return generate_response(prompt)

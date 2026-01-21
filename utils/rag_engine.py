# utils/rag_engine.py - RAG Engine with Confidence Scoring
"""
RAG Engine với tích hợp Confidence Score.

Logic:
1. Gatekeeper filter: Lọc claims dựa trên access control
2. Confidence ranking: Ưu tiên claims có confidence cao
3. Context building: Đưa confidence vào context để AI biết độ tin cậy
4. Response generation: AI có thể caveat thông tin chưa verified
"""

import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer

import sys
import os

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import (
    get_openai_api_key, LLM_MODEL, MAX_TOKENS_RESPONSE, DEFAULT_TOP_K,
    CONFIDENCE_SCORES, MIN_CONFIDENCE_TRUSTED
)
from utils.gatekeeper import gatekeeper_filter, gatekeeper_filter_with_ranking, get_confidence_summary
from utils.embeddings import search_similar


def build_rag_prompt_with_confidence(
    target_user_id: str, 
    context_items: list, 
    query: str
) -> str:
    """
    Xây dựng prompt cho RAG với thông tin về confidence.
    
    Args:
        target_user_id: ID người được hỏi về
        context_items: List các tuples (content, confidence, status)
        query: Câu hỏi của user
        
    Returns:
        Prompt string
    """
    # Build context với confidence markers
    context_lines = []
    for content, confidence, status in context_items:
        if confidence >= 0.9:
            marker = "✅ [VERIFIED - EAS Attested]"
        elif confidence >= 0.5:
            marker = "📎 [Has Evidence]"
        else:
            marker = "📝 [Self-Declared]"
        
        context_lines.append(f"{marker} (Confidence: {confidence:.0%})")
        context_lines.append(f"  {content}")
        context_lines.append("")
    
    context_str = "\n".join(context_lines)
    
    return f"""Bạn là trợ lý AI giúp trả lời câu hỏi dựa trên thông tin được cung cấp.
Chú ý về độ tin cậy của thông tin:
- ✅ [VERIFIED] = Thông tin đã được xác thực trên blockchain (EAS)
- 📎 [Has Evidence] = Có bằng chứng đi kèm (Github, Link, etc.)
- 📝 [Self-Declared] = Tự khai báo, chưa xác thực

Thông tin về '{target_user_id}':
{context_str}

Câu hỏi: {query}

Hướng dẫn trả lời:
1. Trả lời dựa trên thông tin trên
2. Nếu thông tin chỉ là Self-Declared, hãy nói rõ "Theo khai báo của người dùng..." 
3. Nếu thông tin đã Verified, có thể nói "Đã được xác thực rằng..."
4. Nếu không có đủ thông tin, hãy nói rõ"""


def build_rag_prompt(target_user_id: str, context_str: str, query: str) -> str:
    """
    LEGACY: Xây dựng prompt cho RAG (backward compatibility).
    
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
    top_k: int = DEFAULT_TOP_K,
    use_confidence: bool = True
) -> str:
    """
    RAG function với Multi-user logic và Confidence Scoring.
    
    Quy trình:
    1. Filter documents dựa trên gatekeeper logic
    2. Tìm kiếm documents tương tự với query
    3. Build context với confidence information
    4. Generate response với OpenAI (AI biết độ tin cậy)
    
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
        use_confidence: Có dùng confidence scoring không
    
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
    if use_confidence:
        # Build context với confidence info
        context_items = []
        for i in indices[0]:
            if i != -1:
                actual_idx = allowed_indices[i]
                content = documents[actual_idx]
                confidence = metadata[actual_idx].get("confidence_score", CONFIDENCE_SCORES['base_self_declared'])
                status = metadata[actual_idx].get("status", "self_declared")
                context_items.append((content, confidence, status))
        
        # Generate với confidence-aware prompt
        prompt = build_rag_prompt_with_confidence(target_user_id, context_items, query)
    else:
        # Legacy: simple context
        contexts = [documents[allowed_indices[i]] for i in indices[0] if i != -1]
        context_str = "\n".join(contexts)
        prompt = build_rag_prompt(target_user_id, context_str, query)
    
    # Step 4: Generate response
    return generate_response(prompt)


def rag_with_confidence_summary(
    query: str,
    embedder: SentenceTransformer,
    doc_embeddings: np.ndarray,
    documents: list,
    metadata: list,
    target_user_id: str,
    viewer_id: str,
    viewer_role: str = "Default",
    top_k: int = DEFAULT_TOP_K
) -> tuple:
    """
    RAG với trả về thêm confidence summary.
    
    Returns:
        Tuple: (response, confidence_summary_dict)
    """
    # Get allowed indices
    allowed_indices = gatekeeper_filter(metadata, target_user_id, viewer_id, viewer_role)
    
    if not allowed_indices:
        return (
            f"Không có dữ liệu nào của '{target_user_id}' mà bạn được phép truy cập.",
            {"total": 0, "high_confidence": 0, "medium_confidence": 0, "low_confidence": 0, "avg_confidence": 0.0}
        )
    
    # Get confidence summary
    summary = get_confidence_summary(metadata, allowed_indices)
    
    # Run RAG
    response = simple_rag(
        query=query,
        embedder=embedder,
        doc_embeddings=doc_embeddings,
        documents=documents,
        metadata=metadata,
        target_user_id=target_user_id,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        top_k=top_k,
        use_confidence=True
    )
    
    return response, summary

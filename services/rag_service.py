# services/rag_service.py
"""
RAG Service - Core RAG pipeline with confidence scoring.
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
import logging

from core.base import BaseService
from core.exceptions import DataNotFoundError, AccessDeniedError
from config.access import AccessConfig
from config.models import ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context item for RAG."""
    content: str
    confidence: float
    status: str
    claim_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def confidence_marker(self) -> str:
        """Get confidence marker for display."""
        if self.confidence >= 0.9:
            return "✅ [VERIFIED - EAS Attested]"
        elif self.confidence >= 0.5:
            return "📎 [Has Evidence]"
        else:
            return "📝 [Self-Declared]"


@dataclass
class RAGResult:
    """Result from RAG query."""
    answer: str
    contexts: List[RAGContext]
    query: str
    target_user_id: str
    viewer_id: str
    confidence_avg: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "contexts": [
                {
                    "content": c.content,
                    "confidence": c.confidence,
                    "status": c.status,
                    "marker": c.confidence_marker
                }
                for c in self.contexts
            ],
            "query": self.query,
            "target_user_id": self.target_user_id,
            "viewer_id": self.viewer_id,
            "confidence_avg": self.confidence_avg
        }


class RAGService(BaseService):
    """
    RAG (Retrieval-Augmented Generation) Service.
    
    Pipeline:
    1. Filter documents by access control (Gatekeeper)
    2. Embed and search for relevant documents
    3. Rank by confidence scores
    4. Build context-aware prompt
    5. Generate response with LLM
    """
    
    def __init__(
        self,
        embedding_service=None,
        llm_service=None,
        access_control_service=None
    ):
        super().__init__("RAGService")
        self._embedding_service = embedding_service
        self._llm_service = llm_service
        self._access_control_service = access_control_service
    
    def set_services(
        self,
        embedding_service=None,
        llm_service=None,
        access_control_service=None
    ) -> None:
        """Set dependent services."""
        if embedding_service:
            self._embedding_service = embedding_service
        if llm_service:
            self._llm_service = llm_service
        if access_control_service:
            self._access_control_service = access_control_service
    
    def query(
        self,
        query: str,
        documents: List[str],
        metadata: List[Dict[str, Any]],
        target_user_id: str,
        viewer_id: str,
        viewer_role: str = "Default",
        top_k: int = 5,
        use_confidence: bool = True
    ) -> RAGResult:
        """
        Execute RAG query pipeline.
        
        Args:
            query: User's question
            documents: List of document texts
            metadata: List of document metadata
            target_user_id: ID of user being queried about
            viewer_id: ID of viewer making query
            viewer_role: Role of viewer
            top_k: Number of documents to retrieve
            use_confidence: Whether to use confidence scoring
            
        Returns:
            RAGResult with answer and context
        """
        self._ensure_initialized()
        
        if not documents:
            return RAGResult(
                answer="Không có dữ liệu trong hệ thống.",
                contexts=[],
                query=query,
                target_user_id=target_user_id,
                viewer_id=viewer_id,
                confidence_avg=0.0
            )
        
        # Step 1: Filter by access control
        allowed_indices = self._filter_by_access(
            metadata, target_user_id, viewer_id, viewer_role
        )
        
        if not allowed_indices:
            return RAGResult(
                answer=f"Không có dữ liệu nào của '{target_user_id}' mà bạn được phép truy cập.",
                contexts=[],
                query=query,
                target_user_id=target_user_id,
                viewer_id=viewer_id,
                confidence_avg=0.0
            )
        
        # Step 2: Build embeddings if needed
        if self._embedding_service and hasattr(self._embedding_service, 'index'):
            doc_embeddings = self._embedding_service.encode(documents)
        else:
            # Fallback to inline embedding
            from services.embedding_service import load_embedder
            embedder = load_embedder()
            doc_embeddings = embedder.encode(documents)
        
        # Step 3: Search similar documents
        contexts = self._search_and_build_context(
            query, documents, metadata, doc_embeddings, allowed_indices, top_k
        )
        
        if not contexts:
            return RAGResult(
                answer=f"Không tìm thấy thông tin phù hợp với câu hỏi của bạn.",
                contexts=[],
                query=query,
                target_user_id=target_user_id,
                viewer_id=viewer_id,
                confidence_avg=0.0
            )
        
        # Step 4: Build prompt and generate
        if use_confidence:
            prompt = self._build_confidence_prompt(target_user_id, contexts, query)
        else:
            prompt = self._build_simple_prompt(target_user_id, contexts, query)
        
        # Step 5: Generate response
        if self._llm_service:
            answer = self._llm_service.generate(prompt)
        else:
            from services.llm_service import generate_response
            answer = generate_response(prompt)
        
        confidence_avg = np.mean([c.confidence for c in contexts]) if contexts else 0.0
        
        return RAGResult(
            answer=answer,
            contexts=contexts,
            query=query,
            target_user_id=target_user_id,
            viewer_id=viewer_id,
            confidence_avg=float(confidence_avg)
        )
    
    def _filter_by_access(
        self,
        metadata: List[Dict[str, Any]],
        target_user_id: str,
        viewer_id: str,
        viewer_role: str
    ) -> List[int]:
        """Filter document indices by access control."""
        min_confidence = AccessConfig.CONFIDENCE.min_for_rag
        allowed_indices = []
        
        for i, m in enumerate(metadata):
            # Scope: Only target user's documents
            source = m.get("user_id") or m.get("source")
            if source != target_user_id:
                continue
            
            # Access control
            access_level = m.get("access_level", "public")
            status = m.get("status", "self_declared")
            is_verified = m.get("verified", status in AccessConfig.VERIFIED_STATUSES)
            confidence = m.get("confidence_score", AccessConfig.CONFIDENCE.base_self_declared)
            
            # Confidence filter
            if confidence < min_confidence:
                continue
            
            # Owner can see everything
            if viewer_id == target_user_id:
                allowed_indices.append(i)
                continue
            
            # Recruiter access
            if viewer_role == "Recruiter":
                if access_level == "public":
                    allowed_indices.append(i)
                elif access_level in ["connections_only", "recruiter"] and is_verified:
                    allowed_indices.append(i)
                continue
            
            # Public access
            if access_level == "public":
                allowed_indices.append(i)
        
        return allowed_indices
    
    def _search_and_build_context(
        self,
        query: str,
        documents: List[str],
        metadata: List[Dict[str, Any]],
        doc_embeddings: np.ndarray,
        allowed_indices: List[int],
        top_k: int
    ) -> List[RAGContext]:
        """Search for similar documents and build context."""
        import faiss
        from services.embedding_service import load_embedder
        
        embedder = load_embedder()
        
        # Create sub-index from allowed documents
        allowed_embs = np.array([doc_embeddings[i] for i in allowed_indices]).astype('float32')
        allowed_index = faiss.IndexFlatL2(allowed_embs.shape[1])
        allowed_index.add(allowed_embs)
        
        # Embed query and search
        query_emb = embedder.encode([query])[0]
        k = min(top_k, len(allowed_indices))
        distances, indices = allowed_index.search(
            np.array([query_emb]).astype('float32'),
            k=k
        )
        
        # Build context objects
        contexts = []
        for idx in indices[0]:
            if idx != -1:
                actual_idx = allowed_indices[idx]
                content = documents[actual_idx]
                confidence = metadata[actual_idx].get(
                    "confidence_score",
                    AccessConfig.CONFIDENCE.base_self_declared
                )
                status = metadata[actual_idx].get("status", "self_declared")
                
                contexts.append(RAGContext(
                    content=content,
                    confidence=confidence,
                    status=status,
                    metadata=metadata[actual_idx]
                ))
        
        return contexts
    
    def _build_confidence_prompt(
        self,
        target_user_id: str,
        contexts: List[RAGContext],
        query: str
    ) -> str:
        """Build prompt with confidence information."""
        context_lines = []
        for ctx in contexts:
            context_lines.append(f"{ctx.confidence_marker} (Confidence: {ctx.confidence:.0%})")
            context_lines.append(f"  {ctx.content}")
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
    
    def _build_simple_prompt(
        self,
        target_user_id: str,
        contexts: List[RAGContext],
        query: str
    ) -> str:
        """Build simple prompt without confidence info."""
        context_str = "\n".join([ctx.content for ctx in contexts])
        
        return f"""Bạn là trợ lý AI giúp trả lời câu hỏi dựa trên thông tin được cung cấp.

Thông tin về '{target_user_id}':
{context_str}

Câu hỏi: {query}

Hãy trả lời dựa trên thông tin trên. Nếu không có đủ thông tin, hãy nói rõ."""

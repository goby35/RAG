# services/embedding_service.py
"""
Embedding Service - Handles text embedding and vector operations.
"""

from typing import List, Optional, Tuple
import numpy as np
import faiss
import logging

from core.base import BaseService
from core.interfaces import IEmbedder, IVectorIndex
from core.exceptions import EmbeddingError
from config.models import ModelConfig, EmbeddingModelConfig

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedder(IEmbedder):
    """Sentence Transformer based embedder."""
    
    def __init__(self, config: EmbeddingModelConfig):
        self._config = config
        self._model = None
    
    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._config.model_name)
        return self._model
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts into embeddings."""
        if not texts:
            return np.array([])
        try:
            return self.model.encode(texts)
        except Exception as e:
            raise EmbeddingError(f"Failed to encode texts: {e}", model=self._config.model_name)
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self._config.dimension
    
    @property
    def model_name(self) -> str:
        """Get model name."""
        return self._config.model_name


class FAISSVectorIndex(IVectorIndex):
    """FAISS-based vector index."""
    
    def __init__(self, dimension: int):
        self._dimension = dimension
        self._index: Optional[faiss.IndexFlatL2] = None
        self._id_map: List[str] = []
    
    def add(self, embeddings: np.ndarray, ids: Optional[List[str]] = None) -> None:
        """Add embeddings to index."""
        if len(embeddings) == 0:
            return
        
        embeddings = np.array(embeddings).astype('float32')
        
        if self._index is None:
            self._index = faiss.IndexFlatL2(self._dimension)
        
        self._index.add(embeddings)
        
        if ids:
            self._id_map.extend(ids)
        else:
            # Generate IDs based on current size
            start_idx = len(self._id_map)
            self._id_map.extend([str(i) for i in range(start_idx, start_idx + len(embeddings))])
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_ids: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, List[str]]:
        """Search for similar vectors."""
        if self._index is None or self._index.ntotal == 0:
            return np.array([]), []
        
        query_embedding = np.array(query_embedding).astype('float32')
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        if filter_ids is not None:
            # Create filtered sub-index
            filter_indices = [i for i, id_ in enumerate(self._id_map) if id_ in filter_ids]
            if not filter_indices:
                return np.array([]), []
            
            # Get embeddings for filtered indices
            # Note: FAISS doesn't support direct index access, so we'd need to store embeddings
            # For now, search all and filter results
            actual_k = min(k * 3, self._index.ntotal)
            distances, indices = self._index.search(query_embedding, actual_k)
            
            # Filter results
            filtered_distances = []
            filtered_ids = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx >= 0 and idx < len(self._id_map):
                    id_ = self._id_map[idx]
                    if id_ in filter_ids:
                        filtered_distances.append(dist)
                        filtered_ids.append(id_)
                        if len(filtered_ids) >= k:
                            break
            
            return np.array(filtered_distances), filtered_ids
        else:
            k = min(k, self._index.ntotal)
            distances, indices = self._index.search(query_embedding, k)
            
            result_ids = []
            for idx in indices[0]:
                if idx >= 0 and idx < len(self._id_map):
                    result_ids.append(self._id_map[idx])
            
            return distances[0], result_ids
    
    def size(self) -> int:
        """Get number of vectors in index."""
        return self._index.ntotal if self._index else 0


class EmbeddingService(BaseService):
    """
    Service for embedding operations.
    
    Manages:
    - Text embedding
    - Vector indexing
    - Similarity search
    """
    
    def __init__(self, config: Optional[EmbeddingModelConfig] = None):
        super().__init__("EmbeddingService")
        self._config = config or ModelConfig.DEFAULT_EMBEDDING
        self._embedder: Optional[IEmbedder] = None
        self._index: Optional[IVectorIndex] = None
    
    def initialize(self) -> None:
        """Initialize the embedding service."""
        self._embedder = SentenceTransformerEmbedder(self._config)
        self._index = FAISSVectorIndex(self._config.dimension)
        super().initialize()
    
    @property
    def embedder(self) -> IEmbedder:
        """Get the embedder instance."""
        self._ensure_initialized()
        return self._embedder
    
    @property
    def index(self) -> IVectorIndex:
        """Get the vector index."""
        self._ensure_initialized()
        return self._index
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to embeddings."""
        self._ensure_initialized()
        return self._embedder.encode(texts)
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text."""
        result = self.encode([text])
        return result[0] if len(result) > 0 else np.array([])
    
    def build_index(self, texts: List[str], ids: Optional[List[str]] = None) -> None:
        """Build vector index from texts."""
        self._ensure_initialized()
        
        if not texts:
            return
        
        embeddings = self._embedder.encode(texts)
        self._index = FAISSVectorIndex(self._config.dimension)
        self._index.add(embeddings, ids)
        
        self.logger.info(f"Built index with {len(texts)} documents")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_ids: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, List[str]]:
        """Search for similar documents."""
        self._ensure_initialized()
        
        query_embedding = self.encode_single(query)
        return self._index.search(query_embedding, k=top_k, filter_ids=filter_ids)
    
    def create_embeddings_and_index(
        self,
        documents: List[str],
        ids: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, IVectorIndex]:
        """Create embeddings and index (backward compatibility)."""
        self._ensure_initialized()
        
        if not documents:
            return np.array([]), self._index
        
        embeddings = self._embedder.encode(documents)
        self._index = FAISSVectorIndex(self._config.dimension)
        self._index.add(embeddings, ids)
        
        return embeddings, self._index


# Backward compatibility function
def load_embedder():
    """Load embedder (backward compatibility)."""
    import streamlit as st
    from sentence_transformers import SentenceTransformer
    
    @st.cache_resource
    def _load():
        return SentenceTransformer(ModelConfig.DEFAULT_EMBEDDING.model_name)
    
    return _load()

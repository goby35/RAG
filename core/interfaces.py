# core/interfaces.py
"""Abstract interfaces for the RAG application - Dependency Inversion Principle."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic
import numpy as np


# Generic type for repository entities
T = TypeVar('T')


class IEmbedder(ABC):
    """Interface for text embedding providers."""
    
    @abstractmethod
    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode texts into embeddings.
        
        Args:
            texts: List of texts to encode
            
        Returns:
            Numpy array of embeddings
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this encoder."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the name of the embedding model."""
        pass


class ILLMClient(ABC):
    """Interface for LLM providers."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text response from prompt.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response.
        
        Args:
            prompt: User prompt
            schema: Expected JSON schema
            
        Returns:
            Parsed JSON response
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the name of the LLM model."""
        pass


class IRepository(ABC, Generic[T]):
    """Generic repository interface for data access."""
    
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all entities."""
        pass
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by ID."""
        pass
    
    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        pass


class IAccessControl(ABC):
    """Interface for access control implementations."""
    
    @abstractmethod
    def can_access(
        self,
        viewer_id: str,
        target_id: str,
        resource_tags: List[str]
    ) -> bool:
        """
        Check if viewer can access resource with given tags.
        
        Args:
            viewer_id: ID of the viewer
            target_id: ID of the target user
            resource_tags: Access tags on the resource
            
        Returns:
            True if access is allowed
        """
        pass
    
    @abstractmethod
    def get_allowed_tags(self, viewer_id: str, target_id: str) -> List[str]:
        """
        Get list of access tags viewer is allowed to see.
        
        Args:
            viewer_id: ID of the viewer
            target_id: ID of the target user
            
        Returns:
            List of allowed access tags
        """
        pass
    
    @abstractmethod
    def get_relationships(self, viewer_id: str, target_id: str) -> List[str]:
        """
        Get relationships between viewer and target.
        
        Args:
            viewer_id: ID of the viewer
            target_id: ID of the target user
            
        Returns:
            List of relationship types
        """
        pass


class IPresenceManager(ABC):
    """Interface for presence management."""
    
    @abstractmethod
    def get_status(self, user_id: str) -> Optional[str]:
        """Get user's current presence status."""
        pass
    
    @abstractmethod
    def set_status(self, user_id: str, status: str) -> bool:
        """Set user's presence status."""
        pass
    
    @abstractmethod
    def get_online_users(self) -> List[str]:
        """Get list of online user IDs."""
        pass
    
    @abstractmethod
    def is_available_for_chat(self, user_id: str) -> bool:
        """Check if user is available for direct chat."""
        pass


class IMessageRouter(ABC):
    """Interface for message routing."""
    
    @abstractmethod
    def route(
        self,
        sender_id: str,
        receiver_id: str,
        content: str,
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Route a message to appropriate destination.
        
        Args:
            sender_id: Sender user ID
            receiver_id: Receiver user ID
            content: Message content
            message_type: Type of message
            
        Returns:
            Routing result with destination info
        """
        pass


class IVectorIndex(ABC):
    """Interface for vector similarity search."""
    
    @abstractmethod
    def add(self, embeddings: np.ndarray, ids: Optional[List[str]] = None) -> None:
        """Add embeddings to the index."""
        pass
    
    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_ids: Optional[List[str]] = None
    ) -> tuple:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query vector
            k: Number of results
            filter_ids: Optional list of IDs to filter by
            
        Returns:
            Tuple of (distances, indices/ids)
        """
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get number of vectors in index."""
        pass

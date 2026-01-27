# core/exceptions.py
"""Custom exceptions for the RAG application."""

from typing import Optional, Dict, Any


class RAGException(Exception):
    """Base exception for all RAG application errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "RAG_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class ConfigurationError(RAGException):
    """Raised when there's a configuration problem."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message,
            error_code="CONFIG_ERROR",
            details={"config_key": config_key} if config_key else {}
        )


class DataNotFoundError(RAGException):
    """Raised when requested data is not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} with ID '{resource_id}' not found",
            error_code="DATA_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class AccessDeniedError(RAGException):
    """Raised when access to a resource is denied."""
    
    def __init__(
        self,
        message: str = "Access denied",
        viewer_id: Optional[str] = None,
        target_id: Optional[str] = None,
        required_access: Optional[str] = None
    ):
        super().__init__(
            message,
            error_code="ACCESS_DENIED",
            details={
                "viewer_id": viewer_id,
                "target_id": target_id,
                "required_access": required_access
            }
        )


class ValidationError(RAGException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            details={"field": field, "value": str(value) if value else None}
        )


class EmbeddingError(RAGException):
    """Raised when embedding generation fails."""
    
    def __init__(self, message: str, model: Optional[str] = None):
        super().__init__(
            message,
            error_code="EMBEDDING_ERROR",
            details={"model": model}
        )


class LLMError(RAGException):
    """Raised when LLM API call fails."""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        provider: str = "openai"
    ):
        super().__init__(
            message,
            error_code="LLM_ERROR",
            details={"model": model, "provider": provider}
        )


class Neo4jConnectionError(RAGException):
    """Raised when Neo4j connection fails."""
    
    def __init__(self, message: str, uri: Optional[str] = None):
        super().__init__(
            message,
            error_code="NEO4J_CONNECTION_ERROR",
            details={"uri": uri}
        )


class MessageRoutingError(RAGException):
    """Raised when message routing fails."""
    
    def __init__(self, message: str, sender_id: str, receiver_id: str):
        super().__init__(
            message,
            error_code="MESSAGE_ROUTING_ERROR",
            details={"sender_id": sender_id, "receiver_id": receiver_id}
        )


class PresenceError(RAGException):
    """Raised when presence management fails."""
    
    def __init__(self, message: str, user_id: Optional[str] = None):
        super().__init__(
            message,
            error_code="PRESENCE_ERROR",
            details={"user_id": user_id}
        )

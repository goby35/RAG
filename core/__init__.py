# core/__init__.py
"""Core module - Base classes, interfaces, exceptions, and DI container."""

from .exceptions import (
    RAGException,
    ConfigurationError,
    DataNotFoundError,
    AccessDeniedError,
    ValidationError,
    EmbeddingError,
    LLMError,
    Neo4jConnectionError,
    MessageRoutingError,
    PresenceError,
)
from .interfaces import (
    IEmbedder,
    ILLMClient,
    IRepository,
    IAccessControl,
    IPresenceManager,
    IMessageRouter,
    IVectorIndex,
)
from .base import (
    BaseService,
    BaseRepository,
    Singleton,
    LazyProperty,
    validate_not_empty,
    validate_id,
)
from .container import (
    Container,
    get_container,
    configure_container,
    inject,
)

__all__ = [
    # Exceptions
    'RAGException',
    'ConfigurationError',
    'DataNotFoundError',
    'AccessDeniedError',
    'ValidationError',
    'EmbeddingError',
    'LLMError',
    'Neo4jConnectionError',
    'MessageRoutingError',
    'PresenceError',
    # Interfaces
    'IEmbedder',
    'ILLMClient',
    'IRepository',
    'IAccessControl',
    'IPresenceManager',
    'IMessageRouter',
    'IVectorIndex',
    # Base classes
    'BaseService',
    'BaseRepository',
    'Singleton',
    'LazyProperty',
    # Validators
    'validate_not_empty',
    'validate_id',
    # DI Container
    'Container',
    'get_container',
    'configure_container',
    'inject',
]

# core/base.py
"""Base classes for services and repositories."""

from abc import ABC
from typing import Optional, Any, TypeVar, Generic
import logging
from contextlib import contextmanager

T = TypeVar('T')


class BaseService(ABC):
    """
    Base class for all services.
    
    Provides common functionality:
    - Logging
    - Error handling patterns
    - Lifecycle management
    """
    
    def __init__(self, service_name: Optional[str] = None):
        self._service_name = service_name or self.__class__.__name__
        self._logger = logging.getLogger(self._service_name)
        self._is_initialized = False
    
    @property
    def logger(self) -> logging.Logger:
        return self._logger
    
    @property
    def service_name(self) -> str:
        return self._service_name
    
    @property
    def is_initialized(self) -> bool:
        return self._is_initialized
    
    def initialize(self) -> None:
        """Initialize the service. Override in subclasses."""
        self._is_initialized = True
        self._logger.info(f"{self._service_name} initialized")
    
    def shutdown(self) -> None:
        """Shutdown the service. Override in subclasses."""
        self._is_initialized = False
        self._logger.info(f"{self._service_name} shutdown")
    
    def _ensure_initialized(self) -> None:
        """Ensure service is initialized before use."""
        if not self._is_initialized:
            self.initialize()
    
    @contextmanager
    def _error_context(self, operation: str):
        """Context manager for consistent error logging."""
        try:
            yield
        except Exception as e:
            self._logger.error(f"{operation} failed: {e}")
            raise


class BaseRepository(ABC, Generic[T]):
    """
    Base class for all repositories.
    
    Provides common data access patterns and connection management.
    """
    
    def __init__(self, entity_name: str):
        self._entity_name = entity_name
        self._logger = logging.getLogger(f"{entity_name}Repository")
    
    @property
    def entity_name(self) -> str:
        return self._entity_name
    
    @property
    def logger(self) -> logging.Logger:
        return self._logger
    
    def _log_operation(self, operation: str, entity_id: Optional[str] = None) -> None:
        """Log repository operation."""
        if entity_id:
            self._logger.debug(f"{operation} {self._entity_name} [{entity_id}]")
        else:
            self._logger.debug(f"{operation} {self._entity_name}")


class Singleton(type):
    """
    Metaclass for implementing Singleton pattern.
    
    Usage:
        class MyClass(metaclass=Singleton):
            pass
    """
    _instances: dict = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
    
    @classmethod
    def clear_instance(mcs, cls) -> None:
        """Clear singleton instance (useful for testing)."""
        if cls in mcs._instances:
            del mcs._instances[cls]


class LazyProperty:
    """
    Decorator for lazy property initialization.
    
    Usage:
        @LazyProperty
        def expensive_computation(self):
            return compute_something()
    """
    
    def __init__(self, func):
        self.func = func
        self.attr_name = None
    
    def __set_name__(self, owner, name):
        self.attr_name = f"_lazy_{name}"
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        
        if not hasattr(obj, self.attr_name):
            setattr(obj, self.attr_name, self.func(obj))
        
        return getattr(obj, self.attr_name)


def validate_not_empty(value: Any, field_name: str) -> None:
    """Validate that a value is not empty."""
    from .exceptions import ValidationError
    
    if value is None:
        raise ValidationError(f"{field_name} cannot be None", field=field_name)
    
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f"{field_name} cannot be empty", field=field_name)
    
    if isinstance(value, (list, dict)) and len(value) == 0:
        raise ValidationError(f"{field_name} cannot be empty", field=field_name)


def validate_id(entity_id: str, entity_name: str = "Entity") -> None:
    """Validate entity ID format."""
    from .exceptions import ValidationError
    
    if not entity_id or not isinstance(entity_id, str):
        raise ValidationError(f"{entity_name} ID must be a non-empty string", field="id")
    
    if len(entity_id) > 256:
        raise ValidationError(f"{entity_name} ID is too long (max 256 chars)", field="id")

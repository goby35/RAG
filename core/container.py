# core/container.py
"""
Dependency Injection Container.

Provides centralized dependency management for the application.
"""

from typing import TypeVar, Type, Dict, Any, Optional, Callable
import logging

from core.base import Singleton

logger = logging.getLogger(__name__)
T = TypeVar('T')


class Container(metaclass=Singleton):
    """
    Dependency Injection Container.
    
    Manages service registration and resolution with support for:
    - Singleton instances
    - Factory functions
    - Lazy initialization
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._initialized = False
    
    def register(
        self,
        service_type: Type[T],
        instance: Optional[T] = None,
        factory: Optional[Callable[[], T]] = None,
        singleton: bool = True
    ) -> 'Container':
        """
        Register a service.
        
        Args:
            service_type: The type/class to register
            instance: Pre-created instance (optional)
            factory: Factory function to create instance (optional)
            singleton: Whether to cache instance (default True)
            
        Returns:
            Self for chaining
        """
        key = service_type.__name__
        
        if instance is not None:
            self._singletons[key] = instance
            logger.debug(f"Registered singleton instance: {key}")
        elif factory is not None:
            self._factories[key] = (factory, singleton)
            logger.debug(f"Registered factory: {key} (singleton={singleton})")
        else:
            raise ValueError(f"Must provide either instance or factory for {key}")
        
        return self
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service.
        
        Args:
            service_type: The type/class to resolve
            
        Returns:
            The service instance
        """
        key = service_type.__name__
        
        # Check for existing singleton
        if key in self._singletons:
            return self._singletons[key]
        
        # Check for factory
        if key in self._factories:
            factory, is_singleton = self._factories[key]
            instance = factory()
            
            if is_singleton:
                self._singletons[key] = instance
            
            return instance
        
        raise KeyError(f"Service not registered: {key}")
    
    def get(self, service_type: Type[T]) -> Optional[T]:
        """
        Get a service if registered, None otherwise.
        
        Args:
            service_type: The type/class to get
            
        Returns:
            The service instance or None
        """
        try:
            return self.resolve(service_type)
        except KeyError:
            return None
    
    def is_registered(self, service_type: Type[T]) -> bool:
        """Check if a service is registered."""
        key = service_type.__name__
        return key in self._singletons or key in self._factories
    
    def clear(self) -> None:
        """Clear all registrations."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._initialized = False
        logger.debug("Container cleared")
    
    def initialize_all(self) -> None:
        """Initialize all registered services."""
        if self._initialized:
            return
        
        for key, (factory, _) in self._factories.items():
            if key not in self._singletons:
                try:
                    self._singletons[key] = factory()
                    logger.debug(f"Initialized: {key}")
                except Exception as e:
                    logger.error(f"Failed to initialize {key}: {e}")
        
        self._initialized = True
        logger.info("Container initialization complete")


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def configure_container(settings=None) -> Container:
    """
    Configure the container with default services.
    
    Args:
        settings: Optional settings override
        
    Returns:
        Configured container
    """
    from config.settings import get_settings
    from config.models import ModelConfig
    from repositories.user_repository import UserRepository
    from repositories.claim_repository import ClaimRepository
    from repositories.entity_repository import EntityRepository
    from services.embedding_service import EmbeddingService
    from services.llm_service import LLMService
    from services.rag_service import RAGService
    from services.access_control_service import AccessControlService
    from services.presence_service import PresenceService
    from services.message_service import MessageService
    from services.claim_service import ClaimService
    
    container = get_container()
    
    if settings is None:
        settings = get_settings()
    
    # Register repositories
    container.register(
        UserRepository,
        factory=lambda: UserRepository()
    )
    container.register(
        ClaimRepository,
        factory=lambda: ClaimRepository()
    )
    container.register(
        EntityRepository,
        factory=lambda: EntityRepository()
    )
    
    # Register services
    container.register(
        EmbeddingService,
        factory=lambda: EmbeddingService(ModelConfig.DEFAULT_EMBEDDING)
    )
    container.register(
        LLMService,
        factory=lambda: LLMService(
            config=ModelConfig.DEFAULT_LLM,
            api_key=settings.openai_api_key
        )
    )
    container.register(
        AccessControlService,
        factory=lambda: AccessControlService()
    )
    container.register(
        PresenceService,
        factory=lambda: PresenceService()
    )
    container.register(
        MessageService,
        factory=lambda: MessageService(
            presence_service=container.resolve(PresenceService)
        )
    )
    container.register(
        RAGService,
        factory=lambda: RAGService(
            embedding_service=container.resolve(EmbeddingService),
            llm_service=container.resolve(LLMService),
            access_control_service=container.resolve(AccessControlService)
        )
    )
    container.register(
        ClaimService,
        factory=lambda: ClaimService()
    )
    
    logger.info("Container configured with default services")
    return container


def inject(service_type: Type[T]) -> T:
    """
    Decorator/function to inject a service.
    
    Usage:
        embedding_service = inject(EmbeddingService)
    """
    return get_container().resolve(service_type)

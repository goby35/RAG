# repositories/__init__.py
"""
Repositories layer - Data access patterns.

Repositories handle data persistence and retrieval, abstracting the data source.
"""

from .user_repository import UserRepository
from .claim_repository import ClaimRepository
from .entity_repository import EntityRepository
from .json_repository import JSONRepository

__all__ = [
    'UserRepository',
    'ClaimRepository',
    'EntityRepository',
    'JSONRepository',
]

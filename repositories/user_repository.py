# repositories/user_repository.py
"""
User Repository - Data access for User entities.
"""

from typing import List, Dict, Any, Optional
import logging

from repositories.json_repository import JSONRepository
from config.paths import USERS_FILE

logger = logging.getLogger(__name__)


class UserRepository(JSONRepository):
    """
    Repository for User entities.
    
    Extends JSONRepository with user-specific queries.
    """
    
    def __init__(self, file_path: str = USERS_FILE):
        super().__init__(
            file_path=file_path,
            id_field="user_id",
            entity_name="User"
        )
    
    def get_by_wallet_address(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """Get user by wallet address."""
        results = self.find_by(wallet_address=wallet_address)
        return results[0] if results else None
    
    def get_by_did(self, did: str) -> Optional[Dict[str, Any]]:
        """Get user by DID."""
        results = self.find_by(did=did)
        return results[0] if results else None
    
    def get_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get all users with a specific role."""
        all_users = self.get_all()
        return [
            user for user in all_users
            if role in user.get("roles", [])
        ]
    
    def get_user_ids(self) -> List[str]:
        """Get list of all user IDs."""
        users = self.get_all()
        return sorted([u.get("user_id", "") for u in users if u.get("user_id")])
    
    def update_reputation(self, user_id: str, reputation_score: float) -> bool:
        """Update user's reputation score."""
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user["reputation_score"] = reputation_score
        self.update(user)
        return True
    
    def update_presence(self, user_id: str, status: str) -> bool:
        """Update user's presence status."""
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user["presence_status"] = status
        self.update(user)
        return True
    
    def search_by_name(self, name_query: str) -> List[Dict[str, Any]]:
        """Search users by name (case-insensitive partial match)."""
        all_users = self.get_all()
        name_query = name_query.lower()
        return [
            user for user in all_users
            if name_query in user.get("name", "").lower()
        ]
    
    def get_users_with_bio(self) -> List[Dict[str, Any]]:
        """Get users that have a bio set."""
        all_users = self.get_all()
        return [
            user for user in all_users
            if user.get("bio")
        ]

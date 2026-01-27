# services/access_control_service.py
"""
Access Control Service - ReBAC implementation.
"""

from typing import List, Optional, Set, Dict, Any
from dataclasses import dataclass
import logging

from core.base import BaseService
from core.interfaces import IAccessControl
from core.exceptions import AccessDeniedError
from config.access import (
    AccessConfig,
    AccessTag,
    RelationshipType,
    REBAC_MATRIX
)

logger = logging.getLogger(__name__)


@dataclass
class AccessScope:
    """Result of access scope determination."""
    viewer_id: str
    target_id: str
    relationships: List[str]
    allowed_tags: List[str]
    is_self: bool = False
    
    def can_access(self, claim_tags: List[str]) -> bool:
        """Check if viewer can access a claim with given tags."""
        if not claim_tags:
            return AccessTag.PUBLIC.value in self.allowed_tags
        return any(tag in self.allowed_tags for tag in claim_tags)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "viewer_id": self.viewer_id,
            "target_id": self.target_id,
            "relationships": self.relationships,
            "allowed_tags": self.allowed_tags,
            "is_self": self.is_self
        }


class AccessControlService(BaseService, IAccessControl):
    """
    Service for access control using ReBAC.
    
    Implements relationship-based access control by:
    1. Determining relationships between viewer and target
    2. Mapping relationships to allowed access tags
    3. Filtering resources based on tags
    """
    
    def __init__(self, neo4j_client=None):
        super().__init__("AccessControlService")
        self._neo4j_client = neo4j_client
    
    def set_neo4j_client(self, client) -> None:
        """Set Neo4j client (for dependency injection)."""
        self._neo4j_client = client
    
    def can_access(
        self,
        viewer_id: str,
        target_id: str,
        resource_tags: List[str]
    ) -> bool:
        """Check if viewer can access resource with given tags."""
        allowed_tags = self.get_allowed_tags(viewer_id, target_id)
        
        if not resource_tags:
            return AccessTag.PUBLIC.value in allowed_tags
        
        return any(tag in allowed_tags for tag in resource_tags)
    
    def get_allowed_tags(self, viewer_id: str, target_id: str) -> List[str]:
        """Get list of access tags viewer is allowed to see."""
        relationships = self.get_relationships(viewer_id, target_id)
        return AccessConfig.combine_tags(relationships)
    
    def get_relationships(self, viewer_id: str, target_id: str) -> List[str]:
        """Get relationships between viewer and target."""
        # Self check
        if viewer_id == target_id:
            return [RelationshipType.SELF.value]
        
        # Query Neo4j for relationships if available
        if self._neo4j_client:
            return self._query_relationships(viewer_id, target_id)
        
        # Default to stranger
        return [RelationshipType.STRANGER.value]
    
    def determine_access_scope(
        self,
        viewer_id: str,
        target_id: str
    ) -> AccessScope:
        """Determine full access scope for viewer."""
        relationships = self.get_relationships(viewer_id, target_id)
        allowed_tags = AccessConfig.combine_tags(relationships)
        
        return AccessScope(
            viewer_id=viewer_id,
            target_id=target_id,
            relationships=relationships,
            allowed_tags=allowed_tags,
            is_self=(viewer_id == target_id)
        )
    
    def filter_claims_by_access(
        self,
        claims: List[Dict[str, Any]],
        viewer_id: str,
        target_id: str
    ) -> List[Dict[str, Any]]:
        """Filter claims based on access control."""
        scope = self.determine_access_scope(viewer_id, target_id)
        
        accessible = []
        for claim in claims:
            claim_tags = claim.get("access_tags", [AccessTag.PUBLIC.value])
            if scope.can_access(claim_tags):
                accessible.append(claim)
        
        return accessible
    
    def _query_relationships(self, viewer_id: str, target_id: str) -> List[str]:
        """Query Neo4j for relationships."""
        query = """
        MATCH (viewer:User {user_id: $viewer_id})
        MATCH (target:User {user_id: $target_id})
        OPTIONAL MATCH (viewer)-[r]->(target)
        RETURN type(r) as relationship_type
        """
        
        try:
            result = self._neo4j_client.run_query(query, {
                "viewer_id": viewer_id,
                "target_id": target_id
            })
            
            relationships = []
            for row in result:
                rel_type = row.get("relationship_type")
                if rel_type:
                    # Map Neo4j relationship types to our types
                    if rel_type == "FRIENDS_WITH":
                        relationships.append(RelationshipType.FRIEND.value)
                    elif rel_type == "WORKS_WITH":
                        relationships.append(RelationshipType.COLLEAGUE.value)
                    elif rel_type == "RECRUITING":
                        relationships.append(RelationshipType.RECRUITING.value)
            
            return relationships if relationships else [RelationshipType.STRANGER.value]
        except Exception as e:
            logger.warning(f"Failed to query relationships: {e}")
            return [RelationshipType.STRANGER.value]
    
    # Legacy compatibility methods
    def get_access_info(
        self,
        viewer_id: str,
        target_id: str,
        viewer_role: str = "Default"
    ) -> Dict[str, Any]:
        """Get access information (backward compatibility)."""
        if viewer_id == target_id:
            return {
                "type": "owner",
                "icon": "👤",
                "label": "Owner Access",
                "description": "Bạn đang xem hồ sơ của chính mình. Có thể xem TẤT CẢ dữ liệu.",
                "level": "success",
                "can_see": ["public", "private", "connections_only"]
            }
        elif viewer_role == "Recruiter":
            return {
                "type": "recruiter",
                "icon": "💼",
                "label": "Recruiter Access",
                "description": f"Bạn có thể xem dữ liệu `public` và `verified` của '{target_id}'.",
                "level": "info",
                "can_see": ["public", "connections_only (verified only)"]
            }
        elif viewer_id == "__ANONYMOUS__":
            return {
                "type": "anonymous",
                "icon": "👻",
                "label": "Anonymous Access",
                "description": f"Bạn chỉ có thể xem dữ liệu `public` của '{target_id}'.",
                "level": "warning",
                "can_see": ["public"]
            }
        else:
            return {
                "type": "public",
                "icon": "🌐",
                "label": "Public Access",
                "description": f"Bạn ({viewer_id}) chỉ có thể xem dữ liệu `public` của '{target_id}'.",
                "level": "warning",
                "can_see": ["public"]
            }

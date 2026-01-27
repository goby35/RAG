# utils/rebac.py - Relationship-based Access Control Module
"""
ReBAC (Relationship-based Access Control) Module for Graph-based RAG.

Implements dynamic access control based on social relationships in Neo4j Graph.

Access Tags:
- public: Visible to everyone
- friend: Visible to friends
- internal: Visible to colleagues (same organization)
- hr_sensitive: Visible to recruiters

ReBAC Mapping Matrix:
| Relationship | Allowed Tags                           |
|--------------|----------------------------------------|
| SELF         | public, friend, internal, hr_sensitive |
| STRANGER     | public                                 |
| FRIEND       | public, friend                         |
| COLLEAGUE    | public, internal                       |
| RECRUITING   | public, hr_sensitive                   |
"""

from typing import List, Set, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ACCESS TAGS
# ============================================================================

class AccessTag(str, Enum):
    """Access tags for claims."""
    PUBLIC = "public"
    FRIEND = "friend"
    INTERNAL = "internal"
    HR_SENSITIVE = "hr_sensitive"


# All available access tags
ALL_ACCESS_TAGS = [tag.value for tag in AccessTag]


# ============================================================================
# RELATIONSHIP TYPES
# ============================================================================

class RelationshipType(str, Enum):
    """Social relationship types."""
    SELF = "SELF"           # Viewer is the target user
    STRANGER = "STRANGER"   # No relationship
    FRIEND = "FRIEND"       # Friend relationship
    COLLEAGUE = "COLLEAGUE" # Colleague relationship
    RECRUITING = "RECRUITING"  # Recruiter-candidate relationship


# ============================================================================
# ReBAC MAPPING MATRIX
# ============================================================================

# Defines which access tags each relationship type can access
REBAC_MATRIX: Dict[str, List[str]] = {
    RelationshipType.SELF.value: [
        AccessTag.PUBLIC.value,
        AccessTag.FRIEND.value,
        AccessTag.INTERNAL.value,
        AccessTag.HR_SENSITIVE.value
    ],
    RelationshipType.STRANGER.value: [
        AccessTag.PUBLIC.value
    ],
    RelationshipType.FRIEND.value: [
        AccessTag.PUBLIC.value,
        AccessTag.FRIEND.value
    ],
    RelationshipType.COLLEAGUE.value: [
        AccessTag.PUBLIC.value,
        AccessTag.INTERNAL.value
    ],
    RelationshipType.RECRUITING.value: [
        AccessTag.PUBLIC.value,
        AccessTag.HR_SENSITIVE.value
    ]
}


# ============================================================================
# RESULT TYPES
# ============================================================================

@dataclass
class AccessScope:
    """Result of access scope determination."""
    viewer_id: str
    target_id: str
    relationships: List[str]  # List of relationship types found
    allowed_tags: List[str]   # Combined list of allowed access tags
    is_self: bool = False
    
    def can_access(self, claim_tags: List[str]) -> bool:
        """
        Check if viewer can access a claim with given tags.
        
        Access is granted if ANY of the claim's tags is in allowed_tags.
        
        Args:
            claim_tags: List of access tags on the claim
            
        Returns:
            bool: True if access is allowed
        """
        if not claim_tags:
            # If no tags specified, treat as public
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


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def get_allowed_tags_for_relationship(relationship: str) -> List[str]:
    """
    Get allowed access tags for a relationship type.
    
    Args:
        relationship: Relationship type string
        
    Returns:
        List of allowed access tags
    """
    return REBAC_MATRIX.get(relationship, REBAC_MATRIX[RelationshipType.STRANGER.value])


def combine_allowed_tags(relationships: List[str]) -> List[str]:
    """
    Combine allowed tags from multiple relationships.
    
    A viewer may have multiple relationships with target (e.g., both FRIEND and COLLEAGUE).
    This function combines all allowed tags.
    
    Args:
        relationships: List of relationship types
        
    Returns:
        Combined list of unique allowed access tags
    """
    allowed_tags: Set[str] = set()
    
    for rel in relationships:
        tags = get_allowed_tags_for_relationship(rel)
        allowed_tags.update(tags)
    
    return list(allowed_tags)


def determine_access_scope(
    viewer_id: str,
    target_id: str,
    neo4j_client: Any
) -> AccessScope:
    """
    Determine access scope based on relationship between viewer and target.
    
    This is the main function for ReBAC - it queries Neo4j to find relationships
    and returns the allowed access tags.
    
    Args:
        viewer_id: ID of the user viewing
        target_id: ID of the user whose claims are being viewed
        neo4j_client: Neo4j client instance
        
    Returns:
        AccessScope object with allowed tags
    """
    # Check if viewer is viewing their own profile
    if viewer_id == target_id:
        return AccessScope(
            viewer_id=viewer_id,
            target_id=target_id,
            relationships=[RelationshipType.SELF.value],
            allowed_tags=REBAC_MATRIX[RelationshipType.SELF.value],
            is_self=True
        )
    
    # Query Neo4j for relationships
    relationships = query_relationships(viewer_id, target_id, neo4j_client)
    
    # If no relationships found, treat as stranger
    if not relationships:
        relationships = [RelationshipType.STRANGER.value]
    
    # Combine allowed tags from all relationships
    allowed_tags = combine_allowed_tags(relationships)
    
    return AccessScope(
        viewer_id=viewer_id,
        target_id=target_id,
        relationships=relationships,
        allowed_tags=allowed_tags,
        is_self=False
    )


def query_relationships(
    viewer_id: str,
    target_id: str,
    neo4j_client: Any
) -> List[str]:
    """
    Query Neo4j for relationships between viewer and target.
    
    Args:
        viewer_id: Viewer user ID
        target_id: Target user ID
        neo4j_client: Neo4j client instance
        
    Returns:
        List of relationship type strings
    """
    query = """
    MATCH (viewer:User {user_id: $viewer_id})-[r]-(target:User {user_id: $target_id})
    WHERE type(r) IN ['FRIEND', 'COLLEAGUE', 'RECRUITING']
    RETURN DISTINCT type(r) as relationship_type
    """
    
    try:
        results = neo4j_client.run_query(query, {
            "viewer_id": viewer_id,
            "target_id": target_id
        })
        
        relationships = [r["relationship_type"] for r in results]
        logger.debug(f"Found relationships between {viewer_id} and {target_id}: {relationships}")
        
        return relationships
        
    except Exception as e:
        logger.error(f"Error querying relationships: {e}")
        return []


# ============================================================================
# CLAIM FILTERING
# ============================================================================

def filter_claims_by_access(
    claims: List[Dict[str, Any]],
    access_scope: AccessScope
) -> List[Dict[str, Any]]:
    """
    Filter claims based on access scope.
    
    Args:
        claims: List of claim dictionaries
        access_scope: AccessScope object from determine_access_scope
        
    Returns:
        Filtered list of claims that viewer can access
    """
    accessible_claims = []
    
    for claim in claims:
        # Get access tags from claim (support both old and new format)
        access_tags = claim.get('access_tags', [])
        
        # Backward compatibility: convert old access_level to access_tags
        if not access_tags and 'access_level' in claim:
            access_tags = convert_access_level_to_tags(claim['access_level'])
        
        # Check if viewer can access this claim
        if access_scope.can_access(access_tags):
            accessible_claims.append(claim)
    
    return accessible_claims


def convert_access_level_to_tags(access_level: str) -> List[str]:
    """
    Convert old access_level format to new access_tags format.
    
    Mapping:
    - public -> [public]
    - private -> [hr_sensitive, internal, friend] (owner-only effectively)
    - connections_only -> [friend, internal]
    - recruiter -> [hr_sensitive]
    
    Args:
        access_level: Old access level string
        
    Returns:
        List of access tags
    """
    mapping = {
        'public': [AccessTag.PUBLIC.value],
        'private': [],  # Empty means only SELF can access
        'connections_only': [AccessTag.FRIEND.value, AccessTag.INTERNAL.value],
        'recruiter': [AccessTag.HR_SENSITIVE.value]
    }
    
    return mapping.get(access_level, [AccessTag.PUBLIC.value])


# ============================================================================
# CYPHER QUERY HELPERS
# ============================================================================

def build_rebac_where_clause(
    viewer_id: str,
    target_id: str,
    claim_alias: str = "c"
) -> str:
    """
    Build a Cypher WHERE clause for ReBAC filtering.
    
    This can be used directly in Neo4j queries to filter claims.
    
    Args:
        viewer_id: Viewer user ID
        target_id: Target user ID
        claim_alias: Alias for Claim node in query (default: "c")
        
    Returns:
        Cypher WHERE clause string
    """
    # Note: This is a template - actual query would need parameter binding
    return f"""
    (
        // SELF - can see everything
        $viewer_id = $target_id
        OR
        // PUBLIC - everyone can see
        '{AccessTag.PUBLIC.value}' IN {claim_alias}.access_tags
        OR
        // FRIEND - check if viewer is friend and claim has 'friend' tag
        (
            EXISTS((viewer)-[:FRIEND]-(target))
            AND '{AccessTag.FRIEND.value}' IN {claim_alias}.access_tags
        )
        OR
        // COLLEAGUE - check if viewer is colleague and claim has 'internal' tag
        (
            EXISTS((viewer)-[:COLLEAGUE]-(target))
            AND '{AccessTag.INTERNAL.value}' IN {claim_alias}.access_tags
        )
        OR
        // RECRUITING - check if viewer is recruiting target and claim has 'hr_sensitive' tag
        (
            EXISTS((viewer)-[:RECRUITING]->(target))
            AND '{AccessTag.HR_SENSITIVE.value}' IN {claim_alias}.access_tags
        )
    )
    """


def get_accessible_claims_query() -> str:
    """
    Get Cypher query for fetching accessible claims with ReBAC.
    
    Returns:
        Cypher query string (requires $viewer_id and $target_id parameters)
    """
    return """
    MATCH (target:User {user_id: $target_id})-[:MAKES_CLAIM]->(c:Claim)
    OPTIONAL MATCH (viewer:User {user_id: $viewer_id})
    OPTIONAL MATCH (viewer)-[friend_rel:FRIEND]-(target)
    OPTIONAL MATCH (viewer)-[colleague_rel:COLLEAGUE]-(target)
    OPTIONAL MATCH (viewer)-[recruiting_rel:RECRUITING]->(target)
    
    WITH c, 
         $viewer_id = $target_id AS is_self,
         friend_rel IS NOT NULL AS is_friend,
         colleague_rel IS NOT NULL AS is_colleague,
         recruiting_rel IS NOT NULL AS is_recruiting,
         c.access_tags AS tags
    
    // Apply ReBAC rules
    WHERE 
        is_self
        OR 'public' IN tags
        OR (is_friend AND 'friend' IN tags)
        OR (is_colleague AND 'internal' IN tags)
        OR (is_recruiting AND 'hr_sensitive' IN tags)
    
    RETURN c
    ORDER BY c.created_at DESC
    """


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_relationship_display_name(relationship: str) -> str:
    """Get human-readable name for relationship type."""
    names = {
        RelationshipType.SELF.value: "👤 Bản thân",
        RelationshipType.STRANGER.value: "👥 Người lạ",
        RelationshipType.FRIEND.value: "🤝 Bạn bè",
        RelationshipType.COLLEAGUE.value: "💼 Đồng nghiệp",
        RelationshipType.RECRUITING.value: "📋 Nhà tuyển dụng"
    }
    return names.get(relationship, relationship)


def get_access_tag_display_name(tag: str) -> str:
    """Get human-readable name for access tag."""
    names = {
        AccessTag.PUBLIC.value: "🌐 Công khai",
        AccessTag.FRIEND.value: "🤝 Bạn bè",
        AccessTag.INTERNAL.value: "🏢 Nội bộ",
        AccessTag.HR_SENSITIVE.value: "📋 HR"
    }
    return names.get(tag, tag)


def format_access_scope(access_scope: AccessScope) -> str:
    """Format access scope for display."""
    rel_names = [get_relationship_display_name(r) for r in access_scope.relationships]
    tag_names = [get_access_tag_display_name(t) for t in access_scope.allowed_tags]
    
    return (
        f"🔐 Access Scope\n"
        f"  Viewer: {access_scope.viewer_id}\n"
        f"  Target: {access_scope.target_id}\n"
        f"  Relationships: {', '.join(rel_names)}\n"
        f"  Allowed Tags: {', '.join(tag_names)}"
    )


def validate_access_tags(tags: List[str]) -> List[str]:
    """
    Validate and normalize access tags.
    
    Args:
        tags: List of access tag strings
        
    Returns:
        List of valid access tags
    """
    valid_tags = []
    for tag in tags:
        tag_lower = tag.lower().strip()
        if tag_lower in ALL_ACCESS_TAGS:
            valid_tags.append(tag_lower)
        else:
            logger.warning(f"Invalid access tag ignored: {tag}")
    
    # Default to public if no valid tags
    if not valid_tags:
        valid_tags = [AccessTag.PUBLIC.value]
    
    return valid_tags

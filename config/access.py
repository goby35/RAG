# config/access.py
"""
Access control configuration - Access levels, tags, and ReBAC matrix.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from enum import Enum


class AccessLevel(str, Enum):
    """Legacy access levels (backward compatibility)."""
    PUBLIC = "public"
    PRIVATE = "private"
    CONNECTIONS_ONLY = "connections_only"
    RECRUITER = "recruiter"


class AccessTag(str, Enum):
    """ReBAC access tags."""
    PUBLIC = "public"
    FRIEND = "friend"
    INTERNAL = "internal"
    HR_SENSITIVE = "hr_sensitive"


class RelationshipType(str, Enum):
    """Social relationship types for ReBAC."""
    SELF = "SELF"
    STRANGER = "STRANGER"
    FRIEND = "FRIEND"
    COLLEAGUE = "COLLEAGUE"
    RECRUITING = "RECRUITING"


class ClaimStatus(str, Enum):
    """Claim verification status."""
    PENDING = "pending"
    SELF_DECLARED = "self_declared"
    ATTESTED = "attested"
    REVOKED = "revoked"


@dataclass
class ConfidenceScoreConfig:
    """Configuration for confidence scoring."""
    base_self_declared: float = 0.3
    with_evidence: float = 0.5
    with_attestation: float = 0.9
    trusted_organization: float = 1.0
    
    # Thresholds
    min_for_rag: float = 0.3
    min_for_trusted: float = 0.8


class AccessConfig:
    """
    Central access control configuration.
    """
    
    # ReBAC Mapping Matrix
    REBAC_MATRIX: Dict[str, List[str]] = {
        RelationshipType.SELF.value: [
            AccessTag.PUBLIC.value,
            AccessTag.FRIEND.value,
            AccessTag.INTERNAL.value,
            AccessTag.HR_SENSITIVE.value,
        ],
        RelationshipType.STRANGER.value: [
            AccessTag.PUBLIC.value,
        ],
        RelationshipType.FRIEND.value: [
            AccessTag.PUBLIC.value,
            AccessTag.FRIEND.value,
        ],
        RelationshipType.COLLEAGUE.value: [
            AccessTag.PUBLIC.value,
            AccessTag.INTERNAL.value,
        ],
        RelationshipType.RECRUITING.value: [
            AccessTag.PUBLIC.value,
            AccessTag.HR_SENSITIVE.value,
        ],
    }
    
    # Confidence scores
    CONFIDENCE = ConfidenceScoreConfig()
    
    # Verified statuses
    VERIFIED_STATUSES: Set[str] = {
        ClaimStatus.ATTESTED.value,
        ClaimStatus.SELF_DECLARED.value,
    }
    
    # Display labels
    ACCESS_LEVEL_LABELS: Dict[str, str] = {
        'public': 'Công khai - Ai cũng xem được',
        'private': 'Riêng tư - Chỉ Owner xem',
        'connections_only': 'Chỉ kết nối - Connections xem',
        'recruiter': 'Nhà tuyển dụng - Recruiter xem',
    }
    
    ACCESS_TAG_LABELS: Dict[str, str] = {
        'public': 'Công khai - Ai cũng xem được',
        'friend': 'Bạn bè - Chỉ bạn bè xem được',
        'internal': 'Nội bộ - Đồng nghiệp xem được',
        'hr_sensitive': 'HR - Nhà tuyển dụng xem được',
    }
    
    STATUS_LABELS: Dict[str, str] = {
        'pending': 'Chờ xác thực',
        'self_declared': 'Tự khai báo',
        'attested': 'Đã xác thực (EAS)',
        'revoked': 'Đã thu hồi',
    }
    
    @classmethod
    def get_allowed_tags(cls, relationship: str) -> List[str]:
        """Get allowed access tags for a relationship type."""
        return cls.REBAC_MATRIX.get(
            relationship,
            cls.REBAC_MATRIX[RelationshipType.STRANGER.value]
        )
    
    @classmethod
    def combine_tags(cls, relationships: List[str]) -> List[str]:
        """Combine allowed tags from multiple relationships."""
        allowed: Set[str] = set()
        for rel in relationships:
            allowed.update(cls.get_allowed_tags(rel))
        return list(allowed)
    
    @classmethod
    def is_verified(cls, status: str) -> bool:
        """Check if status is considered verified."""
        return status in cls.VERIFIED_STATUSES
    
    @classmethod
    def calculate_confidence(
        cls,
        has_evidence: bool = False,
        has_attestation: bool = False,
        from_trusted_org: bool = False
    ) -> float:
        """Calculate confidence score based on evidence."""
        if from_trusted_org:
            return cls.CONFIDENCE.trusted_organization
        if has_attestation:
            return cls.CONFIDENCE.with_attestation
        if has_evidence:
            return cls.CONFIDENCE.with_evidence
        return cls.CONFIDENCE.base_self_declared


# Backward compatibility exports
ACCESS_LEVELS = AccessConfig.ACCESS_LEVEL_LABELS
ACCESS_TAGS = AccessConfig.ACCESS_TAG_LABELS
REBAC_MATRIX = AccessConfig.REBAC_MATRIX
STATUS_OPTIONS = AccessConfig.STATUS_LABELS
VERIFIED_STATUSES = list(AccessConfig.VERIFIED_STATUSES)
CONFIDENCE_SCORES = {
    'base_self_declared': AccessConfig.CONFIDENCE.base_self_declared,
    'with_evidence': AccessConfig.CONFIDENCE.with_evidence,
    'with_attestation': AccessConfig.CONFIDENCE.with_attestation,
    'trusted_organization': AccessConfig.CONFIDENCE.trusted_organization,
}
MIN_CONFIDENCE_FOR_RAG = AccessConfig.CONFIDENCE.min_for_rag
MIN_CONFIDENCE_TRUSTED = AccessConfig.CONFIDENCE.min_for_trusted

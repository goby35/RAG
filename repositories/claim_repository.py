# repositories/claim_repository.py
"""
Claim Repository - Data access for Claim entities.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from repositories.json_repository import JSONRepository
from config.paths import CLAIMS_FILE
from config.access import AccessConfig, ClaimStatus

logger = logging.getLogger(__name__)


class ClaimRepository(JSONRepository):
    """
    Repository for Claim entities.
    
    Extends JSONRepository with claim-specific queries.
    """
    
    def __init__(self, file_path: str = CLAIMS_FILE):
        super().__init__(
            file_path=file_path,
            id_field="claim_id",
            entity_name="Claim"
        )
    
    def get_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all claims for a specific user."""
        return self.find_by(user_id=user_id)
    
    def get_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Get all claims with a specific topic."""
        return self.find_by(topic=topic)
    
    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all claims with a specific status."""
        return self.find_by(status=status)
    
    def get_verified_claims(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all verified/attested claims."""
        all_claims = self.get_by_user(user_id) if user_id else self.get_all()
        return [
            claim for claim in all_claims
            if claim.get("status") in AccessConfig.VERIFIED_STATUSES
        ]
    
    def get_high_confidence_claims(
        self,
        user_id: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Get claims with confidence above threshold."""
        claims = self.get_by_user(user_id) if user_id else self.get_all()
        return [
            claim for claim in claims
            if claim.get("confidence_score", 0) >= min_confidence
        ]
    
    def get_public_claims(self, user_id: str) -> List[Dict[str, Any]]:
        """Get public claims for a user."""
        claims = self.get_by_user(user_id)
        return [
            claim for claim in claims
            if claim.get("access_level") == "public"
            or "public" in claim.get("access_tags", [])
        ]
    
    def get_accessible_claims(
        self,
        user_id: str,
        allowed_tags: List[str]
    ) -> List[Dict[str, Any]]:
        """Get claims accessible with given access tags."""
        claims = self.get_by_user(user_id)
        
        accessible = []
        for claim in claims:
            claim_tags = claim.get("access_tags", ["public"])
            if any(tag in allowed_tags for tag in claim_tags):
                accessible.append(claim)
        
        return accessible
    
    def update_status(
        self,
        claim_id: str,
        status: str,
        confidence_score: Optional[float] = None
    ) -> bool:
        """Update claim status and optionally confidence."""
        claim = self.get_by_id(claim_id)
        if not claim:
            return False
        
        claim["status"] = status
        claim["updated_at"] = datetime.now().isoformat()
        
        if confidence_score is not None:
            claim["confidence_score"] = confidence_score
        elif status == ClaimStatus.ATTESTED.value:
            claim["confidence_score"] = AccessConfig.CONFIDENCE.with_attestation
        
        self.update(claim)
        return True
    
    def add_attestation(
        self,
        claim_id: str,
        eas_uid: str,
        attester_address: str
    ) -> bool:
        """Add EAS attestation to a claim."""
        claim = self.get_by_id(claim_id)
        if not claim:
            return False
        
        claim["eas_uid"] = eas_uid
        claim["attester_address"] = attester_address
        claim["status"] = ClaimStatus.ATTESTED.value
        claim["confidence_score"] = AccessConfig.CONFIDENCE.with_attestation
        claim["verified_at"] = datetime.now().isoformat()
        claim["updated_at"] = datetime.now().isoformat()
        
        self.update(claim)
        return True
    
    def revoke_claim(self, claim_id: str) -> bool:
        """Revoke a claim."""
        return self.update_status(claim_id, ClaimStatus.REVOKED.value, 0.0)
    
    def get_claims_for_rag(
        self,
        user_id: str,
        min_confidence: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get claims suitable for RAG (meeting minimum confidence)."""
        if min_confidence is None:
            min_confidence = AccessConfig.CONFIDENCE.min_for_rag
        
        claims = self.get_by_user(user_id)
        return [
            claim for claim in claims
            if claim.get("confidence_score", 0) >= min_confidence
            and claim.get("status") != ClaimStatus.REVOKED.value
        ]
    
    def get_documents_and_metadata(self) -> tuple:
        """
        Get documents and metadata for RAG.
        
        Returns:
            Tuple of (documents, metadata) lists
        """
        claims = self.get_all()
        
        documents = []
        metadata = []
        
        for claim in claims:
            content = claim.get("content_summary", "")
            if content:
                documents.append(content)
                metadata.append({
                    "claim_id": claim.get("claim_id"),
                    "user_id": claim.get("user_id"),
                    "topic": claim.get("topic"),
                    "access_level": claim.get("access_level", "public"),
                    "access_tags": claim.get("access_tags", ["public"]),
                    "status": claim.get("status", "self_declared"),
                    "confidence_score": claim.get("confidence_score", 0.3),
                    "source": claim.get("user_id")  # For backward compatibility
                })
        
        return documents, metadata

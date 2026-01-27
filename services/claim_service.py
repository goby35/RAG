# services/claim_service.py
"""
Claim Service - Business logic for claims management.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid
import logging

from core.base import BaseService
from core.exceptions import ValidationError, DataNotFoundError
from config.access import AccessConfig, ClaimStatus

logger = logging.getLogger(__name__)


class ClaimService(BaseService):
    """
    Service for managing claims.
    
    Handles:
    - Claim CRUD operations
    - Confidence score calculation
    - Claim verification
    """
    
    def __init__(self, neo4j_client=None):
        super().__init__("ClaimService")
        self._neo4j_client = neo4j_client
    
    def set_neo4j_client(self, client) -> None:
        """Set Neo4j client."""
        self._neo4j_client = client
    
    def create_claim(
        self,
        user_id: str,
        content_summary: str,
        topic: str = "other",
        access_level: str = "public",
        access_tags: Optional[List[str]] = None,
        evidence_ids: Optional[List[str]] = None,
        entity_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new claim.
        
        Args:
            user_id: ID of the user making the claim
            content_summary: Summary text for RAG
            topic: Claim topic category
            access_level: Access level (legacy)
            access_tags: ReBAC access tags
            evidence_ids: List of evidence IDs to link
            entity_ids: List of entity IDs to link
            
        Returns:
            Created claim data
        """
        claim_id = str(uuid.uuid4())
        
        # Calculate initial confidence
        has_evidence = bool(evidence_ids)
        confidence = AccessConfig.calculate_confidence(has_evidence=has_evidence)
        
        claim_data = {
            "claim_id": claim_id,
            "user_id": user_id,
            "content_summary": content_summary,
            "topic": topic,
            "access_level": access_level,
            "access_tags": access_tags or ["public"],
            "status": ClaimStatus.SELF_DECLARED.value,
            "confidence_score": confidence,
            "created_at": datetime.now().isoformat()
        }
        
        if self._neo4j_client:
            self._create_claim_in_db(claim_data, evidence_ids, entity_ids)
        
        logger.info(f"Created claim {claim_id} for user {user_id}")
        return claim_data
    
    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """Get a claim by ID."""
        if not self._neo4j_client:
            return None
        
        query = """
        MATCH (u:User)-[:MAKES_CLAIM]->(c:Claim {claim_id: $claim_id})
        OPTIONAL MATCH (c)-[:ABOUT]->(e:Entity)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(ev:Evidence)
        RETURN c, u.user_id as user_id, 
               collect(DISTINCT e) as entities,
               collect(DISTINCT ev) as evidence
        """
        
        try:
            result = self._neo4j_client.run_query(query, {"claim_id": claim_id})
            
            if not result:
                return None
            
            row = result[0]
            claim = dict(row.get("c", {}))
            claim["user_id"] = row.get("user_id")
            claim["entities"] = row.get("entities", [])
            claim["evidence"] = row.get("evidence", [])
            
            return claim
            
        except Exception as e:
            logger.error(f"Failed to get claim {claim_id}: {e}")
            return None
    
    def get_claims_by_user(
        self,
        user_id: str,
        status_filter: Optional[List[str]] = None,
        topic_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all claims for a user."""
        if not self._neo4j_client:
            return []
        
        conditions = ["u.user_id = $user_id"]
        params = {"user_id": user_id}
        
        if status_filter:
            conditions.append("c.status IN $statuses")
            params["statuses"] = status_filter
        
        if topic_filter:
            conditions.append("c.topic = $topic")
            params["topic"] = topic_filter
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        MATCH (u:User)-[:MAKES_CLAIM]->(c:Claim)
        WHERE {where_clause}
        OPTIONAL MATCH (c)-[:ABOUT]->(e:Entity)
        RETURN c, collect(DISTINCT e.name) as entity_names
        ORDER BY c.created_at DESC
        """
        
        try:
            result = self._neo4j_client.run_query(query, params)
            
            claims = []
            for row in result:
                claim = dict(row.get("c", {}))
                claim["entity_names"] = row.get("entity_names", [])
                claims.append(claim)
            
            return claims
            
        except Exception as e:
            logger.error(f"Failed to get claims for user {user_id}: {e}")
            return []
    
    def update_claim_status(
        self,
        claim_id: str,
        new_status: str,
        attester_id: Optional[str] = None,
        eas_uid: Optional[str] = None
    ) -> bool:
        """
        Update claim verification status.
        
        Args:
            claim_id: Claim ID
            new_status: New status
            attester_id: ID of the attester (for verified claims)
            eas_uid: EAS attestation UID
            
        Returns:
            True if successful
        """
        try:
            status = ClaimStatus(new_status)
        except ValueError:
            raise ValidationError(f"Invalid claim status: {new_status}", field="status")
        
        # Recalculate confidence based on new status
        has_attestation = status == ClaimStatus.ATTESTED
        confidence = AccessConfig.calculate_confidence(has_attestation=has_attestation)
        
        if not self._neo4j_client:
            return True
        
        query = """
        MATCH (c:Claim {claim_id: $claim_id})
        SET c.status = $status,
            c.confidence_score = $confidence,
            c.updated_at = datetime()
        """
        
        params = {
            "claim_id": claim_id,
            "status": status.value,
            "confidence": confidence
        }
        
        if attester_id:
            query += ", c.attester_id = $attester_id"
            params["attester_id"] = attester_id
        
        if eas_uid:
            query += ", c.eas_uid = $eas_uid, c.verified_at = datetime()"
            params["eas_uid"] = eas_uid
        
        query += " RETURN c"
        
        try:
            self._neo4j_client.run_query(query, params)
            logger.info(f"Updated claim {claim_id} status to {status.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to update claim status: {e}")
            return False
    
    def add_evidence_to_claim(
        self,
        claim_id: str,
        evidence_type: str,
        evidence_url: str,
        description: Optional[str] = None
    ) -> bool:
        """Add evidence to a claim and update confidence."""
        evidence_id = str(uuid.uuid4())
        
        if not self._neo4j_client:
            return True
        
        query = """
        MATCH (c:Claim {claim_id: $claim_id})
        CREATE (e:Evidence {
            evidence_id: $evidence_id,
            type: $type,
            url: $url,
            description: $description,
            created_at: datetime()
        })
        CREATE (c)-[:SUPPORTED_BY]->(e)
        WITH c
        SET c.confidence_score = 
            CASE WHEN c.status = 'attested' THEN 0.9
                 ELSE 0.5 END,
            c.updated_at = datetime()
        RETURN c
        """
        
        try:
            self._neo4j_client.run_query(query, {
                "claim_id": claim_id,
                "evidence_id": evidence_id,
                "type": evidence_type,
                "url": evidence_url,
                "description": description
            })
            logger.info(f"Added evidence {evidence_id} to claim {claim_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add evidence: {e}")
            return False
    
    def delete_claim(self, claim_id: str, user_id: str) -> bool:
        """
        Delete a claim.
        
        Only the claim owner can delete it.
        """
        if not self._neo4j_client:
            return True
        
        # Verify ownership
        query = """
        MATCH (u:User {user_id: $user_id})-[:MAKES_CLAIM]->(c:Claim {claim_id: $claim_id})
        OPTIONAL MATCH (c)-[r]-()
        DELETE r, c
        RETURN count(c) as deleted
        """
        
        try:
            result = self._neo4j_client.run_query(query, {
                "claim_id": claim_id,
                "user_id": user_id
            })
            
            deleted = result[0].get("deleted", 0) if result else 0
            
            if deleted > 0:
                logger.info(f"Deleted claim {claim_id}")
                return True
            else:
                logger.warning(f"Claim {claim_id} not found or not owned by {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete claim: {e}")
            return False
    
    def _create_claim_in_db(
        self,
        claim_data: Dict[str, Any],
        evidence_ids: Optional[List[str]],
        entity_ids: Optional[List[str]]
    ) -> None:
        """Create claim in Neo4j database."""
        query = """
        MATCH (u:User {user_id: $user_id})
        CREATE (c:Claim {
            claim_id: $claim_id,
            content_summary: $content_summary,
            topic: $topic,
            access_level: $access_level,
            access_tags: $access_tags,
            status: $status,
            confidence_score: $confidence_score,
            created_at: datetime($created_at)
        })
        CREATE (u)-[:MAKES_CLAIM]->(c)
        RETURN c
        """
        
        self._neo4j_client.run_query(query, claim_data)
        
        # Link to entities
        if entity_ids:
            for entity_id in entity_ids:
                link_query = """
                MATCH (c:Claim {claim_id: $claim_id})
                MATCH (e:Entity {entity_id: $entity_id})
                CREATE (c)-[:ABOUT]->(e)
                """
                self._neo4j_client.run_query(link_query, {
                    "claim_id": claim_data["claim_id"],
                    "entity_id": entity_id
                })
        
        # Link to evidence
        if evidence_ids:
            for evidence_id in evidence_ids:
                link_query = """
                MATCH (c:Claim {claim_id: $claim_id})
                MATCH (ev:Evidence {evidence_id: $evidence_id})
                CREATE (c)-[:SUPPORTED_BY]->(ev)
                """
                self._neo4j_client.run_query(link_query, {
                    "claim_id": claim_data["claim_id"],
                    "evidence_id": evidence_id
                })
    
    def get_confidence_summary(
        self,
        claims: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get summary statistics for claim confidence."""
        if not claims:
            return {
                "total": 0,
                "verified": 0,
                "with_evidence": 0,
                "self_declared": 0,
                "avg_confidence": 0.0
            }
        
        verified = sum(1 for c in claims if c.get("status") == ClaimStatus.ATTESTED.value)
        with_evidence = sum(1 for c in claims if c.get("confidence_score", 0) >= 0.5)
        self_declared = sum(1 for c in claims if c.get("status") == ClaimStatus.SELF_DECLARED.value)
        
        confidences = [c.get("confidence_score", 0.3) for c in claims]
        avg_confidence = sum(confidences) / len(confidences)
        
        return {
            "total": len(claims),
            "verified": verified,
            "with_evidence": with_evidence,
            "self_declared": self_declared,
            "avg_confidence": avg_confidence
        }

# repositories/entity_repository.py
"""
Entity Repository - Data access for Entity nodes.
"""

from typing import List, Dict, Any, Optional
import logging

from repositories.json_repository import JSONRepository
from config.paths import ENTITIES_FILE

logger = logging.getLogger(__name__)


class EntityRepository(JSONRepository):
    """
    Repository for Entity nodes (Skills, Organizations, etc.).
    
    Handles entity deduplication via canonical_id.
    """
    
    def __init__(self, file_path: str = ENTITIES_FILE):
        super().__init__(
            file_path=file_path,
            id_field="entity_id",
            entity_name="Entity"
        )
    
    def get_by_canonical_id(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by canonical ID."""
        results = self.find_by(canonical_id=canonical_id)
        return results[0] if results else None
    
    def get_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get all entities of a specific type."""
        return self.find_by(type=entity_type)
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get entity by exact name match."""
        results = self.find_by(name=name)
        return results[0] if results else None
    
    def search_by_name(self, name_query: str) -> List[Dict[str, Any]]:
        """Search entities by name (case-insensitive partial match)."""
        all_entities = self.get_all()
        name_query = name_query.lower()
        return [
            entity for entity in all_entities
            if name_query in entity.get("name", "").lower()
        ]
    
    def get_skills(self) -> List[Dict[str, Any]]:
        """Get all Skill entities."""
        return self.get_by_type("Skill")
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """Get all Organization entities."""
        return self.get_by_type("Organization")
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all Project entities."""
        return self.get_by_type("Project")
    
    def get_or_create(
        self,
        name: str,
        entity_type: str,
        canonical_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing entity or create new one.
        
        Uses canonical_id for deduplication if provided.
        """
        # Check by canonical_id first
        if canonical_id:
            existing = self.get_by_canonical_id(canonical_id)
            if existing:
                return existing
        
        # Check by name and type
        all_entities = self.get_all()
        for entity in all_entities:
            if (entity.get("name") == name and 
                entity.get("type") == entity_type):
                return entity
        
        # Create new entity
        import uuid
        new_entity = {
            "entity_id": str(uuid.uuid4()),
            "name": name,
            "type": entity_type,
            "canonical_id": canonical_id or f"{entity_type.lower()}:{name.lower().replace(' ', '_')}"
        }
        
        return self.create(new_entity)
    
    def merge_entities(
        self,
        source_id: str,
        target_id: str
    ) -> bool:
        """
        Merge two entities (for deduplication).
        
        Keeps target, deletes source.
        """
        source = self.get_by_id(source_id)
        target = self.get_by_id(target_id)
        
        if not source or not target:
            return False
        
        # Merge aliases
        target_aliases = target.get("aliases", [])
        source_aliases = source.get("aliases", [])
        
        if source.get("name") not in target_aliases:
            target_aliases.append(source.get("name"))
        
        target_aliases.extend([
            alias for alias in source_aliases
            if alias not in target_aliases
        ])
        
        target["aliases"] = target_aliases
        
        # Update target and delete source
        self.update(target)
        self.delete(source_id)
        
        logger.info(f"Merged entity {source_id} into {target_id}")
        return True
    
    def add_alias(self, entity_id: str, alias: str) -> bool:
        """Add an alias to an entity."""
        entity = self.get_by_id(entity_id)
        if not entity:
            return False
        
        aliases = entity.get("aliases", [])
        if alias not in aliases:
            aliases.append(alias)
            entity["aliases"] = aliases
            self.update(entity)
        
        return True


class EvidenceRepository(JSONRepository):
    """
    Repository for Evidence nodes.
    """
    
    def __init__(self, file_path: str = "data/evidence.json"):
        super().__init__(
            file_path=file_path,
            id_field="evidence_id",
            entity_name="Evidence"
        )
    
    def get_by_type(self, evidence_type: str) -> List[Dict[str, Any]]:
        """Get all evidence of a specific type."""
        return self.find_by(type=evidence_type)
    
    def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get evidence by URL."""
        results = self.find_by(url=url)
        return results[0] if results else None
    
    def get_for_claim(self, claim_id: str) -> List[Dict[str, Any]]:
        """Get all evidence for a claim."""
        return self.find_by(claim_id=claim_id)

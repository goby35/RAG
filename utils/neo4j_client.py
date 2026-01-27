# utils/neo4j_client.py - Neo4j Database Client
"""
Neo4j Client for Graph-based RAG Application.

Provides connection management and query utilities for interacting with Neo4j.
"""

from neo4j import GraphDatabase, Driver
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Neo4j Database Client.
    
    Singleton pattern để quản lý connection pool tới Neo4j.
    """
    
    _instance: Optional['Neo4jClient'] = None
    _driver: Optional[Driver] = None
    
    def __new__(cls, uri: str = None, user: str = None, password: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """
        Initialize Neo4j client.
        
        Args:
            uri: Neo4j connection URI (bolt://localhost:7687)
            user: Username
            password: Password
        """
        if self._driver is None and uri is not None:
            self._uri = uri
            self._user = user
            self._password = password
            self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j."""
        try:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password)
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self._uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            Neo4jClient._instance = None
            logger.info("Neo4j connection closed")
    
    @property
    def driver(self) -> Driver:
        """Get the Neo4j driver instance."""
        if self._driver is None:
            raise RuntimeError("Neo4j client not initialized. Call Neo4jClient(uri, user, password) first.")
        return self._driver
    
    @contextmanager
    def session(self, database: str = "neo4j"):
        """
        Context manager for Neo4j session.
        
        Args:
            database: Database name (default: neo4j)
            
        Yields:
            Neo4j session
        """
        session = self.driver.session(database=database)
        try:
            yield session
        finally:
            session.close()
    
    # ========================================================================
    # CRUD Operations
    # ========================================================================
    
    def run_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """
        Execute a Cypher query and return results.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def run_write_query(self, query: str, parameters: Dict[str, Any] = None) -> Dict:
        """
        Execute a write Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query summary with counters
        """
        with self.session() as session:
            result = session.run(query, parameters or {})
            summary = result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }
    
    # ========================================================================
    # User Operations
    # ========================================================================
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict:
        """
        Create a User node.
        
        Args:
            user_data: User properties
            
        Returns:
            Created user data
        """
        query = """
        CREATE (u:User {
            user_id: $user_id,
            name: $name,
            wallet_address: $wallet_address,
            did: $did,
            roles: $roles,
            reputation_score: $reputation_score,
            bio: $bio,
            presence_status: $presence_status,
            last_seen: datetime(),
            created_at: datetime($created_at)
        })
        RETURN u
        """
        # Ensure presence_status has default value
        if 'presence_status' not in user_data:
            user_data['presence_status'] = 'offline'
        
        result = self.run_query(query, user_data)
        return result[0] if result else None
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """
        Get a User by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User data or None
        """
        query = """
        MATCH (u:User {user_id: $user_id})
        RETURN u
        """
        result = self.run_query(query, {"user_id": user_id})
        return result[0]["u"] if result else None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users."""
        query = """
        MATCH (u:User)
        RETURN u
        ORDER BY u.name
        """
        result = self.run_query(query)
        return [r["u"] for r in result]
    
    # ========================================================================
    # Claim Operations
    # ========================================================================
    
    def create_claim(self, claim_data: Dict[str, Any], user_id: str) -> Dict:
        """
        Create a Claim node and link to User.
        
        Args:
            claim_data: Claim properties
            user_id: Owner user ID
            
        Returns:
            Created claim data
        """
        query = """
        MATCH (u:User {user_id: $user_id})
        CREATE (c:Claim {
            claim_id: $claim_id,
            topic: $topic,
            content_summary: $content_summary,
            access_level: $access_level,
            access_tags: $access_tags,
            status: $status,
            confidence_score: $confidence_score,
            eas_uid: $eas_uid,
            attester_address: $attester_address,
            verified_at: CASE WHEN $verified_at IS NOT NULL THEN datetime($verified_at) ELSE null END,
            verified_by: $verified_by,
            expiration_date: CASE WHEN $expiration_date IS NOT NULL THEN datetime($expiration_date) ELSE null END,
            created_at: datetime($created_at),
            updated_at: datetime($updated_at)
        })
        CREATE (u)-[:MAKES_CLAIM]->(c)
        RETURN c
        """
        # Ensure access_tags has a default value
        if 'access_tags' not in claim_data:
            claim_data['access_tags'] = ['public']
        if 'expiration_date' not in claim_data:
            claim_data['expiration_date'] = None
            
        params = {**claim_data, "user_id": user_id}
        result = self.run_query(query, params)
        return result[0] if result else None
    
    def get_claims_by_user(self, user_id: str) -> List[Dict]:
        """
        Get all claims made by a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of claims
        """
        query = """
        MATCH (u:User {user_id: $user_id})-[:MAKES_CLAIM]->(c:Claim)
        RETURN c
        ORDER BY c.created_at DESC
        """
        result = self.run_query(query, {"user_id": user_id})
        return [r["c"] for r in result]
    
    def get_claim(self, claim_id: str) -> Optional[Dict]:
        """Get a claim by ID."""
        query = """
        MATCH (c:Claim {claim_id: $claim_id})
        RETURN c
        """
        result = self.run_query(query, {"claim_id": claim_id})
        return result[0]["c"] if result else None
    
    # ========================================================================
    # Entity Operations
    # ========================================================================
    
    def create_entity(self, entity_data: Dict[str, Any]) -> Dict:
        """
        Create an Entity node.
        
        Args:
            entity_data: Entity properties
            
        Returns:
            Created entity data
        """
        query = """
        CREATE (e:Entity {
            entity_id: $entity_id,
            name: $name,
            canonical_id: $canonical_id,
            entity_type: $entity_type,
            description: $description,
            aliases: $aliases
        })
        RETURN e
        """
        result = self.run_query(query, entity_data)
        return result[0] if result else None
    
    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """Get an entity by ID."""
        query = """
        MATCH (e:Entity {entity_id: $entity_id})
        RETURN e
        """
        result = self.run_query(query, {"entity_id": entity_id})
        return result[0]["e"] if result else None
    
    def get_entity_by_canonical_id(self, canonical_id: str) -> Optional[Dict]:
        """Get an entity by canonical ID."""
        query = """
        MATCH (e:Entity {canonical_id: $canonical_id})
        RETURN e
        """
        result = self.run_query(query, {"canonical_id": canonical_id})
        return result[0]["e"] if result else None
    
    def get_all_entities(self) -> List[Dict]:
        """Get all entities."""
        query = """
        MATCH (e:Entity)
        RETURN e
        ORDER BY e.name
        """
        result = self.run_query(query)
        return [r["e"] for r in result]
    
    # ========================================================================
    # Evidence Operations
    # ========================================================================
    
    def create_evidence(self, evidence_data: Dict[str, Any]) -> Dict:
        """
        Create an Evidence node.
        
        Args:
            evidence_data: Evidence properties
            
        Returns:
            Created evidence data
        """
        query = """
        CREATE (ev:Evidence {
            evidence_id: $evidence_id,
            evidence_type: $evidence_type,
            url: $url,
            file_hash: $file_hash,
            visibility: $visibility,
            description: $description
        })
        RETURN ev
        """
        result = self.run_query(query, evidence_data)
        return result[0] if result else None
    
    # ========================================================================
    # Relationship Operations
    # ========================================================================
    
    def link_claim_to_entity(self, claim_id: str, entity_canonical_id: str) -> Dict:
        """
        Create ABOUT relationship between Claim and Entity.
        
        Args:
            claim_id: Claim ID
            entity_canonical_id: Entity canonical ID
            
        Returns:
            Operation result
        """
        query = """
        MATCH (c:Claim {claim_id: $claim_id})
        MATCH (e:Entity {canonical_id: $entity_canonical_id})
        MERGE (c)-[:ABOUT]->(e)
        RETURN c, e
        """
        return self.run_write_query(query, {
            "claim_id": claim_id,
            "entity_canonical_id": entity_canonical_id
        })
    
    def link_claim_to_evidence(self, claim_id: str, evidence_id: str) -> Dict:
        """
        Create SUPPORTED_BY relationship between Claim and Evidence.
        
        Args:
            claim_id: Claim ID
            evidence_id: Evidence ID
            
        Returns:
            Operation result
        """
        query = """
        MATCH (c:Claim {claim_id: $claim_id})
        MATCH (ev:Evidence {evidence_id: $evidence_id})
        MERGE (c)-[:SUPPORTED_BY]->(ev)
        RETURN c, ev
        """
        return self.run_write_query(query, {
            "claim_id": claim_id,
            "evidence_id": evidence_id
        })
    
    def create_user_relationship(
        self, 
        from_user_id: str, 
        to_user_id: str, 
        relationship_type: str
    ) -> Dict:
        """
        Create a social relationship between users.
        
        Args:
            from_user_id: Source user ID
            to_user_id: Target user ID
            relationship_type: One of FRIEND, COLLEAGUE, RECRUITING
            
        Returns:
            Operation result
        """
        valid_types = ["FRIEND", "COLLEAGUE", "RECRUITING"]
        if relationship_type not in valid_types:
            raise ValueError(f"Invalid relationship type. Must be one of: {valid_types}")
        
        query = f"""
        MATCH (u1:User {{user_id: $from_user_id}})
        MATCH (u2:User {{user_id: $to_user_id}})
        MERGE (u1)-[:{relationship_type}]->(u2)
        RETURN u1, u2
        """
        return self.run_write_query(query, {
            "from_user_id": from_user_id,
            "to_user_id": to_user_id
        })
    
    def get_user_connections(self, user_id: str, relationship_type: str = None) -> List[Dict]:
        """
        Get all connections of a user.
        
        Args:
            user_id: User ID
            relationship_type: Optional filter by relationship type
            
        Returns:
            List of connected users with relationship info
        """
        if relationship_type:
            query = f"""
            MATCH (u:User {{user_id: $user_id}})-[r:{relationship_type}]-(connected:User)
            RETURN connected, type(r) as relationship_type
            """
        else:
            query = """
            MATCH (u:User {user_id: $user_id})-[r:FRIEND|COLLEAGUE|RECRUITING]-(connected:User)
            RETURN connected, type(r) as relationship_type
            """
        
        result = self.run_query(query, {"user_id": user_id})
        return result
    
    # ========================================================================
    # Graph Queries
    # ========================================================================
    
    def get_user_knowledge_graph(self, user_id: str) -> Dict:
        """
        Get complete knowledge graph for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with nodes and edges
        """
        query = """
        MATCH (u:User {user_id: $user_id})-[:MAKES_CLAIM]->(c:Claim)
        OPTIONAL MATCH (c)-[:ABOUT]->(e:Entity)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(ev:Evidence)
        RETURN u, collect(DISTINCT c) as claims, 
               collect(DISTINCT e) as entities,
               collect(DISTINCT ev) as evidence
        """
        result = self.run_query(query, {"user_id": user_id})
        
        if not result:
            return {"user": None, "claims": [], "entities": [], "evidence": []}
        
        return {
            "user": result[0].get("u"),
            "claims": result[0].get("claims", []),
            "entities": result[0].get("entities", []),
            "evidence": result[0].get("evidence", [])
        }
    
    def search_claims_by_entity(self, entity_name: str) -> List[Dict]:
        """
        Find all claims about a specific entity.
        
        Args:
            entity_name: Entity name to search
            
        Returns:
            List of claims with user info
        """
        query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS toLower($entity_name)
           OR ANY(alias IN e.aliases WHERE toLower(alias) CONTAINS toLower($entity_name))
        MATCH (c:Claim)-[:ABOUT]->(e)
        MATCH (u:User)-[:MAKES_CLAIM]->(c)
        RETURN c, u, e
        ORDER BY c.confidence_score DESC
        """
        return self.run_query(query, {"entity_name": entity_name})
    
    def determine_access_scope(
        self,
        viewer_id: str,
        target_id: str
    ) -> Dict[str, Any]:
        """
        Determine access scope based on relationship between viewer and target.
        
        Implements ReBAC (Relationship-based Access Control) by querying
        Neo4j for relationships and returning allowed access tags.
        
        Args:
            viewer_id: ID of the user viewing
            target_id: ID of the user whose claims are being viewed
            
        Returns:
            Dict with:
                - viewer_id: str
                - target_id: str
                - relationships: List[str] - relationship types found
                - allowed_tags: List[str] - access tags viewer can access
                - is_self: bool
        """
        # ReBAC Matrix
        REBAC_MATRIX = {
            'SELF': ['public', 'friend', 'internal', 'hr_sensitive'],
            'STRANGER': ['public'],
            'FRIEND': ['public', 'friend'],
            'COLLEAGUE': ['public', 'internal'],
            'RECRUITING': ['public', 'hr_sensitive']
        }
        
        # Check if viewer is viewing their own profile
        if viewer_id == target_id:
            return {
                "viewer_id": viewer_id,
                "target_id": target_id,
                "relationships": ["SELF"],
                "allowed_tags": REBAC_MATRIX["SELF"],
                "is_self": True
            }
        
        # Query Neo4j for relationships
        query = """
        MATCH (viewer:User {user_id: $viewer_id})-[r]-(target:User {user_id: $target_id})
        WHERE type(r) IN ['FRIEND', 'COLLEAGUE', 'RECRUITING']
        RETURN DISTINCT type(r) as relationship_type
        """
        
        results = self.run_query(query, {
            "viewer_id": viewer_id,
            "target_id": target_id
        })
        
        relationships = [r["relationship_type"] for r in results]
        
        # If no relationships found, treat as stranger
        if not relationships:
            relationships = ["STRANGER"]
        
        # Combine allowed tags from all relationships
        allowed_tags = set()
        for rel in relationships:
            tags = REBAC_MATRIX.get(rel, REBAC_MATRIX["STRANGER"])
            allowed_tags.update(tags)
        
        return {
            "viewer_id": viewer_id,
            "target_id": target_id,
            "relationships": relationships,
            "allowed_tags": list(allowed_tags),
            "is_self": False
        }
    
    def get_claims_visible_to_user(
        self, 
        viewer_id: str, 
        target_user_id: str
    ) -> List[Dict]:
        """
        Get claims visible to a viewer based on ReBAC.
        
        Implements ReBAC (Relationship-based Access Control):
        - Queries relationships between viewer and target
        - Filters claims based on access_tags
        
        Access Tag Mapping:
        - SELF: all tags
        - STRANGER: public only
        - FRIEND: public, friend
        - COLLEAGUE: public, internal
        - RECRUITING: public, hr_sensitive
        
        Args:
            viewer_id: ID of user viewing
            target_user_id: ID of user whose claims to view
            
        Returns:
            List of visible claims
        """
        query = """
        MATCH (target:User {user_id: $target_user_id})-[:MAKES_CLAIM]->(c:Claim)
        OPTIONAL MATCH (viewer:User {user_id: $viewer_id})-[friend_rel:FRIEND]-(target)
        OPTIONAL MATCH (viewer:User {user_id: $viewer_id})-[colleague_rel:COLLEAGUE]-(target)
        OPTIONAL MATCH (viewer:User {user_id: $viewer_id})-[recruiting_rel:RECRUITING]->(target)
        
        WITH c, 
             $viewer_id = $target_user_id AS is_self,
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
        result = self.run_query(query, {
            "viewer_id": viewer_id,
            "target_user_id": target_user_id
        })
        return [r["c"] for r in result]
    
    def get_claims_visible_to_user_legacy(
        self, 
        viewer_id: str, 
        target_user_id: str
    ) -> List[Dict]:
        """
        LEGACY: Get claims using old access_level field.
        
        For backward compatibility with old data format.
        
        Args:
            viewer_id: ID of user viewing
            target_user_id: ID of user whose claims to view
            
        Returns:
            List of visible claims
        """
        query = """
        MATCH (target:User {user_id: $target_user_id})-[:MAKES_CLAIM]->(c:Claim)
        OPTIONAL MATCH (viewer:User {user_id: $viewer_id})-[rel:FRIEND|COLLEAGUE]-(target)
        WITH c, 
             $viewer_id = $target_user_id AS is_owner,
             rel IS NOT NULL AS is_connected
        WHERE c.access_level = 'public'
           OR (c.access_level = 'connections_only' AND (is_owner OR is_connected))
           OR (c.access_level = 'private' AND is_owner)
        RETURN c
        ORDER BY c.created_at DESC
        """
        result = self.run_query(query, {
            "viewer_id": viewer_id,
            "target_user_id": target_user_id
        })
        return [r["c"] for r in result]
    
    # ========================================================================
    # Database Management
    # ========================================================================
    
    def clear_database(self):
        """Clear all nodes and relationships (use with caution!)."""
        query = "MATCH (n) DETACH DELETE n"
        return self.run_write_query(query)
    
    def create_constraints(self):
        """Create unique constraints for node IDs."""
        constraints = [
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
            "CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.claim_id IS UNIQUE",
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
            "CREATE CONSTRAINT entity_canonical IF NOT EXISTS FOR (e:Entity) REQUIRE e.canonical_id IS UNIQUE",
            "CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (ev:Evidence) REQUIRE ev.evidence_id IS UNIQUE",
        ]
        
        for constraint in constraints:
            try:
                self.run_write_query(constraint)
            except Exception as e:
                logger.warning(f"Constraint may already exist: {e}")
    
    def create_indexes(self):
        """Create indexes for common queries."""
        indexes = [
            "CREATE INDEX user_name IF NOT EXISTS FOR (u:User) ON (u.name)",
            "CREATE INDEX claim_status IF NOT EXISTS FOR (c:Claim) ON (c.status)",
            "CREATE INDEX claim_access IF NOT EXISTS FOR (c:Claim) ON (c.access_level)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
            # Human-First indexes
            "CREATE INDEX user_presence IF NOT EXISTS FOR (u:User) ON (u.presence_status)",
            "CREATE INDEX message_id IF NOT EXISTS FOR (m:Message) ON (m.message_id)",
            "CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
            "CREATE INDEX event_id IF NOT EXISTS FOR (e:Event) ON (e.event_id)",
            "CREATE INDEX event_status IF NOT EXISTS FOR (e:Event) ON (e.status)",
            "CREATE INDEX session_id IF NOT EXISTS FOR (s:Session) ON (s.session_id)",
        ]
        
        for index in indexes:
            try:
                self.run_write_query(index)
            except Exception as e:
                logger.warning(f"Index may already exist: {e}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        stats_query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
        node_stats = self.run_query(stats_query)
        
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        rel_stats = self.run_query(rel_query)
        
        return {
            "nodes": {r["label"]: r["count"] for r in node_stats},
            "relationships": {r["type"]: r["count"] for r in rel_stats}
        }


# ============================================================================
# Factory function
# ============================================================================

def get_neo4j_client(
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "neo4jpassword"
) -> Neo4jClient:
    """
    Get or create Neo4j client instance.
    
    Args:
        uri: Neo4j connection URI
        user: Username
        password: Password
        
    Returns:
        Neo4jClient instance
    """
    return Neo4jClient(uri, user, password)

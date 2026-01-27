#!/usr/bin/env python
"""
Discovery Agent - Bot trung gian để tìm kiếm người dùng toàn cục.

Discovery Agent thực hiện:
1. Nhận query từ người dùng (ví dụ: "Tìm người biết ReactJS")
2. Tìm kiếm qua TẤT CẢ Users dựa trên Claims PUBLIC của họ
3. Xếp hạng Users theo độ phù hợp (không truy cập dữ liệu nhạy cảm)
4. Trả về danh sách User Cards (summary, không có chi tiết nhạy cảm)

Flow:
    User Query → Discovery Agent → Global Search → Ranked User Cards
                                               → User chọn → Personal RAG

Nguyên tắc bảo mật:
- CHỈ tìm kiếm trên Claims có access_tags = ["public"]
- KHÔNG trả về thông tin nhạy cảm (salary, internal info)
- Trả về User Cards với thông tin cơ bản để user quyết định xem chi tiết

Usage:
    from utils.discovery_agent import DiscoveryAgent
    
    agent = DiscoveryAgent(neo4j_client)
    results = agent.search_users("Tìm người biết Python và RAG")
    for user_card in results:
        print(user_card)
"""

import sys
import os

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum

# Try importing from new config module, fallback to old
try:
    from config.settings import SEMANTIC_WEIGHT, CONFIDENCE_WEIGHT, FRESHNESS_WEIGHT
except ImportError:
    from config import (
        SEMANTIC_WEIGHT,
        CONFIDENCE_WEIGHT,
        FRESHNESS_WEIGHT,
    )


@dataclass
class UserCard:
    """
    User Card - Thông tin tóm tắt về User để hiển thị trong kết quả tìm kiếm.
    
    Chỉ chứa thông tin PUBLIC, không có dữ liệu nhạy cảm.
    """
    user_id: str
    name: str
    bio: str
    roles: List[str]
    reputation_score: float
    
    # Matching info
    relevance_score: float  # 0.0 - 1.0
    matched_skills: List[str]  # Skills matching query
    public_claims_count: int  # Số claims public
    verified_claims_count: int  # Số claims đã verified
    
    # Highlights - Snippets từ claims phù hợp
    highlights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "bio": self.bio,
            "roles": self.roles,
            "reputation_score": self.reputation_score,
            "relevance_score": self.relevance_score,
            "matched_skills": self.matched_skills,
            "public_claims_count": self.public_claims_count,
            "verified_claims_count": self.verified_claims_count,
            "highlights": self.highlights,
        }
    
    def __str__(self) -> str:
        """Human-readable representation."""
        skills_str = ", ".join(self.matched_skills[:5])
        roles_str = ", ".join(self.roles)
        return (
            f"┌────────────────────────────────────────────────────────────┐\n"
            f"│ {self.name} ({self.user_id})\n"
            f"│ Roles: {roles_str}\n"
            f"│ Reputation: {self.reputation_score:.2f} | Relevance: {self.relevance_score:.2f}\n"
            f"├────────────────────────────────────────────────────────────┤\n"
            f"│ Bio: {self.bio[:100]}{'...' if len(self.bio) > 100 else ''}\n"
            f"│ Matched Skills: {skills_str}\n"
            f"│ Public Claims: {self.public_claims_count} | Verified: {self.verified_claims_count}\n"
            f"└────────────────────────────────────────────────────────────┘"
        )


@dataclass
class SearchResult:
    """
    Kết quả tìm kiếm từ Discovery Agent.
    """
    query: str
    total_users_found: int
    user_cards: List[UserCard]
    search_time_ms: float
    entities_searched: List[str]  # Entities extracted từ query
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "total_users_found": self.total_users_found,
            "user_cards": [card.to_dict() for card in self.user_cards],
            "search_time_ms": self.search_time_ms,
            "entities_searched": self.entities_searched,
        }


class DiscoveryAgent:
    """
    Discovery Agent - Bot trung gian cho tìm kiếm người dùng toàn cục.
    
    Chức năng:
    - Tìm kiếm người dùng dựa trên skills/entities
    - Chỉ truy cập Claims PUBLIC
    - Trả về User Cards để user chọn xem chi tiết
    
    Example:
        >>> agent = DiscoveryAgent(neo4j_client)
        >>> result = agent.search_users("Tìm người biết Python và RAG")
        >>> for card in result.user_cards:
        ...     print(card)
    """
    
    # Mapping keywords phổ biến -> Entity canonical_id
    SKILL_KEYWORDS = {
        # Python ecosystem
        "python": "tech_python",
        "py": "tech_python",
        "fastapi": "framework_fastapi",
        "fast api": "framework_fastapi",
        "django": "framework_django",
        
        # JavaScript ecosystem
        "javascript": "tech_javascript",
        "js": "tech_javascript",
        "typescript": "tech_typescript",
        "ts": "tech_typescript",
        "react": "framework_react",
        "reactjs": "framework_react",
        "react.js": "framework_react",
        "nextjs": "framework_nextjs",
        "next.js": "framework_nextjs",
        "next": "framework_nextjs",
        "nodejs": "framework_nodejs",
        "node.js": "framework_nodejs",
        "node": "framework_nodejs",
        "tailwind": "framework_tailwind",
        "tailwindcss": "framework_tailwind",
        
        # AI/ML
        "machine learning": "skill_ml",
        "ml": "skill_ml",
        "ai": "skill_ml",
        "nlp": "skill_nlp",
        "natural language processing": "skill_nlp",
        "langchain": "lib_langchain",
        "rag": "skill_rag",
        "retrieval augmented generation": "skill_rag",
        "openai": "lib_openai",
        "gpt": "lib_openai",
        "chatgpt": "lib_openai",
        
        # Cloud & DevOps
        "aws": "cloud_aws",
        "amazon web services": "cloud_aws",
        "docker": "devops_docker",
        "kubernetes": "devops_k8s",
        "k8s": "devops_k8s",
        
        # UI/UX
        "ui": "skill_uiux",
        "ux": "skill_uiux",
        "ui/ux": "skill_uiux",
        "figma": "tool_figma",
        "design": "skill_uiux",
    }
    
    def __init__(self, neo4j_client):
        """
        Initialize Discovery Agent.
        
        Args:
            neo4j_client: Neo4j client instance
        """
        self.client = neo4j_client
    
    def extract_entities_from_query(self, query: str) -> List[str]:
        """
        Trích xuất entity canonical IDs từ query text.
        
        Args:
            query: User query (e.g., "Tìm người biết Python và React")
            
        Returns:
            List of entity canonical IDs
        """
        query_lower = query.lower()
        found_entities = []
        
        # Check từng keyword
        for keyword, canonical_id in self.SKILL_KEYWORDS.items():
            if keyword in query_lower:
                if canonical_id not in found_entities:
                    found_entities.append(canonical_id)
        
        return found_entities
    
    def search_users(
        self,
        query: str,
        limit: int = 10,
        min_relevance: float = 0.1
    ) -> SearchResult:
        """
        Tìm kiếm người dùng dựa trên query.
        
        Args:
            query: Search query (e.g., "Tìm developer biết ReactJS")
            limit: Số lượng kết quả tối đa
            min_relevance: Ngưỡng relevance score tối thiểu
            
        Returns:
            SearchResult với danh sách UserCards
        """
        import time
        start_time = time.time()
        
        # 1. Extract entities từ query
        entity_ids = self.extract_entities_from_query(query)
        
        if not entity_ids:
            # Không tìm thấy skill cụ thể, tìm kiếm full-text
            return self._fulltext_search(query, limit, start_time)
        
        # 2. Tìm users có claims liên kết với entities
        user_cards = self._search_by_entities(entity_ids, limit)
        
        # 3. Filter by min_relevance
        user_cards = [c for c in user_cards if c.relevance_score >= min_relevance]
        
        # 4. Sort by relevance
        user_cards.sort(key=lambda x: x.relevance_score, reverse=True)
        
        search_time = (time.time() - start_time) * 1000
        
        return SearchResult(
            query=query,
            total_users_found=len(user_cards),
            user_cards=user_cards[:limit],
            search_time_ms=round(search_time, 2),
            entities_searched=entity_ids,
        )
    
    def _search_by_entities(
        self,
        entity_ids: List[str],
        limit: int
    ) -> List[UserCard]:
        """
        Tìm users dựa trên entity IDs.
        
        QUAN TRỌNG: Chỉ tìm trên Claims PUBLIC.
        """
        # Cypher query: Tìm users có claims PUBLIC liên kết với entities
        cypher = """
        MATCH (u:User)-[:MAKES_CLAIM]->(c:Claim)-[:ABOUT]->(e:Entity)
        WHERE e.canonical_id IN $entity_ids
          AND 'public' IN c.access_tags
        WITH u, c, e,
             CASE WHEN c.status = 'attested' THEN 1 ELSE 0 END AS is_verified
        WITH u, 
             collect(DISTINCT e.name) AS matched_skills,
             collect(DISTINCT c) AS claims,
             sum(is_verified) AS verified_count,
             count(DISTINCT c) AS claim_count
        RETURN u.user_id AS user_id,
               u.name AS name,
               u.bio AS bio,
               u.roles AS roles,
               u.reputation_score AS reputation_score,
               matched_skills,
               claim_count,
               verified_count,
               [c IN claims | c.content_summary][0..3] AS highlights
        ORDER BY verified_count DESC, claim_count DESC
        LIMIT $limit
        """
        
        with self.client.driver.session() as session:
            result = session.run(cypher, entity_ids=entity_ids, limit=limit * 2)
            records = list(result)
        
        # Build UserCards
        user_cards = []
        total_entities = len(entity_ids)
        
        for record in records:
            matched_skills = record["matched_skills"] or []
            claim_count = record["claim_count"] or 0
            verified_count = record["verified_count"] or 0
            reputation = record["reputation_score"] or 0.0
            
            # Calculate relevance score
            # - Số skills matched / tổng skills searched
            # - Boost nếu có verified claims
            # - Boost theo reputation
            skill_match_ratio = len(matched_skills) / total_entities if total_entities > 0 else 0
            verified_ratio = verified_count / max(claim_count, 1)
            
            relevance = (
                0.5 * skill_match_ratio +  # 50% weight cho skill match
                0.3 * verified_ratio +      # 30% weight cho verified
                0.2 * reputation            # 20% weight cho reputation
            )
            
            user_cards.append(UserCard(
                user_id=record["user_id"],
                name=record["name"],
                bio=record["bio"] or "",
                roles=record["roles"] or [],
                reputation_score=reputation,
                relevance_score=round(relevance, 3),
                matched_skills=matched_skills,
                public_claims_count=claim_count,
                verified_claims_count=verified_count,
                highlights=record["highlights"] or [],
            ))
        
        return user_cards
    
    def _fulltext_search(
        self,
        query: str,
        limit: int,
        start_time: float
    ) -> SearchResult:
        """
        Fallback: Full-text search trên bio và claim content.
        
        QUAN TRỌNG: Chỉ tìm trên Claims PUBLIC.
        """
        # Simplified search - match query terms trong bio hoặc claim content
        search_terms = query.lower().split()
        
        cypher = """
        MATCH (u:User)
        OPTIONAL MATCH (u)-[:MAKES_CLAIM]->(c:Claim)
        WHERE 'public' IN c.access_tags
        WITH u, collect(c) AS claims
        WHERE u.bio IS NOT NULL
        RETURN u.user_id AS user_id,
               u.name AS name,
               u.bio AS bio,
               u.roles AS roles,
               u.reputation_score AS reputation_score,
               size(claims) AS claim_count,
               size([c IN claims WHERE c.status = 'attested']) AS verified_count
        LIMIT $limit
        """
        
        with self.client.driver.session() as session:
            result = session.run(cypher, limit=limit * 2)
            records = list(result)
        
        # Filter and score based on text matching
        user_cards = []
        
        for record in records:
            bio = (record["bio"] or "").lower()
            
            # Count matching terms
            matches = sum(1 for term in search_terms if term in bio)
            if matches == 0:
                continue
            
            relevance = matches / len(search_terms) if search_terms else 0
            
            user_cards.append(UserCard(
                user_id=record["user_id"],
                name=record["name"],
                bio=record["bio"] or "",
                roles=record["roles"] or [],
                reputation_score=record["reputation_score"] or 0.0,
                relevance_score=round(relevance, 3),
                matched_skills=[],
                public_claims_count=record["claim_count"] or 0,
                verified_claims_count=record["verified_count"] or 0,
                highlights=[],
            ))
        
        import time
        search_time = (time.time() - start_time) * 1000
        
        user_cards.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return SearchResult(
            query=query,
            total_users_found=len(user_cards),
            user_cards=user_cards[:limit],
            search_time_ms=round(search_time, 2),
            entities_searched=[],
        )
    
    def get_user_summary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin tóm tắt PUBLIC của một user.
        
        Được gọi khi user click vào một User Card.
        
        Args:
            user_id: ID của user cần xem
            
        Returns:
            Dictionary với thông tin user (chỉ PUBLIC data)
        """
        cypher = """
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[:MAKES_CLAIM]->(c:Claim)
        WHERE 'public' IN c.access_tags
        OPTIONAL MATCH (c)-[:ABOUT]->(e:Entity)
        WITH u, collect(DISTINCT c) AS claims, collect(DISTINCT e.name) AS skills
        RETURN u.user_id AS user_id,
               u.name AS name,
               u.bio AS bio,
               u.roles AS roles,
               u.reputation_score AS reputation_score,
               u.created_at AS created_at,
               size(claims) AS public_claims,
               size([c IN claims WHERE c.status = 'attested']) AS verified_claims,
               skills,
               [c IN claims | {
                   topic: c.topic,
                   summary: c.content_summary,
                   status: c.status,
                   confidence: c.confidence_score
               }][0..5] AS sample_claims
        """
        
        with self.client.driver.session() as session:
            result = session.run(cypher, user_id=user_id)
            record = result.single()
        
        if not record:
            return None
        
        return {
            "user_id": record["user_id"],
            "name": record["name"],
            "bio": record["bio"],
            "roles": record["roles"],
            "reputation_score": record["reputation_score"],
            "created_at": record["created_at"],
            "public_claims": record["public_claims"],
            "verified_claims": record["verified_claims"],
            "skills": record["skills"],
            "sample_claims": record["sample_claims"],
        }
    
    def list_available_skills(self) -> List[Dict[str, Any]]:
        """
        Liệt kê tất cả skills có trong hệ thống.
        
        Useful cho autocomplete trong search box.
        """
        cypher = """
        MATCH (e:Entity)
        WHERE e.entity_type = 'Skill'
        OPTIONAL MATCH (c:Claim)-[:ABOUT]->(e)
        WHERE 'public' IN c.access_tags
        WITH e, count(c) AS usage_count
        RETURN e.name AS name,
               e.canonical_id AS id,
               e.description AS description,
               e.aliases AS aliases,
               usage_count
        ORDER BY usage_count DESC
        """
        
        with self.client.driver.session() as session:
            result = session.run(cypher)
            return [dict(record) for record in result]
    
    def suggest_users_for_recruiter(
        self,
        recruiter_id: str,
        required_skills: List[str],
        limit: int = 10
    ) -> List[UserCard]:
        """
        Đề xuất users cho Recruiter dựa trên skills yêu cầu.
        
        Đặc biệt cho Recruiter: Có thể xem Claims với access_tag = "hr_sensitive"
        cho những users mà họ đang RECRUITING.
        
        Args:
            recruiter_id: ID của recruiter
            required_skills: List entity IDs của skills cần tìm
            limit: Số lượng kết quả
            
        Returns:
            List of UserCards với thông tin phù hợp cho recruiter
        """
        # Kiểm tra xem user có phải Recruiter không
        recruiter = self._get_user_roles(recruiter_id)
        if not recruiter or "Recruiter" not in recruiter.get("roles", []):
            # Không phải recruiter, chỉ trả về public data
            return self._search_by_entities(required_skills, limit)
        
        # Recruiter query - có thể thấy hr_sensitive cho users đang recruiting
        cypher = """
        MATCH (recruiter:User {user_id: $recruiter_id})-[:RECRUITING]->(u:User)
        MATCH (u)-[:MAKES_CLAIM]->(c:Claim)-[:ABOUT]->(e:Entity)
        WHERE e.canonical_id IN $skills
          AND ('public' IN c.access_tags OR 'hr_sensitive' IN c.access_tags)
        WITH u, c, e,
             CASE WHEN c.status = 'attested' THEN 1 ELSE 0 END AS is_verified,
             CASE WHEN 'hr_sensitive' IN c.access_tags THEN true ELSE false END AS has_hr_info
        WITH u,
             collect(DISTINCT e.name) AS matched_skills,
             collect(DISTINCT c) AS claims,
             sum(is_verified) AS verified_count,
             count(DISTINCT c) AS claim_count,
             max(CASE WHEN has_hr_info THEN 1 ELSE 0 END) AS has_salary_info
        RETURN u.user_id AS user_id,
               u.name AS name,
               u.bio AS bio,
               u.roles AS roles,
               u.reputation_score AS reputation_score,
               matched_skills,
               claim_count,
               verified_count,
               has_salary_info,
               [c IN claims | c.content_summary][0..3] AS highlights
        ORDER BY verified_count DESC, claim_count DESC
        LIMIT $limit
        """
        
        with self.client.driver.session() as session:
            result = session.run(
                cypher,
                recruiter_id=recruiter_id,
                skills=required_skills,
                limit=limit
            )
            records = list(result)
        
        user_cards = []
        total_skills = len(required_skills)
        
        for record in records:
            matched_skills = record["matched_skills"] or []
            claim_count = record["claim_count"] or 0
            verified_count = record["verified_count"] or 0
            reputation = record["reputation_score"] or 0.0
            
            skill_match_ratio = len(matched_skills) / total_skills if total_skills > 0 else 0
            verified_ratio = verified_count / max(claim_count, 1)
            
            relevance = (
                0.5 * skill_match_ratio +
                0.3 * verified_ratio +
                0.2 * reputation
            )
            
            # Add indicator if salary info is available
            highlights = record["highlights"] or []
            if record["has_salary_info"]:
                highlights.append("💰 Salary expectation available")
            
            user_cards.append(UserCard(
                user_id=record["user_id"],
                name=record["name"],
                bio=record["bio"] or "",
                roles=record["roles"] or [],
                reputation_score=reputation,
                relevance_score=round(relevance, 3),
                matched_skills=matched_skills,
                public_claims_count=claim_count,
                verified_claims_count=verified_count,
                highlights=highlights,
            ))
        
        return user_cards
    
    def _get_user_roles(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user roles for permission checking."""
        cypher = "MATCH (u:User {user_id: $user_id}) RETURN u.roles AS roles"
        
        with self.client.driver.session() as session:
            result = session.run(cypher, user_id=user_id)
            record = result.single()
        
        return dict(record) if record else None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_discovery_agent():
    """
    Factory function để tạo DiscoveryAgent với default Neo4j client.
    
    Returns:
        DiscoveryAgent instance
    """
    from utils.neo4j_client import get_neo4j_client
    client = get_neo4j_client()
    return DiscoveryAgent(client)


# ============================================================================
# CLI & TESTING
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("🔍 Discovery Agent - Demo")
    print("=" * 60)
    
    try:
        agent = create_discovery_agent()
        
        # Test queries
        test_queries = [
            "Tìm developer biết Python và RAG",
            "Cần người biết ReactJS và TypeScript",
            "Tìm người có kinh nghiệm FastAPI",
        ]
        
        for query in test_queries:
            print(f"\n🔎 Query: {query}")
            print("-" * 50)
            
            result = agent.search_users(query, limit=3)
            
            print(f"Found: {result.total_users_found} users")
            print(f"Entities: {result.entities_searched}")
            print(f"Time: {result.search_time_ms}ms")
            
            for card in result.user_cards:
                print()
                print(card)
        
        # Test available skills
        print("\n\n📚 Available Skills:")
        print("-" * 50)
        skills = agent.list_available_skills()
        for skill in skills[:10]:
            print(f"  - {skill['name']} ({skill['id']}): {skill['usage_count']} claims")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

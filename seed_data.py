#!/usr/bin/env python
# seed_data.py - Script khởi tạo dữ liệu Neo4j cho RAG Application
"""
Script seed data cho Neo4j Graph Database.

Chức năng:
- Khởi tạo Graph với constraints và indexes
- Tạo sample Users, Claims, Entities, Evidence
- Tạo các mối quan hệ xã hội (FRIEND, COLLEAGUE, RECRUITING)
- Liên kết Claims với Entities và Evidence

Usage:
    python seed_data.py [--clear] [--uri URI] [--user USER] [--password PASSWORD]
    
Options:
    --clear     Xóa toàn bộ dữ liệu trước khi seed
    --uri       Neo4j connection URI (default: bolt://localhost:7687)
    --user      Neo4j username (default: neo4j)
    --password  Neo4j password (default: neo4jpassword)
"""

import argparse
import sys
from datetime import datetime
from typing import List, Dict

from utils.neo4j_client import get_neo4j_client, Neo4jClient


# ============================================================================
# SAMPLE DATA
# ============================================================================

SAMPLE_USERS: List[Dict] = [
    # ========== GOBY - Python/RAG Specialist ==========
    {
        "user_id": "goby",
        "name": "Goby",
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "did": "did:pkh:0x1234567890abcdef1234567890abcdef12345678",
        "roles": ["Freelancer"],
        "reputation_score": 0.85,
        "bio": "Full-stack Python Developer với 5 năm kinh nghiệm. Chuyên về AI/ML, RAG systems, và Backend Development với FastAPI, Django. Đam mê xây dựng các hệ thống thông minh.",
        "presence_status": "offline",
        "created_at": "2024-01-15T10:00:00"
    },
    # ========== ALICE - React/Frontend Expert ==========
    {
        "user_id": "alice",
        "name": "Alice Nguyen",
        "wallet_address": "0xabcdef1234567890abcdef1234567890abcdef12",
        "did": "did:pkh:0xabcdef1234567890abcdef1234567890abcdef12",
        "roles": ["Freelancer"],
        "reputation_score": 0.80,
        "bio": "Senior Frontend Developer chuyên React, TypeScript và Next.js. 4 năm kinh nghiệm xây dựng UI/UX cho các startup công nghệ. Yêu thích design systems và accessibility.",
        "presence_status": "offline",
        "created_at": "2024-02-10T14:30:00"
    },
    # ========== BOB - Recruiter ==========
    {
        "user_id": "bob",
        "name": "Bob Tran",
        "wallet_address": "0x9999888877776666555544443333222211110000",
        "did": "did:pkh:0x9999888877776666555544443333222211110000",
        "roles": ["Recruiter"],
        "reputation_score": 0.70,
        "bio": "Technical Recruiter tại TechCorp Vietnam với 6 năm kinh nghiệm. Chuyên tìm kiếm talent trong lĩnh vực AI, Web Development và Blockchain.",
        "presence_status": "offline",
        "created_at": "2024-03-01T09:00:00"
    },
    # ========== ORGANIZATIONS ==========
    {
        "user_id": "org_techcorp",
        "name": "TechCorp Vietnam",
        "wallet_address": "0x9876543210fedcba9876543210fedcba98765432",
        "did": "did:pkh:0x9876543210fedcba9876543210fedcba98765432",
        "roles": ["Organization", "Verifier"],
        "reputation_score": 1.0,
        "bio": "Công ty công nghệ hàng đầu Vietnam, chuyên về AI/ML solutions và Blockchain development.",
        "presence_status": "offline",
        "created_at": "2023-06-01T00:00:00"
    },
    {
        "user_id": "org_fpt",
        "name": "FPT Software",
        "wallet_address": "0xaaaa111122223333444455556666777788889999",
        "did": "did:pkh:0xaaaa111122223333444455556666777788889999",
        "roles": ["Organization", "Verifier"],
        "reputation_score": 0.95,
        "bio": "Công ty phần mềm và dịch vụ CNTT hàng đầu Việt Nam với hơn 30,000 nhân viên toàn cầu.",
        "presence_status": "offline",
        "created_at": "2023-01-01T00:00:00"
    }
]

SAMPLE_ENTITIES: List[Dict] = [
    # Programming Languages
    {"entity_id": "ent_001", "name": "Python", "canonical_id": "tech_python", "entity_type": "Skill", "description": "Python programming language - versatile, high-level", "aliases": ["Py", "Python 3", "Python3"]},
    {"entity_id": "ent_002", "name": "JavaScript", "canonical_id": "tech_javascript", "entity_type": "Skill", "description": "JavaScript programming language", "aliases": ["JS", "ECMAScript"]},
    {"entity_id": "ent_003", "name": "TypeScript", "canonical_id": "tech_typescript", "entity_type": "Skill", "description": "Typed superset of JavaScript", "aliases": ["TS"]},
    
    # Frontend Frameworks
    {"entity_id": "ent_004", "name": "React", "canonical_id": "framework_react", "entity_type": "Skill", "description": "JavaScript library for building UIs", "aliases": ["ReactJS", "React.js"]},
    {"entity_id": "ent_005", "name": "Next.js", "canonical_id": "framework_nextjs", "entity_type": "Skill", "description": "React framework for production", "aliases": ["Next", "NextJS"]},
    {"entity_id": "ent_006", "name": "TailwindCSS", "canonical_id": "framework_tailwind", "entity_type": "Skill", "description": "Utility-first CSS framework", "aliases": ["Tailwind"]},
    
    # Backend Frameworks
    {"entity_id": "ent_007", "name": "FastAPI", "canonical_id": "framework_fastapi", "entity_type": "Skill", "description": "Modern Python web framework for APIs", "aliases": ["Fast API"]},
    {"entity_id": "ent_008", "name": "Django", "canonical_id": "framework_django", "entity_type": "Skill", "description": "High-level Python web framework", "aliases": []},
    {"entity_id": "ent_009", "name": "Node.js", "canonical_id": "framework_nodejs", "entity_type": "Skill", "description": "JavaScript runtime built on Chrome's V8", "aliases": ["Node", "NodeJS"]},
    
    # AI/ML
    {"entity_id": "ent_010", "name": "Machine Learning", "canonical_id": "skill_ml", "entity_type": "Skill", "description": "ML - Study of algorithms that improve through experience", "aliases": ["ML"]},
    {"entity_id": "ent_011", "name": "Natural Language Processing", "canonical_id": "skill_nlp", "entity_type": "Skill", "description": "NLP - AI focused on human language", "aliases": ["NLP"]},
    {"entity_id": "ent_012", "name": "LangChain", "canonical_id": "lib_langchain", "entity_type": "Skill", "description": "Framework for LLM applications", "aliases": []},
    {"entity_id": "ent_013", "name": "RAG", "canonical_id": "skill_rag", "entity_type": "Skill", "description": "Retrieval-Augmented Generation for LLMs", "aliases": ["Retrieval-Augmented Generation"]},
    {"entity_id": "ent_014", "name": "OpenAI", "canonical_id": "lib_openai", "entity_type": "Skill", "description": "OpenAI API and GPT models", "aliases": ["GPT", "ChatGPT", "GPT-4"]},
    
    # Cloud & DevOps
    {"entity_id": "ent_015", "name": "AWS", "canonical_id": "cloud_aws", "entity_type": "Skill", "description": "Amazon Web Services cloud platform", "aliases": ["Amazon Web Services"]},
    {"entity_id": "ent_016", "name": "Docker", "canonical_id": "devops_docker", "entity_type": "Skill", "description": "Container platform", "aliases": []},
    
    # UI/UX
    {"entity_id": "ent_017", "name": "UI/UX Design", "canonical_id": "skill_uiux", "entity_type": "Skill", "description": "User Interface and User Experience Design", "aliases": ["UI Design", "UX Design"]},
    {"entity_id": "ent_018", "name": "Figma", "canonical_id": "tool_figma", "entity_type": "Skill", "description": "Collaborative design tool", "aliases": []},
    
    # Organizations
    {"entity_id": "ent_019", "name": "TechCorp Vietnam", "canonical_id": "org_techcorp", "entity_type": "Organization", "description": "Technology company in Vietnam", "aliases": ["TechCorp"]},
    {"entity_id": "ent_020", "name": "FPT Software", "canonical_id": "org_fpt", "entity_type": "Organization", "description": "Leading IT company in Vietnam", "aliases": ["FPT"]},
    
    # Certifications
    {"entity_id": "ent_021", "name": "AWS Solutions Architect", "canonical_id": "cert_aws_sa", "entity_type": "Certificate", "description": "AWS Solutions Architect certification", "aliases": ["AWS SA"]},
]

SAMPLE_EVIDENCE: List[Dict] = [
    # Goby's evidence
    {"evidence_id": "ev_goby_001", "evidence_type": "GithubRepo", "url": "https://github.com/goby/rag-system", "file_hash": None, "visibility": "public", "description": "RAG System project với LangChain và FAISS"},
    {"evidence_id": "ev_goby_002", "evidence_type": "GithubRepo", "url": "https://github.com/goby/fastapi-microservices", "file_hash": None, "visibility": "public", "description": "Microservices architecture với FastAPI"},
    {"evidence_id": "ev_goby_003", "evidence_type": "Certificate", "url": "https://aws.amazon.com/certification/verify/ABC123", "file_hash": None, "visibility": "public", "description": "AWS Solutions Architect Associate Certificate"},
    
    # Alice's evidence
    {"evidence_id": "ev_alice_001", "evidence_type": "GithubRepo", "url": "https://github.com/alice/react-dashboard", "file_hash": None, "visibility": "public", "description": "React Dashboard với TypeScript và TailwindCSS"},
    {"evidence_id": "ev_alice_002", "evidence_type": "GithubRepo", "url": "https://github.com/alice/nextjs-ecommerce", "file_hash": None, "visibility": "public", "description": "E-commerce platform với Next.js"},
    {"evidence_id": "ev_alice_003", "evidence_type": "Link", "url": "https://dribbble.com/alice-designs", "file_hash": None, "visibility": "public", "description": "Portfolio UI/UX designs trên Dribbble"},
]

SAMPLE_CLAIMS: List[Dict] = [
    # ========================================================================
    # GOBY's RAG - Python/AI Specialist (6 claims)
    # ========================================================================
    
    # Claim 1: Python skills (PUBLIC, VERIFIED, FRESH)
    {
        "claim_id": "goby_claim_001", "user_id": "goby", "topic": "Skill Proficiency",
        "content_summary": "Goby có 5 năm kinh nghiệm lập trình Python, thành thạo xây dựng backend services với FastAPI và Django. Đã phát triển nhiều REST APIs phục vụ hàng nghìn users.",
        "access_level": "public", "access_tags": ["public"],
        "status": "attested", "confidence_score": 0.95,
        "eas_uid": "0xgoby_python_attestation", "attester_address": "0x9876543210fedcba9876543210fedcba98765432",
        "verified_at": "2025-11-01T10:00:00", "verified_by": "org_techcorp",
        "expiration_date": None,
        "entity_ids": ["tech_python", "framework_fastapi", "framework_django"],
        "evidence_ids": ["ev_goby_002"],
        "created_at": "2025-01-15T10:00:00", "updated_at": "2025-11-01T10:00:00"
    },
    # Claim 2: RAG/AI expertise (PUBLIC, FRESH)
    {
        "claim_id": "goby_claim_002", "user_id": "goby", "topic": "Skill Proficiency",
        "content_summary": "Goby chuyên về xây dựng hệ thống RAG (Retrieval-Augmented Generation). Đã triển khai thành công chatbot AI sử dụng LangChain, OpenAI GPT-4, và FAISS vector database với độ chính xác 95%.",
        "access_level": "public", "access_tags": ["public"],
        "status": "self_declared", "confidence_score": 0.6,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": None,
        "entity_ids": ["skill_rag", "lib_langchain", "skill_nlp", "skill_ml"],
        "evidence_ids": ["ev_goby_001"],
        "created_at": "2025-10-01T09:00:00", "updated_at": "2025-10-01T09:00:00"
    },
    # Claim 3: Work Experience at TechCorp (INTERNAL - for colleagues)
    {
        "claim_id": "goby_claim_003", "user_id": "goby", "topic": "Work Experience",
        "content_summary": "Goby đã làm việc tại TechCorp Vietnam từ 2022-2024 với vai trò Senior Backend Developer. Phụ trách thiết kế microservices architecture cho hệ thống e-commerce có 50,000 users.",
        "access_level": "connections_only", "access_tags": ["internal", "friend"],
        "status": "attested", "confidence_score": 1.0,
        "eas_uid": "0xgoby_techcorp_work", "attester_address": "0x9876543210fedcba9876543210fedcba98765432",
        "verified_at": "2025-06-15T10:00:00", "verified_by": "org_techcorp",
        "expiration_date": None,
        "entity_ids": ["org_techcorp"],
        "evidence_ids": [],
        "created_at": "2025-01-20T10:00:00", "updated_at": "2025-06-15T10:00:00"
    },
    # Claim 4: Salary (HR_SENSITIVE - only for recruiters)
    {
        "claim_id": "goby_claim_004", "user_id": "goby", "topic": "Compensation",
        "content_summary": "Mức lương mong muốn của Goby là $3,000-4,000/tháng cho vị trí Senior Backend Developer hoặc AI Engineer. Sẵn sàng thương lượng cho các dự án thú vị.",
        "access_level": "recruiter", "access_tags": ["hr_sensitive"],
        "status": "self_declared", "confidence_score": 0.5,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": None,
        "entity_ids": [],
        "evidence_ids": [],
        "created_at": "2025-12-01T10:00:00", "updated_at": "2025-12-01T10:00:00"
    },
    # Claim 5: AWS Cert (PUBLIC, with expiration)
    {
        "claim_id": "goby_claim_005", "user_id": "goby", "topic": "Certification",
        "content_summary": "Goby đã đạt chứng chỉ AWS Solutions Architect Associate vào tháng 6/2024, chứng minh khả năng thiết kế và triển khai hệ thống cloud-native trên AWS.",
        "access_level": "public", "access_tags": ["public", "hr_sensitive"],
        "status": "self_declared", "confidence_score": 0.6,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": "2027-06-15T23:59:59",
        "entity_ids": ["cert_aws_sa", "cloud_aws"],
        "evidence_ids": ["ev_goby_003"],
        "created_at": "2024-06-15T10:00:00", "updated_at": "2024-06-15T10:00:00"
    },
    # Claim 6: OLD claim for temporal decay testing (2 years old)
    {
        "claim_id": "goby_claim_006", "user_id": "goby", "topic": "Education",
        "content_summary": "Goby đã hoàn thành khóa Machine Learning Specialization trên Coursera (Andrew Ng) vào năm 2022.",
        "access_level": "public", "access_tags": ["public"],
        "status": "self_declared", "confidence_score": 0.4,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": None,
        "entity_ids": ["skill_ml"],
        "evidence_ids": [],
        "created_at": "2022-08-01T10:00:00", "updated_at": "2022-08-01T10:00:00"
    },
    
    # ========================================================================
    # ALICE's RAG - React/Frontend Expert (6 claims)
    # ========================================================================
    
    # Claim 1: React skills (PUBLIC, VERIFIED, FRESH)
    {
        "claim_id": "alice_claim_001", "user_id": "alice", "topic": "Skill Proficiency",
        "content_summary": "Alice có 4 năm kinh nghiệm với React và TypeScript. Thành thạo xây dựng SPA, state management (Redux, Zustand), và modern React patterns như hooks và suspense.",
        "access_level": "public", "access_tags": ["public"],
        "status": "attested", "confidence_score": 0.9,
        "eas_uid": "0xalice_react_attestation", "attester_address": "0x9876543210fedcba9876543210fedcba98765432",
        "verified_at": "2025-10-15T10:00:00", "verified_by": "org_techcorp",
        "expiration_date": None,
        "entity_ids": ["framework_react", "tech_typescript", "tech_javascript"],
        "evidence_ids": ["ev_alice_001"],
        "created_at": "2025-02-10T10:00:00", "updated_at": "2025-10-15T10:00:00"
    },
    # Claim 2: Next.js & Full-stack (PUBLIC, FRESH)
    {
        "claim_id": "alice_claim_002", "user_id": "alice", "topic": "Skill Proficiency",
        "content_summary": "Alice có kinh nghiệm xây dựng ứng dụng production với Next.js 14+, bao gồm SSR, ISR, và App Router. Đã phát triển e-commerce platform phục vụ 10,000+ users.",
        "access_level": "public", "access_tags": ["public", "friend"],
        "status": "self_declared", "confidence_score": 0.6,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": None,
        "entity_ids": ["framework_nextjs", "framework_react"],
        "evidence_ids": ["ev_alice_002"],
        "created_at": "2025-09-20T10:00:00", "updated_at": "2025-09-20T10:00:00"
    },
    # Claim 3: UI/UX Design (PUBLIC)
    {
        "claim_id": "alice_claim_003", "user_id": "alice", "topic": "Skill Proficiency",
        "content_summary": "Alice có kỹ năng UI/UX design với Figma. Có thể thiết kế và implement design systems, component libraries với TailwindCSS và Storybook.",
        "access_level": "public", "access_tags": ["public"],
        "status": "self_declared", "confidence_score": 0.5,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": None,
        "entity_ids": ["skill_uiux", "tool_figma", "framework_tailwind"],
        "evidence_ids": ["ev_alice_003"],
        "created_at": "2025-08-01T10:00:00", "updated_at": "2025-08-01T10:00:00"
    },
    # Claim 4: Previous work (INTERNAL)
    {
        "claim_id": "alice_claim_004", "user_id": "alice", "topic": "Work Experience",
        "content_summary": "Alice đã làm Frontend Developer tại FPT Software từ 2021-2023. Phụ trách phát triển dashboard analytics cho khách hàng enterprise.",
        "access_level": "connections_only", "access_tags": ["internal"],
        "status": "attested", "confidence_score": 0.9,
        "eas_uid": "0xalice_fpt_work", "attester_address": "0xfpt_verifier",
        "verified_at": "2023-12-01T10:00:00", "verified_by": "org_fpt",
        "expiration_date": None,
        "entity_ids": ["org_fpt"],
        "evidence_ids": [],
        "created_at": "2023-06-01T10:00:00", "updated_at": "2023-12-01T10:00:00"
    },
    # Claim 5: Salary expectation (HR_SENSITIVE)
    {
        "claim_id": "alice_claim_005", "user_id": "alice", "topic": "Compensation",
        "content_summary": "Alice mong muốn mức lương $2,500-3,500/tháng cho vị trí Senior Frontend Developer. Ưu tiên remote work hoặc hybrid.",
        "access_level": "recruiter", "access_tags": ["hr_sensitive"],
        "status": "self_declared", "confidence_score": 0.5,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": None,
        "entity_ids": [],
        "evidence_ids": [],
        "created_at": "2025-11-15T10:00:00", "updated_at": "2025-11-15T10:00:00"
    },
    # Claim 6: OLD claim for temporal decay (3 years old)
    {
        "claim_id": "alice_claim_006", "user_id": "alice", "topic": "Education",
        "content_summary": "Alice đã học JavaScript bootcamp tại CodeGym Vietnam năm 2021.",
        "access_level": "public", "access_tags": ["public"],
        "status": "self_declared", "confidence_score": 0.3,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": None,
        "entity_ids": ["tech_javascript"],
        "evidence_ids": [],
        "created_at": "2021-06-01T10:00:00", "updated_at": "2021-06-01T10:00:00"
    },
    
    # ========================================================================
    # BOB's RAG - Recruiter (2 claims)
    # ========================================================================
    
    # Claim 1: Recruiting experience (PUBLIC)
    {
        "claim_id": "bob_claim_001", "user_id": "bob", "topic": "Work Experience",
        "content_summary": "Bob là Technical Recruiter với 6 năm kinh nghiệm. Chuyên tìm kiếm và đánh giá talent trong lĩnh vực AI, Web Development, và Blockchain.",
        "access_level": "public", "access_tags": ["public"],
        "status": "attested", "confidence_score": 0.85,
        "eas_uid": "0xbob_recruiter_attestation", "attester_address": "0x9876543210fedcba9876543210fedcba98765432",
        "verified_at": "2025-08-01T10:00:00", "verified_by": "org_techcorp",
        "expiration_date": None,
        "entity_ids": ["org_techcorp"],
        "evidence_ids": [],
        "created_at": "2024-03-01T10:00:00", "updated_at": "2025-08-01T10:00:00"
    },
    # Claim 2: Current hiring needs (PUBLIC)
    {
        "claim_id": "bob_claim_002", "user_id": "bob", "topic": "Hiring",
        "content_summary": "Bob đang tìm kiếm Senior Python Developer và React Developer cho các vị trí tại TechCorp Vietnam. Budget $2,500-4,500/tháng.",
        "access_level": "public", "access_tags": ["public"],
        "status": "self_declared", "confidence_score": 0.5,
        "eas_uid": None, "attester_address": None, "verified_at": None, "verified_by": None,
        "expiration_date": "2026-06-30T23:59:59",
        "entity_ids": ["tech_python", "framework_react", "org_techcorp"],
        "evidence_ids": [],
        "created_at": "2025-12-01T10:00:00", "updated_at": "2025-12-01T10:00:00"
    },
]

# Social relationships
SAMPLE_RELATIONSHIPS = [
    # Bob is RECRUITING Goby and Alice
    {"from": "bob", "to": "goby", "type": "RECRUITING"},
    {"from": "bob", "to": "alice", "type": "RECRUITING"},
    
    # Goby and Alice are FRIENDS (they know each other from community)
    {"from": "goby", "to": "alice", "type": "FRIEND"},
    
    # Goby was COLLEAGUE with Alice (hypothetically worked together)
    {"from": "goby", "to": "alice", "type": "COLLEAGUE"},
]


# ============================================================================
# SEED FUNCTIONS
# ============================================================================

def seed_users(client: Neo4jClient) -> None:
    """Seed User nodes."""
    print("📝 Seeding Users...")
    for user in SAMPLE_USERS:
        try:
            client.create_user(user)
            print(f"  ✓ Created user: {user['name']} ({user['user_id']})")
        except Exception as e:
            print(f"  ✗ Failed to create user {user['user_id']}: {e}")


def seed_entities(client: Neo4jClient) -> None:
    """Seed Entity nodes."""
    print("\n🏷️  Seeding Entities...")
    for entity in SAMPLE_ENTITIES:
        try:
            client.create_entity(entity)
            print(f"  ✓ Created entity: {entity['name']} ({entity['entity_type']})")
        except Exception as e:
            print(f"  ✗ Failed to create entity {entity['entity_id']}: {e}")


def seed_evidence(client: Neo4jClient) -> None:
    """Seed Evidence nodes."""
    print("\n📎 Seeding Evidence...")
    for evidence in SAMPLE_EVIDENCE:
        try:
            client.create_evidence(evidence)
            print(f"  ✓ Created evidence: {evidence['evidence_id']} ({evidence['evidence_type']})")
        except Exception as e:
            print(f"  ✗ Failed to create evidence {evidence['evidence_id']}: {e}")


def seed_claims(client: Neo4jClient) -> None:
    """Seed Claim nodes and relationships."""
    print("\n📋 Seeding Claims...")
    for claim in SAMPLE_CLAIMS:
        try:
            # Extract entity_ids and evidence_ids
            entity_ids = claim.pop("entity_ids", [])
            evidence_ids = claim.pop("evidence_ids", [])
            user_id = claim["user_id"]
            
            # Create claim
            client.create_claim(claim, user_id)
            print(f"  ✓ Created claim: {claim['claim_id']} ({claim['topic']}) for {user_id}")
            
            # Link to entities
            for entity_canonical_id in entity_ids:
                try:
                    client.link_claim_to_entity(claim["claim_id"], entity_canonical_id)
                except Exception as e:
                    print(f"    ⚠ Could not link entity {entity_canonical_id}: {e}")
            
            # Link to evidence
            for evidence_id in evidence_ids:
                try:
                    client.link_claim_to_evidence(claim["claim_id"], evidence_id)
                except Exception as e:
                    print(f"    ⚠ Could not link evidence {evidence_id}: {e}")
                    
        except Exception as e:
            print(f"  ✗ Failed to create claim {claim.get('claim_id')}: {e}")


def seed_relationships(client: Neo4jClient) -> None:
    """Seed social relationships between users."""
    print("\n🔗 Seeding Social Relationships...")
    for rel in SAMPLE_RELATIONSHIPS:
        try:
            client.create_user_relationship(rel["from"], rel["to"], rel["type"])
            print(f"  ✓ Created: ({rel['from']})-[:{rel['type']}]->({rel['to']})")
        except Exception as e:
            print(f"  ✗ Failed to create relationship: {e}")


def setup_database(client: Neo4jClient) -> None:
    """Setup database constraints and indexes."""
    print("⚙️  Setting up database constraints and indexes...")
    client.create_constraints()
    client.create_indexes()
    print("  ✓ Constraints and indexes created")


def print_stats(client: Neo4jClient) -> None:
    """Print database statistics."""
    print("\n📊 Database Statistics:")
    stats = client.get_database_stats()
    
    print("  Nodes:")
    for label, count in stats["nodes"].items():
        print(f"    - {label}: {count}")
    
    print("  Relationships:")
    for rel_type, count in stats["relationships"].items():
        print(f"    - {rel_type}: {count}")


def print_demo_info() -> None:
    """Print demo information."""
    print("\n" + "=" * 60)
    print("📚 DEMO PERSONAS - 3 Core Users")
    print("=" * 60)
    print("""
┌────────────────────────────────────────────────────────────┐
│ GOBY (Freelancer - Python/RAG Specialist)                  │
├────────────────────────────────────────────────────────────┤
│ • 5 năm Python, FastAPI, Django                            │
│ • Chuyên về RAG systems, LangChain, OpenAI                 │
│ • Ex-TechCorp (2022-2024)                                  │
│ • Claims: 6 (public, internal, hr_sensitive)               │
│ • Salary expectation: $3,000-4,000/mo (HR only)            │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ ALICE (Freelancer - React/Frontend Expert)                 │
├────────────────────────────────────────────────────────────┤
│ • 4 năm React, TypeScript, Next.js                         │
│ • UI/UX Design với Figma, TailwindCSS                      │
│ • Ex-FPT Software (2021-2023)                              │
│ • Claims: 6 (public, internal, hr_sensitive)               │
│ • Salary expectation: $2,500-3,500/mo (HR only)            │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ BOB (Recruiter - TechCorp Vietnam)                         │
├────────────────────────────────────────────────────────────┤
│ • 6 năm Technical Recruiting                               │
│ • Đang tìm Python + React Developers                       │
│ • Budget: $2,500-4,500/mo                                  │
│ • RECRUITING → Goby, Alice                                 │
└────────────────────────────────────────────────────────────┘

🔗 Social Graph:
   Bob --[RECRUITING]--> Goby
   Bob --[RECRUITING]--> Alice
   Goby <--[FRIEND]--> Alice
   Goby <--[COLLEAGUE]--> Alice
""")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Seed Neo4j database with sample data")
    parser.add_argument("--clear", action="store_true", help="Clear database before seeding")
    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j connection URI")
    parser.add_argument("--user", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", default="neo4jpassword", help="Neo4j password")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🌱 Neo4j Seed Data Script - 3 Personas Demo")
    print("=" * 60)
    print(f"URI: {args.uri}")
    print(f"User: {args.user}")
    print("=" * 60)
    
    try:
        # Connect to Neo4j
        print("\n🔌 Connecting to Neo4j...")
        client = get_neo4j_client(args.uri, args.user, args.password)
        print("  ✓ Connected successfully")
        
        # Clear database if requested
        if args.clear:
            print("\n🗑️  Clearing database...")
            result = client.clear_database()
            print(f"  ✓ Cleared {result.get('nodes_deleted', 0)} nodes")
        
        # Setup database
        setup_database(client)
        
        # Seed data
        seed_users(client)
        seed_entities(client)
        seed_evidence(client)
        seed_claims(client)
        seed_relationships(client)
        
        # Print statistics
        print_stats(client)
        
        # Print demo info
        print_demo_info()
        
        print("\n" + "=" * 60)
        print("✅ Seed completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Open Neo4j Browser: http://localhost:7474")
        print("  2. Login with neo4j / neo4jpassword")
        print("  3. Try queries:")
        print("     - MATCH (n) RETURN n LIMIT 50")
        print("     - MATCH (u:User)-[:MAKES_CLAIM]->(c:Claim) RETURN u, c")
        print("     - MATCH (bob:User {user_id:'bob'})-[:RECRUITING]->(target) RETURN target")
        print("\n  4. Test Discovery Agent:")
        print("     python -m utils.discovery_agent")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        # Close connection
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    main()

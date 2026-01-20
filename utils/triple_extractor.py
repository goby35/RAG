# utils/triple_extractor.py - AI Claim Extraction from Natural Language
"""
Module này sử dụng OpenAI để tự động extract Claims từ text tự nhiên.
User nhập mô tả bình thường, AI sẽ chuyển thành Claim objects với:
- content_summary: Mô tả chi tiết cho RAG
- entities: Các entities được nhắc đến
- topic: Phân loại chủ đề

Output theo schema mới: Claim, Entity (với canonical_id)
"""

import json
from typing import List, Dict, Tuple, Optional
from openai import OpenAI

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_openai_api_key, LLM_MODEL, CLAIM_TOPICS, CONFIDENCE_SCORES
from models.schema import Claim, Entity, Evidence, ClaimStatus, create_claim_from_input
from utils.entity_linker import link_or_create_entity, get_entity_linker


# ============================================================================
# CATEGORY MAPPING
# ============================================================================

# Map từ category UI về topic trong schema
CATEGORY_TO_TOPIC = {
    "experience": "work",
    "skill": "skill",
    "project": "project",
    "certificate": "certificate",
    "education": "education",
    "achievement": "achievement",
    "connection": "other",
    "bio": "other"
}

# Category display names (Vietnamese)
CATEGORY_DISPLAY = {
    "experience": "💼 Kinh nghiệm làm việc",
    "skill": "🛠️ Kỹ năng",
    "project": "📁 Dự án",
    "certificate": "📜 Chứng chỉ & Khóa học",
    "education": "🎓 Học vấn",
    "achievement": "🏆 Thành tích & Giải thưởng",
    "connection": "🤝 Kết nối & Endorsement"
}

CATEGORY_PLACEHOLDERS = {
    "experience": "Ví dụ: Tôi làm Senior Developer tại TechCorp từ 2022, phụ trách backend với Python và FastAPI...",
    "skill": "Ví dụ: Thành thạo Python, React, Docker. Có kinh nghiệm với AWS và Kubernetes...",
    "project": "Ví dụ: Xây dựng hệ thống RAG cho chatbot hỗ trợ khách hàng, sử dụng LangChain và OpenAI...",
    "certificate": "Ví dụ: Hoàn thành khóa Machine Learning của Coursera, đạt chứng chỉ AWS Solutions Architect...",
    "education": "Ví dụ: Tốt nghiệp Đại học Bách Khoa chuyên ngành Khoa học Máy tính năm 2020...",
    "achievement": "Ví dụ: Đạt giải nhất Hackathon AI 2024, được vinh danh Top 10 Developer of the Year...",
    "connection": "Ví dụ: Được Alice (Senior Manager tại Google) endorse về kỹ năng Machine Learning..."
}


# ============================================================================
# CLAIM EXTRACTION PROMPT
# ============================================================================

def build_claim_extraction_prompt(user_id: str, category: str, description: str, evidence: str) -> str:
    """
    Xây dựng prompt để AI extract Claim với entities.
    
    Args:
        user_id: ID của user đang nhập
        category: Loại thông tin (experience, skill, project, etc.)
        description: Mô tả tự nhiên từ user
        evidence: Link bằng chứng (nếu có)
        
    Returns:
        Prompt string
    """
    topic = CLAIM_TOPICS.get(CATEGORY_TO_TOPIC.get(category, "other"), "Other")
    
    return f"""Bạn là AI chuyên phân tích thông tin cá nhân và trích xuất thành Claims cho Knowledge Graph.

Nhiệm vụ: Phân tích mô tả sau và tạo các Claim objects với entities liên quan.

User ID: {user_id}
Loại thông tin: {category}
Topic chuẩn: {topic}
Mô tả: "{description}"
Bằng chứng: {evidence if evidence else "Không có"}

Quy tắc trích xuất:
1. Mỗi Claim là một khẳng định CỤ THỂ và ĐỘC LẬP
2. content_summary phải chi tiết đủ để AI có thể trả lời câu hỏi về user
3. entities là danh sách các thực thể (skills, công ty, trường học, chứng chỉ...)
4. Mỗi entity có type: Skill, Organization, Project, Certificate, Education, Achievement

Trả về JSON với format:
```json
{{
  "claims": [
    {{
      "content_summary": "User {user_id} có 3 năm kinh nghiệm làm việc với Python tại TechCorp...",
      "entities": [
        {{"name": "Python", "type": "Skill"}},
        {{"name": "TechCorp", "type": "Organization"}}
      ]
    }}
  ]
}}
```

Quan trọng:
- content_summary phải BẮT ĐẦU bằng "User {user_id}" để dễ search
- Nếu có nhiều thông tin khác nhau, tạo nhiều claims
- Entities phải cụ thể (Python thay vì "programming language")

Chỉ trả về JSON, không giải thích thêm."""


# ============================================================================
# MAIN EXTRACTION FUNCTION
# ============================================================================

def extract_claims(
    user_id: str, 
    category: str, 
    description: str, 
    evidence: str = "",
    access_level: str = "public"
) -> Tuple[List[Claim], List[Entity], Optional[Evidence]]:
    """
    Sử dụng AI để extract Claims, Entities từ mô tả tự nhiên.
    
    Args:
        user_id: ID của user
        category: Loại thông tin
        description: Mô tả từ user
        evidence: Link bằng chứng
        access_level: Mức độ truy cập
        
    Returns:
        Tuple: (List[Claim], List[Entity], Evidence or None)
    """
    if not description.strip():
        return [], [], None
    
    client = OpenAI(api_key=get_openai_api_key())
    prompt = build_claim_extraction_prompt(user_id, category, description, evidence)
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON từ response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        data = json.loads(content)
        claims_data = data.get("claims", [])
        
        # Build Claim và Entity objects
        claims = []
        all_entities = []
        entity_linker = get_entity_linker()
        
        # Tạo Evidence nếu có
        evidence_obj = None
        if evidence.strip():
            evidence_obj = Evidence(url=evidence)
        
        topic = CLAIM_TOPICS.get(CATEGORY_TO_TOPIC.get(category, "other"), "Other")
        
        for claim_data in claims_data:
            content_summary = claim_data.get("content_summary", "")
            entities_data = claim_data.get("entities", [])
            
            # Create Entity objects với canonical_id
            entity_ids = []
            for ent in entities_data:
                ent_name = ent.get("name", "")
                ent_type = ent.get("type", "Skill")
                
                # Link về canonical_id
                canonical_id = link_or_create_entity(ent_name, ent_type)
                
                entity = Entity(
                    name=ent_name,
                    canonical_id=canonical_id,
                    entity_type=ent_type
                )
                all_entities.append(entity)
                entity_ids.append(canonical_id)
            
            # Create Claim
            claim = Claim(
                user_id=user_id,
                topic=topic,
                content_summary=content_summary,
                access_level=access_level,
                status=ClaimStatus.SELF_DECLARED.value,
                confidence_score=CONFIDENCE_SCORES['base_self_declared'],
                entity_ids=entity_ids
            )
            
            # Add evidence if exists
            if evidence_obj:
                claim.evidence_ids.append(evidence_obj.evidence_id)
                claim.calculate_confidence_score(has_evidence=True)
            
            claims.append(claim)
        
        return claims, all_entities, evidence_obj
        
    except json.JSONDecodeError:
        # Fallback: tạo claim đơn giản
        topic = CLAIM_TOPICS.get(CATEGORY_TO_TOPIC.get(category, "other"), "Other")
        claim = Claim(
            user_id=user_id,
            topic=topic,
            content_summary=f"User {user_id}: {description[:200]}",
            access_level=access_level,
            status=ClaimStatus.SELF_DECLARED.value,
            confidence_score=CONFIDENCE_SCORES['base_self_declared']
        )
        
        evidence_obj = None
        if evidence.strip():
            evidence_obj = Evidence(url=evidence)
            claim.evidence_ids.append(evidence_obj.evidence_id)
            claim.calculate_confidence_score(has_evidence=True)
        
        return [claim], [], evidence_obj
        
    except Exception as e:
        print(f"Error extracting claims: {str(e)}")
        return [], [], None


# ============================================================================
# BACKWARD COMPATIBILITY - Legacy Triple Format
# ============================================================================

def extract_triples(user_id: str, category: str, description: str, 
                    evidence: str = "") -> list:
    """
    LEGACY: Sử dụng AI để extract triples từ mô tả tự nhiên.
    Giữ lại cho backward compatibility với code cũ.
    
    Returns:
        List các triples dạng dict với keys: Source, Relation, Target, Evidence
    """
    claims, entities, evidence_obj = extract_claims(user_id, category, description, evidence)
    
    # Convert claims sang format triples cũ
    triples = []
    for claim in claims:
        for entity_id in claim.entity_ids:
            triples.append({
                "Source": claim.user_id,
                "Relation": f"HAS_{claim.topic.upper().replace(' ', '_')}",
                "Target": entity_id,
                "Evidence": evidence if evidence else "",
                "Access_Level": claim.access_level,
                "Status": claim.status,
                "Confidence_Score": claim.confidence_score,
                "Content_Summary": claim.content_summary
            })
    
    # Nếu không có entities, tạo triple với content làm target
    if not triples and claims:
        for claim in claims:
            triples.append({
                "Source": claim.user_id,
                "Relation": f"HAS_{claim.topic.upper().replace(' ', '_')}",
                "Target": claim.content_summary[:100],
                "Evidence": evidence if evidence else "",
                "Access_Level": claim.access_level,
                "Status": claim.status,
                "Confidence_Score": claim.confidence_score,
                "Content_Summary": claim.content_summary
            })
    
    return triples


# ============================================================================
# PREVIEW FUNCTIONS
# ============================================================================

def preview_claims(claims: List[Claim], entities: List[Entity]) -> str:
    """
    Tạo preview text cho các Claims đã extract.
    
    Args:
        claims: List các Claims
        entities: List các Entities
        
    Returns:
        Formatted string để hiển thị
    """
    if not claims:
        return "Không có thông tin để trích xuất."
    
    lines = ["**📋 Claims sẽ được lưu:**", ""]
    
    for i, claim in enumerate(claims, 1):
        confidence_emoji = "🟢" if claim.confidence_score >= 0.8 else "🟡" if claim.confidence_score >= 0.5 else "🔴"
        lines.append(f"**{i}. {claim.topic}** {confidence_emoji} ({claim.confidence_score:.1%} tin cậy)")
        lines.append(f"   📝 {claim.content_summary[:150]}...")
        lines.append("")
    
    if entities:
        lines.append("**🏷️ Entities được phát hiện:**")
        unique_entities = {e.canonical_id: e for e in entities}
        for ent in unique_entities.values():
            lines.append(f"   • {ent.name} ({ent.entity_type})")
    
    return "\n".join(lines)


def preview_triples(triples: list) -> str:
    """
    LEGACY: Tạo preview text cho các triples đã extract.
    
    Args:
        triples: List các triples
        
    Returns:
        Formatted string để hiển thị
    """
    if not triples:
        return "Không có thông tin để trích xuất."
    
    lines = ["**Thông tin sẽ được lưu:**", ""]
    for i, t in enumerate(triples, 1):
        confidence = t.get('Confidence_Score', 0.3)
        confidence_emoji = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.5 else "🔴"
        lines.append(f"{i}. `{t['Source']}` → **{t['Relation']}** → `{t['Target']}` {confidence_emoji}")
    
    return "\n".join(lines)

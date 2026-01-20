# utils/triple_extractor.py - AI Triple Extraction from Natural Language
"""
Module này sử dụng OpenAI để tự động extract triples từ text tự nhiên.
User nhập mô tả bình thường, AI sẽ chuyển thành các bộ ba (Source, Relation, Target).
"""

import json
from openai import OpenAI

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_openai_api_key, LLM_MODEL


# Mapping từ loại thông tin sang các relation types phù hợp
CATEGORY_RELATIONS = {
    "experience": ["WORKED_AT", "WORKED_ON", "HAS_ROLE", "HAS_EXPERIENCE"],
    "skill": ["HAS_SKILL", "PROFICIENT_IN", "USES", "KNOWS"],
    "project": ["DEVELOPED", "CONTRIBUTED_TO", "WORKED_ON", "CREATED"],
    "certificate": ["COMPLETED_COURSE", "HAS_CERTIFICATION", "EARNED", "ACHIEVED"],
    "education": ["STUDIED_AT", "GRADUATED_FROM", "HAS_DEGREE", "MAJORED_IN"],
    "achievement": ["WON_AWARD", "ACHIEVED", "RECOGNIZED_FOR", "RECEIVED"],
    "connection": ["CONNECTED_WITH", "ENDORSED", "RECOMMENDED", "COLLABORATED_WITH"]
}


def build_extraction_prompt(user_id: str, category: str, description: str, evidence: str) -> str:
    """
    Xây dựng prompt cho AI để extract triples.
    
    Args:
        user_id: ID của user đang nhập
        category: Loại thông tin (experience, skill, project, etc.)
        description: Mô tả tự nhiên từ user
        evidence: Link bằng chứng (nếu có)
        
    Returns:
        Prompt string
    """
    relations = CATEGORY_RELATIONS.get(category, ["RELATED_TO"])
    
    return f"""Bạn là AI chuyên trích xuất thông tin từ văn bản thành Knowledge Graph triples.

Nhiệm vụ: Phân tích mô tả sau và trích xuất thành các bộ ba (triples) theo format JSON.

User ID: {user_id}
Loại thông tin: {category}
Mô tả: "{description}"
Bằng chứng: {evidence if evidence else "Không có"}

Các Relation phù hợp cho loại "{category}": {', '.join(relations)}

Quy tắc:
1. Source thường là User ID hoặc entity chính
2. Target là đối tượng cụ thể (kỹ năng, công ty, dự án, etc.)
3. Relation mô tả mối quan hệ giữa Source và Target
4. Trích xuất TẤT CẢ thông tin có thể từ mô tả
5. Mỗi thông tin riêng biệt tạo thành 1 triple

Trả về JSON array với format:
```json
[
  {{"source": "...", "relation": "...", "target": "..."}},
  ...
]
```

Chỉ trả về JSON, không giải thích thêm."""


def extract_triples(user_id: str, category: str, description: str, 
                    evidence: str = "") -> list:
    """
    Sử dụng AI để extract triples từ mô tả tự nhiên.
    
    Args:
        user_id: ID của user
        category: Loại thông tin
        description: Mô tả từ user
        evidence: Link bằng chứng
        
    Returns:
        List các triples dạng dict
    """
    if not description.strip():
        return []
    
    client = OpenAI(api_key=get_openai_api_key())
    prompt = build_extraction_prompt(user_id, category, description, evidence)
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature cho extraction chính xác
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON từ response
        # Xử lý trường hợp response có markdown code block
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        triples = json.loads(content)
        
        # Normalize keys và thêm evidence
        normalized = []
        for t in triples:
            normalized.append({
                "Source": t.get("source", user_id),
                "Relation": t.get("relation", "RELATED_TO"),
                "Target": t.get("target", ""),
                "Evidence": evidence
            })
        
        return normalized
        
    except json.JSONDecodeError as e:
        # Fallback: tạo triple đơn giản
        return [{
            "Source": user_id,
            "Relation": CATEGORY_RELATIONS.get(category, ["RELATED_TO"])[0],
            "Target": description[:100],  # Truncate nếu quá dài
            "Evidence": evidence
        }]
    except Exception as e:
        print(f"Error extracting triples: {str(e)}")
        return []


def preview_triples(triples: list) -> str:
    """
    Tạo preview text cho các triples đã extract.
    
    Args:
        triples: List các triples
        
    Returns:
        Formatted string để hiển thị
    """
    if not triples:
        return "Không có thông tin để trích xuất."
    
    lines = ["**Thông tin sẽ được lưu:**", ""]
    for i, t in enumerate(triples, 1):
        lines.append(f"{i}. `{t['Source']}` → **{t['Relation']}** → `{t['Target']}`")
    
    return "\n".join(lines)


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

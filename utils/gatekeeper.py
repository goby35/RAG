# utils/gatekeeper.py - Gatekeeper Logic với Confidence Scoring
"""
Gatekeeper Module - Access Control cho RAG Application.

Logic phân quyền theo Graph Schema mới:
- Dựa trên Claim.access_level và Claim.status
- Kết hợp confidence_score để ranking
- Hỗ trợ multi-layer access control

Confidence Score Logic:
- Self-declared = 0.3 (base)
- Có Evidence = 0.5
- Có Attestation (EAS) = 0.9
- Attestation từ nguồn uy tín = 1.0
"""

import sys
import os

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Try importing from new config module, fallback to old
try:
    from config.access import CONFIDENCE_SCORES, VERIFIED_STATUSES, MIN_CONFIDENCE_FOR_RAG
except ImportError:
    from config import CONFIDENCE_SCORES, VERIFIED_STATUSES, MIN_CONFIDENCE_FOR_RAG


def gatekeeper_filter(
    metadata: list,
    target_user_id: str,
    viewer_id: str,
    viewer_role: str = "Default",
    min_confidence: float = None
) -> list:
    """
    Lọc dữ liệu theo 3 bước:
    
    Bước 1 (Scope): Chỉ lấy các dòng có user_id == Target User ID
    Bước 2 (Access Control): So sánh Viewer ID và Target User ID để xác định quyền
    Bước 3 (Confidence Filter): Lọc theo minimum confidence score
    
    Access Control Rules:
    - Owner (Viewer == Target): Xem được tất cả
    - Recruiter: Xem public + connections_only nếu verified
    - Public/Anonymous: Chỉ xem public
    
    Args:
        metadata: List metadata của tất cả documents
        target_user_id: ID của người bị soi (Target User)
        viewer_id: ID của người đang xem (Viewer)
        viewer_role: Role đặc biệt của Viewer (Default, Recruiter)
        min_confidence: Minimum confidence score (None = không filter)
    
    Returns:
        List các indices được phép truy cập
    """
    if min_confidence is None:
        min_confidence = MIN_CONFIDENCE_FOR_RAG
    
    allowed_indices = []
    
    for i, m in enumerate(metadata):
        # Bước 1: Scope - Chỉ xét các dòng thuộc về Target User
        # Support cả schema cũ (source) và schema mới (user_id)
        source = m.get("user_id") or m.get("source")
        if source != target_user_id:
            continue
        
        # Bước 2: Access Control
        access_level = m.get("access_level", "public")
        
        # Check verified status - support cả schema cũ và mới
        status = m.get("status", "self_declared")
        is_verified = m.get("verified", status in VERIFIED_STATUSES)
        
        # Get confidence score - mặc định 0.3 cho self-declared
        confidence = m.get("confidence_score", CONFIDENCE_SCORES['base_self_declared'])
        
        # Bước 3: Confidence Filter
        if confidence < min_confidence:
            continue
        
        # Case 1: Viewer == Target (Owner) -> Xem được tất cả
        if viewer_id == target_user_id:
            allowed_indices.append(i)
            continue
        
        # Case 2: Viewer là Recruiter -> Xem public + connections_only nếu verified
        if viewer_role == "Recruiter":
            if access_level == "public":
                allowed_indices.append(i)
            elif access_level in ["connections_only", "recruiter"] and is_verified:
                allowed_indices.append(i)
            continue
        
        # Case 3: Viewer != Target (Public/Anonymous) -> Chỉ xem public
        if access_level == "public":
            allowed_indices.append(i)
    
    return allowed_indices


def gatekeeper_filter_with_ranking(
    metadata: list,
    target_user_id: str,
    viewer_id: str,
    viewer_role: str = "Default"
) -> list:
    """
    Lọc và RANKING theo confidence score.
    
    Trả về indices đã được sắp xếp theo confidence từ cao xuống thấp.
    Giúp RAG ưu tiên các claims đáng tin cậy hơn.
    
    Returns:
        List các tuples (index, confidence_score) đã sắp xếp
    """
    allowed_indices = gatekeeper_filter(
        metadata, target_user_id, viewer_id, viewer_role, min_confidence=0.0
    )
    
    # Sort by confidence score descending
    indexed_with_confidence = []
    for i in allowed_indices:
        confidence = metadata[i].get("confidence_score", CONFIDENCE_SCORES['base_self_declared'])
        indexed_with_confidence.append((i, confidence))
    
    indexed_with_confidence.sort(key=lambda x: x[1], reverse=True)
    
    return indexed_with_confidence


def get_access_info(viewer_id: str, target_user_id: str, viewer_role: str) -> dict:
    """
    Lấy thông tin về quyền truy cập hiện tại.
    
    Args:
        viewer_id: ID người xem
        target_user_id: ID người bị xem
        viewer_role: Role của người xem
        
    Returns:
        Dictionary chứa thông tin access
    """
    if viewer_id == target_user_id:
        return {
            "type": "owner",
            "icon": "",
            "label": "Owner Access",
            "description": "Bạn đang xem hồ sơ của chính mình. Có thể xem TẤT CẢ dữ liệu.",
            "level": "success",
            "can_see": ["public", "private", "connections_only"]
        }
    elif viewer_role == "Recruiter":
        return {
            "type": "recruiter",
            "icon": "",
            "label": "Recruiter Access",
            "description": f"Bạn có thể xem dữ liệu `public` và `verified` của '{target_user_id}'.",
            "level": "info",
            "can_see": ["public", "connections_only (verified only)"]
        }
    elif viewer_id == "__ANONYMOUS__":
        return {
            "type": "anonymous",
            "icon": "",
            "label": "Anonymous Access",
            "description": f"Bạn chỉ có thể xem dữ liệu `public` của '{target_user_id}'.",
            "level": "warning",
            "can_see": ["public"]
        }
    else:
        return {
            "type": "public",
            "icon": "",
            "label": "Public Access",
            "description": f"Bạn ({viewer_id}) chỉ có thể xem dữ liệu `public` của '{target_user_id}'.",
            "level": "warning",
            "can_see": ["public"]
        }


def count_accessible_documents(metadata: list, target_user_id: str, 
                                viewer_id: str, viewer_role: str) -> tuple:
    """
    Đếm số documents có thể truy cập.
    
    Args:
        metadata: List metadata
        target_user_id: ID người bị xem
        viewer_id: ID người xem
        viewer_role: Role của người xem
        
    Returns:
        Tuple (accessible_count, total_count)
    """
    accessible = len(gatekeeper_filter(metadata, target_user_id, viewer_id, viewer_role))
    
    # Support cả schema cũ và mới
    total = len([m for m in metadata if (m.get("user_id") or m.get("source")) == target_user_id])
    
    return accessible, total


def get_confidence_summary(metadata: list, indices: list) -> dict:
    """
    Tính summary về confidence scores của các documents được phép.
    
    Args:
        metadata: List metadata
        indices: List indices được phép
        
    Returns:
        Dict với thống kê confidence
    """
    if not indices:
        return {
            "total": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "avg_confidence": 0.0
        }
    
    confidences = [metadata[i].get("confidence_score", 0.3) for i in indices]
    
    return {
        "total": len(indices),
        "high_confidence": len([c for c in confidences if c >= 0.8]),  # Attested
        "medium_confidence": len([c for c in confidences if 0.5 <= c < 0.8]),  # With evidence
        "low_confidence": len([c for c in confidences if c < 0.5]),  # Self-declared only
        "avg_confidence": sum(confidences) / len(confidences)
    }

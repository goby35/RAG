# utils/gatekeeper.py - Gatekeeper Logic (Access Control)

def gatekeeper_filter(
    metadata: list,
    target_user_id: str,
    viewer_id: str,
    viewer_role: str = "Default"
) -> list:
    """
    Lọc dữ liệu theo 2 bước:
    
    Bước 1 (Scope): Chỉ lấy các dòng có Source == Target User ID
    Bước 2 (Access Control): So sánh Viewer ID và Target User ID để xác định quyền
    
    Access Control Rules:
    - Owner (Viewer == Target): Xem được tất cả
    - Recruiter: Xem public + private/recruiter nếu verified
    - Public/Anonymous: Chỉ xem public
    
    Args:
        metadata: List metadata của tất cả documents
        target_user_id: ID của người bị soi (Target User)
        viewer_id: ID của người đang xem (Viewer)
        viewer_role: Role đặc biệt của Viewer (Default, Recruiter)
    
    Returns:
        List các indices được phép truy cập
    """
    allowed_indices = []
    
    for i, m in enumerate(metadata):
        # Bước 1: Scope - Chỉ xét các dòng thuộc về Target User
        if m["source"] != target_user_id:
            continue
        
        # Bước 2: Access Control
        access_level = m["access_level"]
        is_verified = m["verified"]
        
        # Case 1: Viewer == Target (Owner) -> Xem được tất cả
        if viewer_id == target_user_id:
            allowed_indices.append(i)
            continue
        
        # Case 2: Viewer là Recruiter -> Xem public + private/recruiter nếu verified
        if viewer_role == "Recruiter":
            if access_level == "public":
                allowed_indices.append(i)
            elif access_level in ["private", "recruiter"] and is_verified:
                allowed_indices.append(i)
            continue
        
        # Case 3: Viewer != Target (Public/Anonymous) -> Chỉ xem public
        if access_level == "public":
            allowed_indices.append(i)
    
    return allowed_indices


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
            "icon": "🔓",
            "label": "Owner Access",
            "description": "Bạn đang xem hồ sơ của chính mình. Có thể xem TẤT CẢ dữ liệu.",
            "level": "success"
        }
    elif viewer_role == "Recruiter":
        return {
            "type": "recruiter",
            "icon": "👔",
            "label": "Recruiter Access",
            "description": f"Bạn có thể xem dữ liệu `public` và dữ liệu `verified` của '{target_user_id}'.",
            "level": "info"
        }
    elif viewer_id == "__ANONYMOUS__":
        return {
            "type": "anonymous",
            "icon": "👁️",
            "label": "Anonymous Access",
            "description": f"Bạn chỉ có thể xem dữ liệu `public` của '{target_user_id}'.",
            "level": "warning"
        }
    else:
        return {
            "type": "public",
            "icon": "👁️",
            "label": "Public Access",
            "description": f"Bạn ({viewer_id}) chỉ có thể xem dữ liệu `public` của '{target_user_id}'.",
            "level": "warning"
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
    total = len([m for m in metadata if m["source"] == target_user_id])
    return accessible, total

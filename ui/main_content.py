# ui/main_content.py - Main Content Components
import streamlit as st
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.gatekeeper import get_access_info, count_accessible_documents
from utils.rag_engine import simple_rag


def render_viewer_selection(user_ids: list) -> tuple:
    """
    Render phần chọn Viewer.
    
    Args:
        user_ids: List các User ID
        
    Returns:
        Tuple (viewer_id, viewer_role)
    """
    st.subheader("Bạn là ai? (Viewer)")
    
    viewer_options = ["Khách vãng lai (Anonymous)"] + user_ids
    viewer_selection = st.selectbox(
        "Chọn danh tính của bạn:",
        viewer_options,
        key="viewer_id"
    )
    
    # Xác định Viewer ID
    if viewer_selection == "Khách vãng lai (Anonymous)":
        viewer_id = "__ANONYMOUS__"
    else:
        viewer_id = viewer_selection
    
    # Role selection (nâng cao)
    viewer_role = st.selectbox(
        "Role đặc biệt (tùy chọn):",
        ["Default", "Recruiter"],
        key="viewer_role",
        help="Recruiter có thể xem thêm dữ liệu đã verified"
    )
    
    return viewer_id, viewer_role


def render_target_selection(user_ids: list) -> str:
    """
    Render phần chọn Target User.
    
    Args:
        user_ids: List các User ID
        
    Returns:
        Target User ID hoặc None
    """
    st.subheader("Bạn muốn xem hồ sơ của ai?")
    
    if user_ids:
        target_user_id = st.selectbox(
            "Chọn User để xem thông tin:",
            user_ids,
            key="target_user_id"
        )
        return target_user_id
    else:
        st.warning("Chưa có User nào trong hệ thống!")
        return None


def render_access_info(metadata: list, target_user_id: str, 
                       viewer_id: str, viewer_role: str):
    """Render thông tin quyền truy cập."""
    with st.expander("ℹ️ Thông tin quyền truy cập", expanded=False):
        access_info = get_access_info(viewer_id, target_user_id, viewer_role)
        
        # Hiển thị theo level
        message = f"{access_info['icon']} **{access_info['label']}**: {access_info['description']}"
        
        if access_info['level'] == 'success':
            st.success(message)
        elif access_info['level'] == 'info':
            st.info(message)
        else:
            st.warning(message)
        
        # Hiển thị số lượng documents có thể truy cập
        if metadata:
            accessible, total = count_accessible_documents(
                metadata, target_user_id, viewer_id, viewer_role
            )
            st.metric("Số dữ liệu có thể truy cập", f"{accessible}/{total}")


def render_query_section(embedder: SentenceTransformer,
                         doc_embeddings: np.ndarray,
                         documents: list,
                         metadata: list,
                         target_user_id: str,
                         viewer_id: str,
                         viewer_role: str):
    """Render phần query và kết quả."""
    st.subheader("Đặt câu hỏi")
    
    placeholder_text = (
        f"Ví dụ: {target_user_id} có những kỹ năng gì?" 
        if target_user_id else "Chọn user trước..."
    )
    
    query = st.text_input(
        "Nhập câu hỏi về người dùng được chọn:",
        placeholder=placeholder_text,
        key="query_input"
    )
    
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        search_btn = st.button("Tìm kiếm", type="primary", use_container_width=True)
    
    # Handle search
    if search_btn and query and target_user_id:
        with st.spinner("Đang tìm kiếm và phân tích..."):
            answer = simple_rag(
                query=query,
                embedder=embedder,
                doc_embeddings=doc_embeddings,
                documents=documents,
                metadata=metadata,
                target_user_id=target_user_id,
                viewer_id=viewer_id,
                viewer_role=viewer_role
            )
        
        st.markdown("### Kết quả")
        st.markdown(answer)
    
    elif search_btn and not query:
        st.warning("⚠️ Vui lòng nhập câu hỏi.")
    
    elif search_btn and not target_user_id:
        st.warning("⚠️ Vui lòng chọn User để xem thông tin.")


def render_data_preview(data_df: pd.DataFrame):
    """Render phần preview dữ liệu."""
    st.markdown("---")
    with st.expander("Xem dữ liệu thô (Raw Data Preview)", expanded=False):
        if not data_df.empty:
            st.dataframe(data_df, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu. Hãy thêm dữ liệu qua sidebar.")


def render_main_content(data_df: pd.DataFrame,
                        user_ids: list,
                        embedder: SentenceTransformer,
                        documents: list,
                        metadata: list,
                        doc_embeddings: np.ndarray):
    """
    Render toàn bộ main content.
    
    Args:
        data_df: DataFrame dữ liệu
        user_ids: List User IDs
        embedder: SentenceTransformer model
        documents: List documents
        metadata: List metadata
        doc_embeddings: Document embeddings
    """
    # User selection columns
    col1, col2 = st.columns(2)
    
    with col1:
        viewer_id, viewer_role = render_viewer_selection(user_ids)
    
    with col2:
        target_user_id = render_target_selection(user_ids)
    
    st.markdown("---")
    
    # Access info
    if target_user_id and metadata:
        render_access_info(metadata, target_user_id, viewer_id, viewer_role)
    
    # Query section
    if target_user_id:
        render_query_section(
            embedder=embedder,
            doc_embeddings=doc_embeddings,
            documents=documents,
            metadata=metadata,
            target_user_id=target_user_id,
            viewer_id=viewer_id,
            viewer_role=viewer_role
        )
    
    # Data preview
    render_data_preview(data_df)

# ui/sidebar.py - Sidebar Components (LinkedIn-style Form)
import streamlit as st
import pandas as pd

import sys
import os

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Try importing from new config module, fallback to old
try:
    from config.entities import ACCESS_LEVELS, STATUS_OPTIONS
    from config.paths import DATA_COLUMNS
except ImportError:
    from config import ACCESS_LEVELS, STATUS_OPTIONS, DATA_COLUMNS
    
from utils.data_loader import load_data, save_data, get_unique_user_ids
from utils.triple_extractor import (
    extract_triples, 
    preview_triples,
    CATEGORY_DISPLAY,
    CATEGORY_PLACEHOLDERS
)


def render_user_profile_form():
    """Render form nhập liệu thân thiện kiểu LinkedIn/TopCV."""
    
    st.sidebar.markdown("### Thông tin của bạn")
    
    # User ID selection hoặc nhập mới
    existing_users = get_unique_user_ids(load_data())
    user_options = ["Tạo profile mới..."] + existing_users
    
    user_selection = st.sidebar.selectbox(
        "Chọn hoặc tạo profile:",
        user_options,
        key="sidebar_user_select"
    )
    
    if user_selection == "Tạo profile mới...":
        user_id = st.sidebar.text_input(
            "Nhập tên/ID của bạn:",
            placeholder="Ví dụ: Nguyen_Van_A",
            key="new_user_id"
        )
    else:
        user_id = user_selection
    
    return user_id


def render_friendly_input_form(user_id: str):
    """Render form nhập liệu thân thiện với AI extraction."""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Thêm thông tin mới")
    
    # Chọn loại thông tin
    category_options = list(CATEGORY_DISPLAY.keys())
    category_labels = list(CATEGORY_DISPLAY.values())
    
    selected_label = st.sidebar.selectbox(
        "Loại thông tin:",
        category_labels,
        key="info_category"
    )
    
    # Map label về key
    category = category_options[category_labels.index(selected_label)]
    
    # Form nhập liệu
    with st.sidebar.form(key="friendly_input_form"):
        # Mô tả tự nhiên
        description = st.text_area(
            "Mô tả chi tiết:",
            placeholder=CATEGORY_PLACEHOLDERS.get(category, "Nhập mô tả..."),
            height=120,
            key="description_input"
        )
        
        # Link bằng chứng
        evidence = st.text_input(
            "Link bằng chứng (tùy chọn):",
            placeholder="https://github.com/... hoặc https://linkedin.com/...",
            key="evidence_input"
        )
        
        # Chế độ hiển thị
        col1, col2 = st.columns(2)
        with col1:
            access_level = st.selectbox(
                "Ai được xem?",
                ["public", "private", "connections_only"],
                format_func=lambda x: {
                    "public": "Công khai",
                    "private": "Riêng tư", 
                    "connections_only": "Chỉ kết nối"
                }.get(x, x),
                key="access_level_input"
            )
        
        with col2:
            status = st.selectbox(
                "Trạng thái:",
                ["self_declared", "attested", "pending"],
                format_func=lambda x: {
                    "self_declared": "Tự khai",
                    "attested": "Đã xác minh",
                    "pending": "Chờ duyệt"
                }.get(x, x),
                key="status_input"
            )
        
        # Preview button (trong form)
        preview_btn = st.form_submit_button("Xem trước & Lưu", use_container_width=True)
    
    # Xử lý khi submit
    if preview_btn and user_id and description:
        with st.sidebar.spinner("AI đang phân tích..."):
            triples = extract_triples(
                user_id=user_id,
                category=category,
                description=description,
                evidence=evidence
            )
        
        if triples:
            # Hiển thị preview
            st.sidebar.markdown("---")
            st.sidebar.markdown(preview_triples(triples))
            
            # Lưu vào database
            current_df = load_data()
            new_rows = []
            
            for t in triples:
                new_rows.append({
                    'Source': t['Source'],
                    'Relation': t['Relation'],
                    'Target': t['Target'],
                    'Evidence': t['Evidence'],
                    'Access_Level': access_level,
                    'Status': status
                })
            
            updated_df = pd.concat([current_df, pd.DataFrame(new_rows)], ignore_index=True)
            
            if save_data(updated_df):
                st.sidebar.success(f"Đã lưu {len(triples)} thông tin!")
                st.cache_data.clear()
                st.rerun()
        else:
            st.sidebar.warning("⚠️Không thể trích xuất thông tin. Vui lòng mô tả chi tiết hơn.")
    
    elif preview_btn and not user_id:
        st.sidebar.warning("⚠️ Vui lòng chọn hoặc tạo profile trước.")
    
    elif preview_btn and not description:
        st.sidebar.warning("⚠️ Vui lòng nhập mô tả.")


def render_advanced_form():
    """Render form nhập liệu nâng cao (dạng kỹ thuật - ẩn mặc định)."""
    
    with st.sidebar.expander("Nhập thủ công (Nâng cao)", expanded=False):
        st.caption("Dành cho người dùng kỹ thuật muốn nhập trực tiếp triples.")
        
        with st.form(key="advanced_input_form"):
            source = st.text_input("Source (User ID)")
            relation = st.text_input("Relation (e.g., HAS_SKILL)")
            target = st.text_input("Target (e.g., Python)")
            evidence = st.text_input("Evidence (Link)")
            access_level = st.selectbox("Access Level", ACCESS_LEVELS)
            status = st.selectbox("Status", STATUS_OPTIONS)
            
            submit_btn = st.form_submit_button("➕ Thêm Triple")
            
            if submit_btn:
                if source and relation and target:
                    new_row = {
                        'Source': source,
                        'Relation': relation,
                        'Target': target,
                        'Evidence': evidence,
                        'Access_Level': access_level,
                        'Status': status
                    }
                    updated_df = pd.concat([load_data(), pd.DataFrame([new_row])], ignore_index=True)
                    if save_data(updated_df):
                        st.success("✅ Đã thêm!")
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.warning("⚠️ Điền đủ Source, Relation, Target.")


def render_csv_uploader():
    """Render file uploader cho CSV."""
    st.sidebar.markdown("---")
    
    with st.sidebar.expander("Import/Export Data", expanded=False):
        # Upload
        uploaded_file = st.file_uploader("Upload CSV:", type="csv", key="csv_upload")
        
        if uploaded_file:
            new_df = pd.read_csv(uploaded_file)
            required_cols = set(DATA_COLUMNS)
            
            if required_cols.issubset(new_df.columns):
                if save_data(new_df):
                    st.success("✅ Import thành công!")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.error(f"❌ Thiếu cột: {required_cols - set(new_df.columns)}")
        
        # Download current data
        current_df = load_data()
        if not current_df.empty:
            csv_data = current_df.to_csv(index=False)
            st.download_button(
                "📥 Tải xuống data hiện tại",
                csv_data,
                "knowledge_graph_data.csv",
                "text/csv",
                use_container_width=True
            )


def render_sidebar():
    """Render toàn bộ sidebar."""
    st.sidebar.title("Thêm Dữ Liệu")
    
    # 1. Chọn/tạo user
    user_id = render_user_profile_form()
    
    # 2. Form nhập liệu thân thiện
    if user_id:
        render_friendly_input_form(user_id)
    
    # 3. Form nâng cao (ẩn)
    render_advanced_form()
    
    # 4. Import/Export
    render_csv_uploader()

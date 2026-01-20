# utils/data_loader.py - Data Loading Functions
import os
import pandas as pd
import streamlit as st

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_FILE, DATA_COLUMNS, CACHE_TTL


@st.cache_data(ttl=CACHE_TTL)
def load_data() -> pd.DataFrame:
    """
    Load data từ CSV file.
    
    Returns:
        DataFrame chứa dữ liệu từ CSV hoặc DataFrame rỗng nếu file không tồn tại.
    """
    if os.path.exists(DATA_FILE):
        data_df = pd.read_csv(DATA_FILE)
    else:
        data_df = pd.DataFrame(columns=DATA_COLUMNS)
    return data_df


def save_data(df: pd.DataFrame) -> bool:
    """
    Lưu DataFrame vào CSV file.
    
    Args:
        df: DataFrame cần lưu
        
    Returns:
        True nếu lưu thành công, False nếu có lỗi
    """
    try:
        df.to_csv(DATA_FILE, index=False)
        return True
    except Exception as e:
        st.error(f"Lỗi khi lưu file: {str(e)}")
        return False


def get_unique_user_ids(df: pd.DataFrame) -> list:
    """
    Trích xuất danh sách User ID duy nhất từ cột Source.
    
    Args:
        df: DataFrame chứa dữ liệu
        
    Returns:
        List các User ID duy nhất, đã sắp xếp
    """
    if df.empty:
        return []
    unique_users = df['Source'].dropna().unique().tolist()
    return sorted(unique_users)


def add_new_claim(source: str, relation: str, target: str, 
                  evidence: str, access_level: str, status: str) -> bool:
    """
    Thêm một claim mới vào dữ liệu.
    
    Args:
        source: User ID nguồn
        relation: Loại quan hệ
        target: Đối tượng đích
        evidence: Bằng chứng
        access_level: Mức độ truy cập
        status: Trạng thái xác minh
        
    Returns:
        True nếu thêm thành công
    """
    new_row = {
        'Source': source,
        'Relation': relation,
        'Target': target,
        'Evidence': evidence,
        'Access_Level': access_level,
        'Status': status
    }
    
    current_df = load_data()
    updated_df = pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True)
    return save_data(updated_df)

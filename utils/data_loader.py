# utils/data_loader.py - Data Loading Functions với Graph Schema
"""
Data Loader Module - Hỗ trợ cả Legacy CSV và JSON Schema mới.

Schema mới:
- data/users.json: User nodes
- data/claims.json: Claim nodes (trung tâm logic)
- data/entities.json: Entity nodes
- data/evidence.json: Evidence nodes

Backward compatible với data_mock.csv legacy format.
"""

import os
import json
import pandas as pd
import streamlit as st

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    DATA_FILE, DATA_COLUMNS, CACHE_TTL,
    USERS_FILE, CLAIMS_FILE, ENTITIES_FILE, EVIDENCE_FILE,
    CONFIDENCE_SCORES
)


# ============================================================================
# LEGACY CSV FUNCTIONS (backward compatibility)
# ============================================================================

@st.cache_data(ttl=CACHE_TTL)
def load_data() -> pd.DataFrame:
    """
    LEGACY: Load data từ CSV file.
    
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
    LEGACY: Lưu DataFrame vào CSV file.
    
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
    LEGACY: Trích xuất danh sách User ID duy nhất từ cột Source.
    
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
    LEGACY: Thêm một claim mới vào CSV.
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


# ============================================================================
# NEW JSON SCHEMA FUNCTIONS
# ============================================================================

def _load_json(filepath: str) -> list:
    """Helper: Load JSON file."""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def _save_json(filepath: str, data: list) -> bool:
    """Helper: Save JSON file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Lỗi khi lưu file: {str(e)}")
        return False


@st.cache_data(ttl=CACHE_TTL)
def load_users() -> list:
    """Load User nodes từ JSON."""
    return _load_json(USERS_FILE)


@st.cache_data(ttl=CACHE_TTL)
def load_claims() -> list:
    """Load Claim nodes từ JSON."""
    return _load_json(CLAIMS_FILE)


@st.cache_data(ttl=CACHE_TTL)
def load_entities() -> list:
    """Load Entity nodes từ JSON."""
    return _load_json(ENTITIES_FILE)


@st.cache_data(ttl=CACHE_TTL)
def load_evidence() -> list:
    """Load Evidence nodes từ JSON."""
    return _load_json(EVIDENCE_FILE)


def get_user_ids_from_json() -> list:
    """Get list of user IDs từ users.json."""
    users = load_users()
    return sorted([u.get('user_id', '') for u in users if u.get('user_id')])


def get_claims_by_user(user_id: str) -> list:
    """Get claims của một user cụ thể."""
    claims = load_claims()
    return [c for c in claims if c.get('user_id') == user_id]


def save_claim(claim_data: dict) -> bool:
    """
    Lưu một Claim mới vào JSON.
    
    Args:
        claim_data: Dictionary chứa claim data
        
    Returns:
        True nếu thành công
    """
    claims = load_claims()
    claims.append(claim_data)
    
    # Clear cache
    load_claims.clear()
    
    return _save_json(CLAIMS_FILE, claims)


def save_entity(entity_data: dict) -> bool:
    """Lưu một Entity mới vào JSON."""
    entities = load_entities()
    
    # Check if entity already exists (by canonical_id)
    canonical_id = entity_data.get('canonical_id')
    if canonical_id and any(e.get('canonical_id') == canonical_id for e in entities):
        return True  # Already exists, skip
    
    entities.append(entity_data)
    load_entities.clear()
    return _save_json(ENTITIES_FILE, entities)


def save_evidence_item(evidence_data: dict) -> bool:
    """Lưu một Evidence mới vào JSON."""
    evidence_list = load_evidence()
    evidence_list.append(evidence_data)
    load_evidence.clear()
    return _save_json(EVIDENCE_FILE, evidence_list)


# ============================================================================
# HYBRID FUNCTIONS - Works với cả CSV và JSON
# ============================================================================

def get_all_user_ids() -> list:
    """
    Get tất cả user IDs từ cả CSV (legacy) và JSON (new schema).
    
    Returns:
        List unique user IDs
    """
    # From legacy CSV
    csv_users = get_unique_user_ids(load_data())
    
    # From new JSON
    json_users = get_user_ids_from_json()
    
    # Combine and deduplicate
    all_users = list(set(csv_users + json_users))
    return sorted(all_users)


def get_documents_and_metadata(use_json: bool = True) -> tuple:
    """
    Get documents và metadata cho RAG.
    Hỗ trợ cả legacy CSV và JSON schema mới.
    
    Args:
        use_json: True = dùng JSON schema mới, False = dùng CSV legacy
        
    Returns:
        Tuple: (documents: list, metadata: list)
    """
    if use_json and os.path.exists(CLAIMS_FILE):
        # New JSON schema
        claims = load_claims()
        documents = []
        metadata = []
        
        for claim in claims:
            # Document = content_summary để RAG search
            documents.append(claim.get('content_summary', ''))
            
            # Metadata cho gatekeeper filtering
            metadata.append({
                'user_id': claim.get('user_id'),
                'source': claim.get('user_id'),  # Backward compat
                'access_level': claim.get('access_level', 'public'),
                'status': claim.get('status', 'self_declared'),
                'verified': claim.get('status') in ['attested'],
                'confidence_score': claim.get('confidence_score', CONFIDENCE_SCORES['base_self_declared']),
                'topic': claim.get('topic'),
                'claim_id': claim.get('claim_id'),
                'eas_uid': claim.get('eas_uid'),
                'entity_ids': claim.get('entity_ids', [])
            })
        
        return documents, metadata
    
    else:
        # Legacy CSV schema
        df = load_data()
        if df.empty:
            return [], []
        
        # Build document strings
        documents = []
        metadata = []
        
        for _, row in df.iterrows():
            # Legacy format: "Source HAS_SKILL Target"
            doc = f"{row['Source']} {row['Relation']} {row['Target']}"
            documents.append(doc)
            
            metadata.append({
                'source': row['Source'],
                'user_id': row['Source'],  # New schema compat
                'access_level': row.get('Access_Level', 'public'),
                'status': row.get('Status', 'self_declared'),
                'verified': row.get('Status') in ['attested', 'self_declared'],
                'confidence_score': CONFIDENCE_SCORES['base_self_declared'] if row.get('Status') != 'attested' else CONFIDENCE_SCORES['with_attestation']
            })
        
        return documents, metadata


def clear_all_caches():
    """Clear all cached data loaders."""
    load_data.clear()
    load_users.clear()
    load_claims.clear()
    load_entities.clear()
    load_evidence.clear()

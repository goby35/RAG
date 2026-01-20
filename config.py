# config.py - Configuration và Constants cho Graph-based RAG
import os
import streamlit as st

# ============================================================================
# API CONFIGURATION
# ============================================================================
def init_api_keys():
    """Initialize API keys từ Streamlit secrets."""
    os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']


def get_openai_api_key():
    """Get OpenAI API key."""
    return os.environ.get('OPENAI_API_KEY', '')


# ============================================================================
# FILE PATHS
# ============================================================================
# Legacy data file (for backward compatibility)
DATA_FILE = 'data_mock.csv'

# New Graph-based data files
USERS_FILE = 'data/users.json'
CLAIMS_FILE = 'data/claims.json'
ENTITIES_FILE = 'data/entities.json'
EVIDENCE_FILE = 'data/evidence.json'

# ============================================================================
# DATA SCHEMA - LEGACY (backward compatibility)
# ============================================================================
DATA_COLUMNS = ['Source', 'Relation', 'Target', 'Evidence', 'Access_Level', 'Status']

# ============================================================================
# ACCESS LEVELS - Mức độ truy cập
# ============================================================================
ACCESS_LEVELS = {
    'public': 'Công khai - Ai cũng xem được',
    'private': 'Riêng tư - Chỉ Owner xem',
    'connections_only': 'Chỉ kết nối - Connections xem',
    'recruiter': 'Nhà tuyển dụng - Recruiter xem'
}

# ============================================================================
# CLAIM STATUS - Trạng thái xác thực
# ============================================================================
STATUS_OPTIONS = {
    'pending': 'Chờ xác thực',
    'self_declared': 'Tự khai báo',
    'attested': 'Đã xác thực (EAS)',
    'revoked': 'Đã thu hồi'
}

# Statuses that are considered "verified" for RAG
VERIFIED_STATUSES = ['attested', 'self_declared']

# ============================================================================
# CONFIDENCE SCORE - Logic tính điểm tin cậy
# ============================================================================
CONFIDENCE_SCORES = {
    'base_self_declared': 0.3,     # Điểm cơ bản cho tự khai báo
    'with_evidence': 0.5,          # Có bằng chứng (Github, Link)
    'with_attestation': 0.9,       # Có EAS attestation
    'trusted_organization': 1.0   # Xác thực từ tổ chức uy tín
}

# Minimum confidence thresholds
MIN_CONFIDENCE_FOR_RAG = 0.3      # Tối thiểu để đưa vào RAG
MIN_CONFIDENCE_TRUSTED = 0.8      # Coi là đáng tin cậy

# ============================================================================
# ENTITY TYPES - Loại Entity
# ============================================================================
ENTITY_TYPES = {
    'Skill': 'Kỹ năng',
    'Organization': 'Tổ chức/Công ty',
    'Project': 'Dự án',
    'Certificate': 'Chứng chỉ',
    'Education': 'Học vấn',
    'Achievement': 'Thành tựu'
}

# ============================================================================
# CLAIM TOPICS - Phân loại chủ đề Claims
# ============================================================================
CLAIM_TOPICS = {
    'skill': 'Skill Proficiency',
    'project': 'Project Contribution',
    'work': 'Work Experience',
    'education': 'Education',
    'certificate': 'Certification',
    'achievement': 'Achievement',
    'other': 'Other'
}

# Map từ category cũ sang topic mới
CATEGORY_TO_TOPIC = {
    'skills': 'skill',
    'projects': 'project', 
    'work_experience': 'work',
    'education': 'education',
    'certifications': 'certificate',
    'achievements': 'achievement',
    'bio': 'other'
}

# ============================================================================
# MODEL CONFIGURATIONS
# ============================================================================
EMBEDDING_MODEL = 'paraphrase-mpnet-base-v2'
LLM_MODEL = 'gpt-4o-mini'

# ============================================================================
# RAG SETTINGS
# ============================================================================
DEFAULT_TOP_K = 5
MAX_TOKENS_SUMMARY = 200
MAX_TOKENS_RESPONSE = 512

# ============================================================================
# CACHE SETTINGS
# ============================================================================
CACHE_TTL = 60  # seconds

# ============================================================================
# USER ROLES
# ============================================================================
USER_ROLES = {
    'freelancer': 'Freelancer',
    'recruiter': 'Nhà tuyển dụng',
    'verifier': 'Người xác thực',
    'organization': 'Tổ chức'
}

# ============================================================================
# EVIDENCE TYPES
# ============================================================================
EVIDENCE_TYPES = {
    'PDF': 'Tài liệu PDF',
    'Image': 'Hình ảnh',
    'Link': 'Đường dẫn',
    'GithubRepo': 'Github Repository',
    'LinkedIn': 'LinkedIn Profile',
    'Certificate': 'Chứng chỉ'
}

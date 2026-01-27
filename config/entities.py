# config/entities.py
"""
Entity type configurations and mappings.
"""

from dataclasses import dataclass
from typing import Dict, List
from enum import Enum


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""
    SKILL = "Skill"
    ORGANIZATION = "Organization"
    PROJECT = "Project"
    CERTIFICATE = "Certificate"
    EDUCATION = "Education"
    ACHIEVEMENT = "Achievement"


class EvidenceType(str, Enum):
    """Types of evidence."""
    PDF = "PDF"
    IMAGE = "Image"
    LINK = "Link"
    GITHUB_REPO = "GithubRepo"
    LINKEDIN = "LinkedIn"
    CERTIFICATE = "Certificate"


class UserRole(str, Enum):
    """User roles."""
    FREELANCER = "Freelancer"
    RECRUITER = "Recruiter"
    VERIFIER = "Verifier"
    ORGANIZATION = "Organization"


class ClaimTopic(str, Enum):
    """Claim topic categories."""
    SKILL = "skill"
    PROJECT = "project"
    WORK = "work"
    EDUCATION = "education"
    CERTIFICATE = "certificate"
    ACHIEVEMENT = "achievement"
    OTHER = "other"


@dataclass
class EntityConfig:
    """Configuration for entity types and mappings."""
    
    # Entity type labels (Vietnamese)
    ENTITY_TYPE_LABELS: Dict[str, str] = None
    
    # Claim topic labels
    CLAIM_TOPIC_LABELS: Dict[str, str] = None
    
    # Category to topic mapping
    CATEGORY_TO_TOPIC: Dict[str, str] = None
    
    # Evidence type labels
    EVIDENCE_TYPE_LABELS: Dict[str, str] = None
    
    # User role labels
    USER_ROLE_LABELS: Dict[str, str] = None
    
    def __post_init__(self):
        if self.ENTITY_TYPE_LABELS is None:
            self.ENTITY_TYPE_LABELS = {
                'Skill': 'Kỹ năng',
                'Organization': 'Tổ chức/Công ty',
                'Project': 'Dự án',
                'Certificate': 'Chứng chỉ',
                'Education': 'Học vấn',
                'Achievement': 'Thành tựu',
            }
        
        if self.CLAIM_TOPIC_LABELS is None:
            self.CLAIM_TOPIC_LABELS = {
                'skill': 'Skill Proficiency',
                'project': 'Project Contribution',
                'work': 'Work Experience',
                'education': 'Education',
                'certificate': 'Certification',
                'achievement': 'Achievement',
                'other': 'Other',
            }
        
        if self.CATEGORY_TO_TOPIC is None:
            self.CATEGORY_TO_TOPIC = {
                'skills': 'skill',
                'projects': 'project',
                'work_experience': 'work',
                'education': 'education',
                'certifications': 'certificate',
                'achievements': 'achievement',
                'bio': 'other',
            }
        
        if self.EVIDENCE_TYPE_LABELS is None:
            self.EVIDENCE_TYPE_LABELS = {
                'PDF': 'Tài liệu PDF',
                'Image': 'Hình ảnh',
                'Link': 'Đường dẫn',
                'GithubRepo': 'Github Repository',
                'LinkedIn': 'LinkedIn Profile',
                'Certificate': 'Chứng chỉ',
            }
        
        if self.USER_ROLE_LABELS is None:
            self.USER_ROLE_LABELS = {
                'freelancer': 'Freelancer',
                'recruiter': 'Nhà tuyển dụng',
                'verifier': 'Người xác thực',
                'organization': 'Tổ chức',
            }


# Singleton instance
_entity_config = EntityConfig()


# Backward compatibility exports
ENTITY_TYPES = _entity_config.ENTITY_TYPE_LABELS
CLAIM_TOPICS = _entity_config.CLAIM_TOPIC_LABELS
CATEGORY_TO_TOPIC = _entity_config.CATEGORY_TO_TOPIC
EVIDENCE_TYPES = _entity_config.EVIDENCE_TYPE_LABELS
USER_ROLES = _entity_config.USER_ROLE_LABELS

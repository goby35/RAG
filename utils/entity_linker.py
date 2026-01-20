# utils/entity_linker.py - Entity Linking Service
"""
Entity Linker - Map các tên Entity về Canonical ID.

Logic:
- Input: "Py", "Python 3", "Snake Lang"
- Entity Linking Service: Map tất cả về "tech_python"
- Giúp Graph không bị phân mảnh (Fragmented).

Tương lai: Có thể dùng LLM để suggest mapping thông minh hơn.
"""

from typing import Optional, List, Dict
import json
import os

# ============================================================================
# KNOWLEDGE BASE - Entity Mapping
# ============================================================================

# Mapping từ alias về canonical_id
ENTITY_ALIASES = {
    # === PROGRAMMING LANGUAGES ===
    "python": "tech_python",
    "py": "tech_python",
    "python 3": "tech_python",
    "python3": "tech_python",
    "snake lang": "tech_python",
    
    "javascript": "tech_javascript",
    "js": "tech_javascript",
    "es6": "tech_javascript",
    "ecmascript": "tech_javascript",
    
    "typescript": "tech_typescript",
    "ts": "tech_typescript",
    
    "java": "tech_java",
    "jdk": "tech_java",
    
    "c++": "tech_cpp",
    "cpp": "tech_cpp",
    "c plus plus": "tech_cpp",
    
    "c#": "tech_csharp",
    "csharp": "tech_csharp",
    "c sharp": "tech_csharp",
    
    "golang": "tech_go",
    "go": "tech_go",
    
    "rust": "tech_rust",
    
    "ruby": "tech_ruby",
    
    "php": "tech_php",
    
    "swift": "tech_swift",
    
    "kotlin": "tech_kotlin",
    
    "r": "tech_r",
    "r language": "tech_r",
    
    "sql": "tech_sql",
    "mysql": "tech_mysql",
    "postgresql": "tech_postgresql",
    "postgres": "tech_postgresql",
    "mongodb": "tech_mongodb",
    "mongo": "tech_mongodb",
    
    # === FRAMEWORKS & LIBRARIES ===
    "react": "framework_react",
    "reactjs": "framework_react",
    "react.js": "framework_react",
    
    "vue": "framework_vue",
    "vuejs": "framework_vue",
    "vue.js": "framework_vue",
    
    "angular": "framework_angular",
    "angularjs": "framework_angular",
    
    "django": "framework_django",
    "flask": "framework_flask",
    "fastapi": "framework_fastapi",
    "fast api": "framework_fastapi",
    
    "nodejs": "runtime_nodejs",
    "node.js": "runtime_nodejs",
    "node": "runtime_nodejs",
    
    "express": "framework_express",
    "expressjs": "framework_express",
    
    "nextjs": "framework_nextjs",
    "next.js": "framework_nextjs",
    "next": "framework_nextjs",
    
    "tensorflow": "lib_tensorflow",
    "tf": "lib_tensorflow",
    
    "pytorch": "lib_pytorch",
    "torch": "lib_pytorch",
    
    "pandas": "lib_pandas",
    "numpy": "lib_numpy",
    "scikit-learn": "lib_sklearn",
    "sklearn": "lib_sklearn",
    
    "langchain": "lib_langchain",
    "openai": "lib_openai",
    
    # === TOOLS & PLATFORMS ===
    "git": "tool_git",
    "github": "platform_github",
    "gitlab": "platform_gitlab",
    "bitbucket": "platform_bitbucket",
    
    "docker": "tool_docker",
    "kubernetes": "tool_kubernetes",
    "k8s": "tool_kubernetes",
    
    "aws": "cloud_aws",
    "amazon web services": "cloud_aws",
    "gcp": "cloud_gcp",
    "google cloud": "cloud_gcp",
    "google cloud platform": "cloud_gcp",
    "azure": "cloud_azure",
    "microsoft azure": "cloud_azure",
    
    "linux": "os_linux",
    "ubuntu": "os_ubuntu",
    "centos": "os_centos",
    "windows": "os_windows",
    "macos": "os_macos",
    "mac os": "os_macos",
    
    # === CONCEPTS & SKILLS ===
    "machine learning": "skill_ml",
    "ml": "skill_ml",
    
    "deep learning": "skill_dl",
    "dl": "skill_dl",
    
    "artificial intelligence": "skill_ai",
    "ai": "skill_ai",
    
    "natural language processing": "skill_nlp",
    "nlp": "skill_nlp",
    
    "computer vision": "skill_cv",
    "cv": "skill_cv",
    
    "data science": "skill_datascience",
    "data analysis": "skill_dataanalysis",
    
    "web development": "skill_webdev",
    "web dev": "skill_webdev",
    "frontend": "skill_frontend",
    "backend": "skill_backend",
    "fullstack": "skill_fullstack",
    "full stack": "skill_fullstack",
    
    "devops": "skill_devops",
    "ci/cd": "skill_cicd",
    "cicd": "skill_cicd",
    
    "agile": "method_agile",
    "scrum": "method_scrum",
    
    # === CERTIFICATES ===
    "aws certified": "cert_aws",
    "aws solutions architect": "cert_aws_sa",
    "gcp certified": "cert_gcp",
    "azure certified": "cert_azure",
    "pmp": "cert_pmp",
    "ielts": "cert_ielts",
    "toefl": "cert_toefl",
    "toeic": "cert_toeic",
    
    # === EDUCATION ===
    "bachelor": "edu_bachelor",
    "bs": "edu_bachelor",
    "bachelor of science": "edu_bachelor",
    "master": "edu_master",
    "ms": "edu_master",
    "master of science": "edu_master",
    "phd": "edu_phd",
    "doctorate": "edu_phd",
    "mba": "edu_mba",
    
    "computer science": "field_cs",
    "cs": "field_cs",
    "software engineering": "field_se",
    "information technology": "field_it",
    "it": "field_it",
    "data science": "field_datascience",
}

# Canonical entity details
CANONICAL_ENTITIES = {
    "tech_python": {
        "name": "Python",
        "entity_type": "Skill",
        "description": "Python programming language"
    },
    "tech_javascript": {
        "name": "JavaScript",
        "entity_type": "Skill",
        "description": "JavaScript programming language"
    },
    "framework_react": {
        "name": "React",
        "entity_type": "Skill",
        "description": "React JavaScript library for building user interfaces"
    },
    "skill_ml": {
        "name": "Machine Learning",
        "entity_type": "Skill",
        "description": "Machine Learning expertise"
    },
    "skill_nlp": {
        "name": "Natural Language Processing",
        "entity_type": "Skill",
        "description": "NLP expertise"
    },
    # ... Add more as needed
}


# ============================================================================
# ENTITY LINKER CLASS
# ============================================================================

class EntityLinker:
    """
    Entity Linker - Map các tên thực thể về canonical ID.
    """
    
    def __init__(self, custom_aliases: Dict[str, str] = None):
        """
        Initialize với optional custom aliases.
        
        Args:
            custom_aliases: Dict mapping alias -> canonical_id
        """
        self.aliases = ENTITY_ALIASES.copy()
        if custom_aliases:
            self.aliases.update(custom_aliases)
        self.canonical_entities = CANONICAL_ENTITIES.copy()
    
    def link(self, entity_text: str) -> Optional[str]:
        """
        Map entity text về canonical_id.
        
        Args:
            entity_text: Tên entity từ input (e.g., "Py", "Python 3")
            
        Returns:
            canonical_id hoặc None nếu không tìm thấy
        """
        normalized = entity_text.lower().strip()
        return self.aliases.get(normalized)
    
    def link_or_create(self, entity_text: str, entity_type: str = "Skill") -> str:
        """
        Map entity text về canonical_id, tạo mới nếu chưa có.
        
        Args:
            entity_text: Tên entity
            entity_type: Loại entity (Skill, Organization, etc.)
            
        Returns:
            canonical_id
        """
        existing = self.link(entity_text)
        if existing:
            return existing
        
        # Tạo canonical_id mới từ text
        canonical_id = self._generate_canonical_id(entity_text, entity_type)
        
        # Thêm vào aliases
        self.aliases[entity_text.lower().strip()] = canonical_id
        
        return canonical_id
    
    def _generate_canonical_id(self, entity_text: str, entity_type: str) -> str:
        """Generate canonical_id từ text."""
        # Normalize: lowercase, replace spaces với underscore
        normalized = entity_text.lower().strip()
        normalized = normalized.replace(" ", "_")
        normalized = "".join(c for c in normalized if c.isalnum() or c == "_")
        
        # Prefix với entity type
        type_prefix = {
            "Skill": "skill",
            "Organization": "org",
            "Project": "proj",
            "Certificate": "cert",
            "Education": "edu",
            "Achievement": "achieve"
        }
        prefix = type_prefix.get(entity_type, "entity")
        
        return f"{prefix}_{normalized}"
    
    def get_entity_info(self, canonical_id: str) -> Optional[dict]:
        """Get entity details từ canonical_id."""
        return self.canonical_entities.get(canonical_id)
    
    def bulk_link(self, entities: List[str]) -> Dict[str, Optional[str]]:
        """
        Map nhiều entities cùng lúc.
        
        Args:
            entities: List các tên entity
            
        Returns:
            Dict mapping entity_text -> canonical_id
        """
        return {entity: self.link(entity) for entity in entities}
    
    def add_alias(self, alias: str, canonical_id: str):
        """Add alias mới."""
        self.aliases[alias.lower().strip()] = canonical_id
    
    def save_to_file(self, filepath: str = "data/entity_aliases.json"):
        """Save aliases ra file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.aliases, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: str = "data/entity_aliases.json"):
        """Load aliases từ file."""
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                custom_aliases = json.load(f)
                self.aliases.update(custom_aliases)


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_entity_linker = None

def get_entity_linker() -> EntityLinker:
    """Get singleton instance của EntityLinker."""
    global _entity_linker
    if _entity_linker is None:
        _entity_linker = EntityLinker()
    return _entity_linker


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def link_entity(entity_text: str) -> Optional[str]:
    """Quick link entity về canonical_id."""
    return get_entity_linker().link(entity_text)


def link_entities(entities: List[str]) -> Dict[str, Optional[str]]:
    """Quick link nhiều entities."""
    return get_entity_linker().bulk_link(entities)


def link_or_create_entity(entity_text: str, entity_type: str = "Skill") -> str:
    """Link hoặc tạo mới entity."""
    return get_entity_linker().link_or_create(entity_text, entity_type)

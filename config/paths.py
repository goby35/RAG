# config/paths.py
"""
File paths and directory configuration.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PathConfig:
    """
    Configuration for file paths and directories.
    
    All paths are relative to the project root.
    """
    
    # Project root (auto-detected)
    _root: Optional[Path] = None
    
    # Data directories
    DATA_DIR: str = "data"
    
    # Legacy data file
    LEGACY_DATA_FILE: str = "data_mock.csv"
    
    # JSON data files
    USERS_FILE: str = "data/users.json"
    CLAIMS_FILE: str = "data/claims.json"
    ENTITIES_FILE: str = "data/entities.json"
    EVIDENCE_FILE: str = "data/evidence.json"
    
    # Documentation
    DOCS_DIR: str = "docs"
    
    @property
    def root(self) -> Path:
        """Get project root directory."""
        if self._root is None:
            # Auto-detect from this file's location
            self._root = Path(__file__).parent.parent
        return self._root
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Get absolute path from relative path."""
        return self.root / relative_path
    
    def ensure_data_dir(self) -> Path:
        """Ensure data directory exists and return path."""
        data_path = self.get_absolute_path(self.DATA_DIR)
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path
    
    @property
    def users_file(self) -> Path:
        return self.get_absolute_path(self.USERS_FILE)
    
    @property
    def claims_file(self) -> Path:
        return self.get_absolute_path(self.CLAIMS_FILE)
    
    @property
    def entities_file(self) -> Path:
        return self.get_absolute_path(self.ENTITIES_FILE)
    
    @property
    def evidence_file(self) -> Path:
        return self.get_absolute_path(self.EVIDENCE_FILE)
    
    @property
    def legacy_data_file(self) -> Path:
        return self.get_absolute_path(self.LEGACY_DATA_FILE)
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists."""
        return self.get_absolute_path(relative_path).exists()


# Singleton instance
_path_config: Optional[PathConfig] = None


def get_path_config() -> PathConfig:
    """Get the global path config instance."""
    global _path_config
    if _path_config is None:
        _path_config = PathConfig()
    return _path_config


# Backward compatibility exports
DATA_FILE = 'data_mock.csv'
USERS_FILE = 'data/users.json'
CLAIMS_FILE = 'data/claims.json'
ENTITIES_FILE = 'data/entities.json'
EVIDENCE_FILE = 'data/evidence.json'
DATA_COLUMNS = ['Source', 'Relation', 'Target', 'Evidence', 'Access_Level', 'Status']
CACHE_TTL = 60  # seconds

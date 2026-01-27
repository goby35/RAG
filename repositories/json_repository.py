# repositories/json_repository.py
"""
JSON File Repository - Generic JSON file storage.
"""

import os
import json
from typing import List, Dict, Any, Optional, TypeVar, Generic
from pathlib import Path
import logging
from threading import Lock

from core.base import BaseRepository
from core.exceptions import DataNotFoundError
from config.paths import get_path_config

logger = logging.getLogger(__name__)
T = TypeVar('T', bound=Dict[str, Any])


class JSONRepository(BaseRepository, Generic[T]):
    """
    Generic repository for JSON file storage.
    
    Provides thread-safe read/write operations for JSON files.
    """
    
    def __init__(
        self,
        file_path: str,
        id_field: str = "id",
        entity_name: str = "Entity"
    ):
        super().__init__(entity_name)
        self._file_path = Path(file_path)
        self._id_field = id_field
        self._lock = Lock()
        self._cache: Optional[List[T]] = None
    
    @property
    def file_path(self) -> Path:
        return self._file_path
    
    def _ensure_file_exists(self) -> None:
        """Ensure the data file exists."""
        if not self._file_path.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_data([])
    
    def _load_data(self) -> List[T]:
        """Load data from JSON file."""
        self._ensure_file_exists()
        
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file {self._file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load {self._file_path}: {e}")
            return []
    
    def _save_data(self, data: List[T]) -> bool:
        """Save data to JSON file."""
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._cache = data
            return True
        except Exception as e:
            logger.error(f"Failed to save {self._file_path}: {e}")
            return False
    
    def get_all(self) -> List[T]:
        """Get all entities."""
        with self._lock:
            if self._cache is not None:
                return self._cache.copy()
            
            data = self._load_data()
            self._cache = data
            return data.copy()
    
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        self._log_operation("get", entity_id)
        
        data = self.get_all()
        for item in data:
            if item.get(self._id_field) == entity_id:
                return item
        return None
    
    def create(self, entity: T) -> T:
        """Create a new entity."""
        self._log_operation("create")
        
        with self._lock:
            data = self._load_data()
            data.append(entity)
            
            if self._save_data(data):
                return entity
            raise RuntimeError(f"Failed to save {self._entity_name}")
    
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        entity_id = entity.get(self._id_field)
        self._log_operation("update", entity_id)
        
        with self._lock:
            data = self._load_data()
            
            for i, item in enumerate(data):
                if item.get(self._id_field) == entity_id:
                    data[i] = entity
                    if self._save_data(data):
                        return entity
                    raise RuntimeError(f"Failed to save {self._entity_name}")
            
            raise DataNotFoundError(self._entity_name, entity_id)
    
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by ID."""
        self._log_operation("delete", entity_id)
        
        with self._lock:
            data = self._load_data()
            original_len = len(data)
            
            data = [item for item in data if item.get(self._id_field) != entity_id]
            
            if len(data) < original_len:
                return self._save_data(data)
            return False
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        return self.get_by_id(entity_id) is not None
    
    def find_by(self, **criteria) -> List[T]:
        """Find entities matching criteria."""
        data = self.get_all()
        
        results = []
        for item in data:
            match = all(
                item.get(key) == value
                for key, value in criteria.items()
            )
            if match:
                results.append(item)
        
        return results
    
    def count(self) -> int:
        """Get total count of entities."""
        return len(self.get_all())
    
    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache = None
    
    def bulk_create(self, entities: List[T]) -> List[T]:
        """Create multiple entities at once."""
        self._log_operation("bulk_create")
        
        with self._lock:
            data = self._load_data()
            data.extend(entities)
            
            if self._save_data(data):
                return entities
            raise RuntimeError(f"Failed to bulk save {self._entity_name}")

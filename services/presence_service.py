# services/presence_service.py
"""
Presence Service - User presence management for Human-First routing.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

from core.base import BaseService
from core.interfaces import IPresenceManager
from core.exceptions import PresenceError

logger = logging.getLogger(__name__)


class PresenceStatus(str, Enum):
    """User presence status."""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class PresenceInfo:
    """Information about a user's presence status."""
    user_id: str
    user_name: str
    status: PresenceStatus
    last_seen: Optional[datetime]
    is_available_for_chat: bool
    
    @property
    def status_emoji(self) -> str:
        """Get emoji for status."""
        return {
            PresenceStatus.ONLINE: "🟢",
            PresenceStatus.AWAY: "🟡",
            PresenceStatus.BUSY: "🔴",
            PresenceStatus.OFFLINE: "⚫"
        }.get(self.status, "⚫")
    
    @property
    def status_text(self) -> str:
        """Get human-readable status text."""
        return {
            PresenceStatus.ONLINE: "Đang hoạt động",
            PresenceStatus.AWAY: "Vắng mặt",
            PresenceStatus.BUSY: "Đang bận",
            PresenceStatus.OFFLINE: "Ngoại tuyến"
        }.get(self.status, "Không xác định")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_available_for_chat": self.is_available_for_chat,
            "status_emoji": self.status_emoji,
            "status_text": self.status_text
        }


class PresenceService(BaseService, IPresenceManager):
    """
    Service for managing user presence.
    
    Tracks:
    - Online/offline status
    - Last activity time
    - Availability for chat
    """
    
    INACTIVITY_THRESHOLD = timedelta(minutes=5)
    
    def __init__(self, neo4j_client=None):
        super().__init__("PresenceService")
        self._neo4j_client = neo4j_client
        self._presence_cache: Dict[str, PresenceInfo] = {}
    
    def set_neo4j_client(self, client) -> None:
        """Set Neo4j client."""
        self._neo4j_client = client
    
    def get_status(self, user_id: str) -> Optional[str]:
        """Get user's current presence status."""
        presence = self.get_user_presence(user_id)
        return presence.status.value if presence else None
    
    def set_status(self, user_id: str, status: str) -> bool:
        """Set user's presence status."""
        try:
            presence_status = PresenceStatus(status)
        except ValueError:
            raise PresenceError(f"Invalid presence status: {status}", user_id=user_id)
        
        return self._update_presence(user_id, presence_status)
    
    def get_online_users(self) -> List[str]:
        """Get list of online user IDs."""
        if not self._neo4j_client:
            return [uid for uid, p in self._presence_cache.items() 
                    if p.status == PresenceStatus.ONLINE]
        
        query = """
        MATCH (u:User)
        WHERE u.presence_status = 'online'
        RETURN u.user_id as user_id
        """
        
        try:
            result = self._neo4j_client.run_query(query)
            return [row["user_id"] for row in result]
        except Exception as e:
            logger.error(f"Failed to get online users: {e}")
            return []
    
    def is_available_for_chat(self, user_id: str) -> bool:
        """Check if user is available for direct chat."""
        presence = self.get_user_presence(user_id)
        return presence.is_available_for_chat if presence else False
    
    def get_user_presence(self, user_id: str) -> Optional[PresenceInfo]:
        """Get full presence information for a user."""
        # Check cache first
        if user_id in self._presence_cache:
            return self._presence_cache[user_id]
        
        if not self._neo4j_client:
            return None
        
        query = """
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session {is_active: true})
        RETURN u.user_id as user_id,
               u.name as user_name,
               u.presence_status as status,
               u.last_seen as last_seen,
               s IS NOT NULL as has_active_session
        """
        
        try:
            result = self._neo4j_client.run_query(query, {"user_id": user_id})
            
            if not result:
                return None
            
            row = result[0]
            status_str = row.get("status", "offline")
            
            if row.get("has_active_session"):
                status = PresenceStatus.ONLINE
            else:
                try:
                    status = PresenceStatus(status_str)
                except ValueError:
                    status = PresenceStatus.OFFLINE
            
            last_seen = row.get("last_seen")
            if last_seen and hasattr(last_seen, 'to_native'):
                last_seen = last_seen.to_native()
            
            presence = PresenceInfo(
                user_id=row["user_id"],
                user_name=row["user_name"] or user_id,
                status=status,
                last_seen=last_seen,
                is_available_for_chat=status in [PresenceStatus.ONLINE, PresenceStatus.AWAY]
            )
            
            self._presence_cache[user_id] = presence
            return presence
            
        except Exception as e:
            logger.error(f"Failed to get presence for {user_id}: {e}")
            return None
    
    def get_all_users_presence(self) -> List[PresenceInfo]:
        """Get presence info for all users."""
        if not self._neo4j_client:
            return list(self._presence_cache.values())
        
        query = """
        MATCH (u:User)
        OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session {is_active: true})
        RETURN u.user_id as user_id,
               u.name as user_name,
               u.presence_status as status,
               u.last_seen as last_seen,
               s IS NOT NULL as has_active_session
        ORDER BY 
            CASE WHEN s IS NOT NULL THEN 0
                 WHEN u.presence_status = 'online' THEN 1
                 WHEN u.presence_status = 'away' THEN 2
                 WHEN u.presence_status = 'busy' THEN 3
                 ELSE 4 END
        """
        
        try:
            result = self._neo4j_client.run_query(query)
            
            users = []
            for row in result:
                status_str = row.get("status", "offline")
                
                if row.get("has_active_session"):
                    status = PresenceStatus.ONLINE
                else:
                    try:
                        status = PresenceStatus(status_str)
                    except ValueError:
                        status = PresenceStatus.OFFLINE
                
                last_seen = row.get("last_seen")
                if last_seen and hasattr(last_seen, 'to_native'):
                    last_seen = last_seen.to_native()
                
                users.append(PresenceInfo(
                    user_id=row["user_id"],
                    user_name=row["user_name"] or row["user_id"],
                    status=status,
                    last_seen=last_seen,
                    is_available_for_chat=status in [PresenceStatus.ONLINE, PresenceStatus.AWAY]
                ))
            
            return users
            
        except Exception as e:
            logger.error(f"Failed to get all users presence: {e}")
            return []
    
    def _update_presence(self, user_id: str, status: PresenceStatus) -> bool:
        """Update presence status in database."""
        if not self._neo4j_client:
            # Update cache only
            if user_id in self._presence_cache:
                self._presence_cache[user_id].status = status
            return True
        
        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.presence_status = $status,
            u.last_seen = datetime()
        RETURN u
        """
        
        try:
            self._neo4j_client.run_query(query, {
                "user_id": user_id,
                "status": status.value
            })
            
            # Update cache
            if user_id in self._presence_cache:
                self._presence_cache[user_id].status = status
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update presence for {user_id}: {e}")
            return False
    
    def check_inactivity(self, user_id: str, last_activity: datetime) -> bool:
        """Check and update status if user is inactive."""
        now = datetime.now()
        inactive_time = now - last_activity
        
        if inactive_time > self.INACTIVITY_THRESHOLD:
            current_status = self.get_status(user_id)
            if current_status == PresenceStatus.ONLINE.value:
                return self.set_status(user_id, PresenceStatus.AWAY.value)
        
        return False
    
    def invalidate_cache(self, user_id: Optional[str] = None) -> None:
        """Invalidate presence cache."""
        if user_id:
            self._presence_cache.pop(user_id, None)
        else:
            self._presence_cache.clear()

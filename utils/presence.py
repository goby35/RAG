# utils/presence.py - Presence Status Management
"""
Presence Management Module for Human-First RAG.

Tracks and manages user online/offline status for message routing.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from utils.neo4j_client import Neo4jClient
from utils.auth import PresenceStatus


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


class PresenceManager:
    """
    Manages user presence status.
    
    Determines:
    - Who is online/offline
    - Who can receive direct messages
    - When to activate AI fallback
    """
    
    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize PresenceManager.
        
        Args:
            neo4j_client: Neo4j database client
        """
        self.client = neo4j_client
    
    # ========================================================================
    # Presence Queries
    # ========================================================================
    
    def get_user_presence(self, user_id: str) -> Optional[PresenceInfo]:
        """
        Get presence information for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            PresenceInfo or None
        """
        query = """
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session {is_active: true})
        RETURN u.user_id as user_id,
               u.name as user_name,
               u.presence_status as status,
               u.last_seen as last_seen,
               s IS NOT NULL as has_active_session
        """
        
        result = self.client.run_query(query, {"user_id": user_id})
        
        if not result:
            return None
        
        row = result[0]
        status_str = row.get("status", "offline")
        has_active_session = row.get("has_active_session", False)
        
        # Priority: Use database presence_status first
        # Session is just an additional indicator
        try:
            status = PresenceStatus(status_str)
        except ValueError:
            status = PresenceStatus.OFFLINE
        
        # If user has no active session and status is ONLINE, they're actually OFFLINE
        # (This handles stale status from crashed sessions)
        if not has_active_session and status == PresenceStatus.ONLINE:
            status = PresenceStatus.OFFLINE
        
        # Convert Neo4j DateTime if needed
        last_seen = row.get("last_seen")
        if last_seen and hasattr(last_seen, 'to_native'):
            last_seen = last_seen.to_native()
        
        return PresenceInfo(
            user_id=row["user_id"],
            user_name=row["user_name"],
            status=status,
            last_seen=last_seen,
            is_available_for_chat=status in [PresenceStatus.ONLINE, PresenceStatus.AWAY]
        )
    
    def get_online_users(self) -> List[PresenceInfo]:
        """
        Get all online users.
        
        Returns:
            List of PresenceInfo for online users
        """
        query = """
        MATCH (u:User)
        WHERE u.presence_status = 'online'
        OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session {is_active: true})
        RETURN u.user_id as user_id,
               u.name as user_name,
               u.presence_status as status,
               u.last_seen as last_seen
        """
        
        result = self.client.run_query(query)
        
        online_users = []
        for row in result:
            last_seen = row.get("last_seen")
            if last_seen and hasattr(last_seen, 'to_native'):
                last_seen = last_seen.to_native()
            
            online_users.append(PresenceInfo(
                user_id=row["user_id"],
                user_name=row["user_name"],
                status=PresenceStatus.ONLINE,
                last_seen=last_seen,
                is_available_for_chat=True
            ))
        
        return online_users
    
    def get_all_users_presence(self) -> List[PresenceInfo]:
        """
        Get presence info for all users.
        
        Returns:
            List of PresenceInfo for all users
        """
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
        
        result = self.client.run_query(query)
        
        users = []
        for row in result:
            status_str = row.get("status", "offline")
            has_active_session = row.get("has_active_session", False)
            
            # Priority: Use database presence_status first
            try:
                status = PresenceStatus(status_str)
            except ValueError:
                status = PresenceStatus.OFFLINE
            
            # If user has no active session and status is ONLINE, they're actually OFFLINE
            if not has_active_session and status == PresenceStatus.ONLINE:
                status = PresenceStatus.OFFLINE
            
            last_seen = row.get("last_seen")
            if last_seen and hasattr(last_seen, 'to_native'):
                last_seen = last_seen.to_native()
            
            users.append(PresenceInfo(
                user_id=row["user_id"],
                user_name=row["user_name"],
                status=status,
                last_seen=last_seen,
                is_available_for_chat=status in [PresenceStatus.ONLINE, PresenceStatus.AWAY]
            ))
        
        return users
    
    # ========================================================================
    # Presence Updates
    # ========================================================================
    
    def set_online(self, user_id: str) -> bool:
        """Set user status to online."""
        return self._update_status(user_id, PresenceStatus.ONLINE)
    
    def set_away(self, user_id: str) -> bool:
        """Set user status to away."""
        return self._update_status(user_id, PresenceStatus.AWAY)
    
    def set_busy(self, user_id: str) -> bool:
        """Set user status to busy."""
        return self._update_status(user_id, PresenceStatus.BUSY)
    
    def set_offline(self, user_id: str) -> bool:
        """Set user status to offline."""
        return self._update_status(user_id, PresenceStatus.OFFLINE)
    
    def _update_status(self, user_id: str, status: PresenceStatus) -> bool:
        """
        Update user presence status in database.
        
        Args:
            user_id: User ID
            status: New status
            
        Returns:
            True if successful
        """
        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.presence_status = $status, u.last_seen = datetime()
        RETURN u
        """
        
        result = self.client.run_query(query, {
            "user_id": user_id,
            "status": status.value
        })
        
        return len(result) > 0
    
    # ========================================================================
    # Routing Decisions
    # ========================================================================
    
    def should_use_ai_fallback(self, target_user_id: str) -> bool:
        """
        Determine if AI should respond instead of human.
        
        Args:
            target_user_id: User being messaged
            
        Returns:
            True if AI should respond
        """
        presence = self.get_user_presence(target_user_id)
        
        if presence is None:
            return True  # User doesn't exist, AI handles error
        
        # AI responds when user is offline
        return presence.status == PresenceStatus.OFFLINE
    
    def can_receive_direct_message(self, target_user_id: str) -> bool:
        """
        Check if user can receive direct messages.
        
        Args:
            target_user_id: User being messaged
            
        Returns:
            True if user can receive direct messages
        """
        presence = self.get_user_presence(target_user_id)
        
        if presence is None:
            return False
        
        return presence.is_available_for_chat
    
    def get_routing_decision(self, target_user_id: str) -> Dict[str, Any]:
        """
        Get full routing decision for a message.
        
        Args:
            target_user_id: User being messaged
            
        Returns:
            Dictionary with routing decision details
        """
        presence = self.get_user_presence(target_user_id)
        
        if presence is None:
            return {
                "route_to": "error",
                "reason": "User not found",
                "ai_fallback": False,
                "direct_message": False
            }
        
        if presence.status == PresenceStatus.ONLINE:
            return {
                "route_to": "human",
                "reason": "User is online",
                "ai_fallback": False,
                "direct_message": True,
                "presence": presence.to_dict()
            }
        
        if presence.status == PresenceStatus.AWAY:
            return {
                "route_to": "human_with_notification",
                "reason": "User is away, message will be queued",
                "ai_fallback": False,
                "direct_message": True,
                "presence": presence.to_dict()
            }
        
        if presence.status == PresenceStatus.BUSY:
            return {
                "route_to": "human_with_notification",
                "reason": "User is busy, only important messages",
                "ai_fallback": False,
                "direct_message": True,
                "presence": presence.to_dict()
            }
        
        # OFFLINE - AI Fallback
        return {
            "route_to": "ai_agent",
            "reason": "User is offline, AI will respond",
            "ai_fallback": True,
            "direct_message": False,
            "presence": presence.to_dict()
        }

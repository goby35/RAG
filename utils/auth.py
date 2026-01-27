# utils/auth.py - Authentication & Session Management
"""
Authentication Module for Human-First RAG.

Manages user authentication, session tracking, and role inference.
Roles are inferred from Graph relationships, not manually selected.
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import uuid

from utils.neo4j_client import Neo4jClient


class PresenceStatus(Enum):
    """User presence status."""
    ONLINE = "online"      # Active, can chat directly
    AWAY = "away"          # Inactive > 5 min, still logged in
    BUSY = "busy"          # Available but busy
    OFFLINE = "offline"    # Logged out, AI can represent


@dataclass
class UserSession:
    """Represents an active user session."""
    session_id: str
    user_id: str
    user_name: str
    login_at: datetime
    presence_status: PresenceStatus
    last_activity: datetime
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "login_at": self.login_at.isoformat(),
            "presence_status": self.presence_status.value,
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active
        }


class AuthManager:
    """
    Authentication and Session Manager.
    
    Handles:
    - User login/logout
    - Session management
    - Presence status tracking
    - Role inference from Graph
    """
    
    # Inactivity threshold in seconds (5 minutes)
    INACTIVITY_THRESHOLD = 300
    
    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize AuthManager.
        
        Args:
            neo4j_client: Neo4j database client
        """
        self.client = neo4j_client
    
    # ========================================================================
    # Authentication
    # ========================================================================
    
    def login(self, user_id: str) -> Optional[UserSession]:
        """
        Log in a user and create a session.
        
        Args:
            user_id: User ID to log in
            
        Returns:
            UserSession if successful, None otherwise
        """
        # Get user from database
        user = self.client.get_user(user_id)
        if not user:
            return None
        
        # Create session
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            user_name=user.get("name", user_id),
            login_at=now,
            presence_status=PresenceStatus.ONLINE,
            last_activity=now,
            is_active=True
        )
        
        # Save session to database
        self._create_session_in_db(session)
        
        # Update user presence
        self._update_user_presence(user_id, PresenceStatus.ONLINE)
        
        return session
    
    def logout(self, session: UserSession) -> bool:
        """
        Log out a user and close session.
        
        Args:
            session: Active session to close
            
        Returns:
            True if successful
        """
        # Close session in database
        self._close_session_in_db(session.session_id)
        
        # Update user presence to offline
        self._update_user_presence(session.user_id, PresenceStatus.OFFLINE)
        
        return True
    
    def get_available_users(self) -> List[Dict]:
        """
        Get list of users available for login.
        
        Returns:
            List of user dictionaries
        """
        return self.client.get_all_users()
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    def update_activity(self, session: UserSession) -> UserSession:
        """
        Update last activity time for session.
        
        Args:
            session: Session to update
            
        Returns:
            Updated session
        """
        session.last_activity = datetime.now()
        
        # Check if status should change from AWAY to ONLINE
        if session.presence_status == PresenceStatus.AWAY:
            session.presence_status = PresenceStatus.ONLINE
            self._update_user_presence(session.user_id, PresenceStatus.ONLINE)
        
        return session
    
    def check_inactivity(self, session: UserSession) -> UserSession:
        """
        Check for inactivity and update status if needed.
        
        Args:
            session: Session to check
            
        Returns:
            Updated session
        """
        now = datetime.now()
        inactive_seconds = (now - session.last_activity).total_seconds()
        
        if inactive_seconds > self.INACTIVITY_THRESHOLD:
            if session.presence_status == PresenceStatus.ONLINE:
                session.presence_status = PresenceStatus.AWAY
                self._update_user_presence(session.user_id, PresenceStatus.AWAY)
        
        return session
    
    def set_presence(self, session: UserSession, status: PresenceStatus) -> UserSession:
        """
        Manually set presence status.
        
        Args:
            session: Session to update
            status: New presence status
            
        Returns:
            Updated session
        """
        session.presence_status = status
        self._update_user_presence(session.user_id, status)
        return session
    
    # ========================================================================
    # Role Inference from Graph
    # ========================================================================
    
    def infer_relationship(self, viewer_id: str, target_id: str) -> str:
        """
        Infer relationship type between two users from Graph.
        
        This replaces manual role selection with automatic inference.
        
        Args:
            viewer_id: The user viewing
            target_id: The user being viewed
            
        Returns:
            Relationship type: SELF, FRIEND, COLLEAGUE, RECRUITING, STRANGER
        """
        if viewer_id == target_id:
            return "SELF"
        
        # Check direct relationships
        query = """
        MATCH (viewer:User {user_id: $viewer_id})-[r]-(target:User {user_id: $target_id})
        WHERE type(r) IN ['FRIEND', 'COLLEAGUE', 'RECRUITING']
        RETURN type(r) as relationship_type
        LIMIT 1
        """
        
        result = self.client.run_query(query, {
            "viewer_id": viewer_id,
            "target_id": target_id
        })
        
        if result:
            return result[0]["relationship_type"]
        
        return "STRANGER"
    
    def get_user_relationships(self, user_id: str) -> Dict[str, List[Dict]]:
        """
        Get all relationships for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with relationship types as keys
        """
        query = """
        MATCH (u:User {user_id: $user_id})-[r]-(other:User)
        WHERE type(r) IN ['FRIEND', 'COLLEAGUE', 'RECRUITING']
        RETURN type(r) as rel_type, other.user_id as other_id, other.name as other_name
        """
        
        result = self.client.run_query(query, {"user_id": user_id})
        
        relationships = {
            "FRIEND": [],
            "COLLEAGUE": [],
            "RECRUITING": []
        }
        
        for row in result:
            rel_type = row["rel_type"]
            if rel_type in relationships:
                relationships[rel_type].append({
                    "user_id": row["other_id"],
                    "name": row["other_name"]
                })
        
        return relationships
    
    # ========================================================================
    # Database Operations
    # ========================================================================
    
    def _create_session_in_db(self, session: UserSession):
        """Create session node in database."""
        # First, close any existing active sessions for this user
        close_old_query = """
        MATCH (u:User {user_id: $user_id})-[:HAS_SESSION]->(s:Session {is_active: true})
        SET s.is_active = false, s.logout_at = datetime()
        """
        self.client.run_query(close_old_query, {"user_id": session.user_id})
        
        # Create new session
        query = """
        MATCH (u:User {user_id: $user_id})
        CREATE (s:Session {
            session_id: $session_id,
            login_at: datetime($login_at),
            is_active: true
        })
        CREATE (u)-[:HAS_SESSION]->(s)
        RETURN s
        """
        self.client.run_query(query, {
            "user_id": session.user_id,
            "session_id": session.session_id,
            "login_at": session.login_at.isoformat()
        })
    
    def _close_session_in_db(self, session_id: str):
        """Close session in database."""
        query = """
        MATCH (s:Session {session_id: $session_id})
        SET s.is_active = false, s.logout_at = datetime()
        RETURN s
        """
        self.client.run_query(query, {"session_id": session_id})
    
    def _update_user_presence(self, user_id: str, status: PresenceStatus):
        """Update user presence status in database."""
        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.presence_status = $status, u.last_seen = datetime()
        RETURN u
        """
        self.client.run_query(query, {
            "user_id": user_id,
            "status": status.value
        })
    
    def get_user_presence(self, user_id: str) -> PresenceStatus:
        """
        Get current presence status for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            PresenceStatus
        """
        user = self.client.get_user(user_id)
        if not user:
            return PresenceStatus.OFFLINE
        
        status_str = user.get("presence_status", "offline")
        try:
            return PresenceStatus(status_str)
        except ValueError:
            return PresenceStatus.OFFLINE


# ============================================================================
# Streamlit Session State Helpers
# ============================================================================

def init_auth_session_state():
    """Initialize authentication in Streamlit session state."""
    if "auth_session" not in st.session_state:
        st.session_state.auth_session = None
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = None


def get_current_session() -> Optional[UserSession]:
    """Get current user session from Streamlit state."""
    return st.session_state.get("auth_session")


def is_logged_in() -> bool:
    """Check if user is logged in."""
    session = get_current_session()
    return session is not None and session.is_active


def get_current_user_id() -> Optional[str]:
    """Get current logged-in user ID."""
    session = get_current_session()
    return session.user_id if session else None


def get_current_user_name() -> Optional[str]:
    """Get current logged-in user name."""
    session = get_current_session()
    return session.user_name if session else None

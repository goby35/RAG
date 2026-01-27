# utils/chat_router.py - Human-First Message Routing
"""
Chat Router Module for Human-First RAG.

Implements the core principle: Human-to-Human first, AI only when human is unavailable.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from utils.neo4j_client import Neo4jClient
from utils.presence import PresenceManager, PresenceInfo
from utils.auth import PresenceStatus


class MessageType(Enum):
    """Types of messages in the system."""
    TEXT = "text"              # Regular text message
    SCHEDULE_REQUEST = "schedule_request"  # Request for meeting
    SCHEDULE_CONFIRM = "schedule_confirm"  # Confirm meeting
    CLAIM_SHARE = "claim_share"  # Sharing a claim
    SYSTEM = "system"          # System notification


class RouteType(Enum):
    """Where to route the message."""
    HUMAN_DIRECT = "human_direct"     # Direct to online human
    HUMAN_QUEUED = "human_queued"     # Queue for offline/away human
    AI_FALLBACK = "ai_fallback"       # AI responds on behalf
    ERROR = "error"                   # Error handling


@dataclass
class Message:
    """Represents a chat message."""
    message_id: str
    sender_id: str
    receiver_id: str
    content: str
    message_type: MessageType
    timestamp: datetime
    is_ai_response: bool = False
    ai_disclaimer: Optional[str] = None
    is_read: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "is_ai_response": self.is_ai_response,
            "ai_disclaimer": self.ai_disclaimer,
            "is_read": self.is_read,
            "metadata": self.metadata
        }


@dataclass
class RoutingResult:
    """Result of message routing decision."""
    route_type: RouteType
    message: Message
    receiver_presence: Optional[PresenceInfo]
    reason: str
    ai_should_respond: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_type": self.route_type.value,
            "message": self.message.to_dict(),
            "receiver_presence": self.receiver_presence.to_dict() if self.receiver_presence else None,
            "reason": self.reason,
            "ai_should_respond": self.ai_should_respond
        }


class ChatRouter:
    """
    Routes messages between users with Human-First priority.
    
    Flow:
    1. Check receiver's presence status
    2. If ONLINE/AWAY/BUSY -> Route to human (direct or queued)
    3. If OFFLINE -> AI Fallback responds
    4. Save message to graph
    """
    
    AI_DISCLAIMER = "🤖 Đây là phản hồi tự động từ AI khi người dùng vắng mặt. Nội dung dựa trên thông tin đã được xác thực trong hồ sơ."
    
    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize ChatRouter.
        
        Args:
            neo4j_client: Neo4j database client
        """
        self.client = neo4j_client
        self.presence_manager = PresenceManager(neo4j_client)
    
    # ========================================================================
    # Message Routing
    # ========================================================================
    
    def route_message(
        self, 
        sender_id: str, 
        receiver_id: str, 
        content: str,
        message_type: MessageType = MessageType.TEXT
    ) -> RoutingResult:
        """
        Route a message to appropriate destination.
        
        Args:
            sender_id: Sender user ID
            receiver_id: Receiver user ID
            content: Message content
            message_type: Type of message
            
        Returns:
            RoutingResult with routing decision
        """
        # Create message object
        message = Message(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type,
            timestamp=datetime.now()
        )
        
        # Get receiver presence
        receiver_presence = self.presence_manager.get_user_presence(receiver_id)
        
        if receiver_presence is None:
            return RoutingResult(
                route_type=RouteType.ERROR,
                message=message,
                receiver_presence=None,
                reason="Người nhận không tồn tại"
            )
        
        # Route based on presence
        if receiver_presence.status == PresenceStatus.ONLINE:
            return RoutingResult(
                route_type=RouteType.HUMAN_DIRECT,
                message=message,
                receiver_presence=receiver_presence,
                reason="Người nhận đang online, tin nhắn sẽ được gửi trực tiếp"
            )
        
        if receiver_presence.status in [PresenceStatus.AWAY, PresenceStatus.BUSY]:
            return RoutingResult(
                route_type=RouteType.HUMAN_QUEUED,
                message=message,
                receiver_presence=receiver_presence,
                reason=f"Người nhận đang {receiver_presence.status_text.lower()}, tin nhắn sẽ được lưu và thông báo"
            )
        
        # OFFLINE -> AI Fallback
        message.ai_disclaimer = self.AI_DISCLAIMER
        return RoutingResult(
            route_type=RouteType.AI_FALLBACK,
            message=message,
            receiver_presence=receiver_presence,
            reason="Người nhận đang offline, AI sẽ trả lời thay",
            ai_should_respond=True
        )
    
    # ========================================================================
    # Message Persistence
    # ========================================================================
    
    def save_message(self, message: Message) -> Dict:
        """
        Save message to Neo4j graph.
        
        Args:
            message: Message to save
            
        Returns:
            Saved message data
        """
        query = """
        MATCH (sender:User {user_id: $sender_id})
        MATCH (receiver:User {user_id: $receiver_id})
        CREATE (m:Message {
            message_id: $message_id,
            content: $content,
            message_type: $message_type,
            timestamp: datetime($timestamp),
            is_ai_response: $is_ai_response,
            ai_disclaimer: $ai_disclaimer,
            is_read: $is_read
        })
        CREATE (sender)-[:SENDS]->(m)
        CREATE (m)-[:RECEIVED_BY]->(receiver)
        RETURN m
        """
        
        result = self.client.run_query(query, {
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "message_id": message.message_id,
            "content": message.content,
            "message_type": message.message_type.value,
            "timestamp": message.timestamp.isoformat(),
            "is_ai_response": message.is_ai_response,
            "ai_disclaimer": message.ai_disclaimer,
            "is_read": message.is_read
        })
        
        return result[0] if result else None
    
    def save_ai_response(self, original_message: Message, ai_content: str) -> Message:
        """
        Save AI-generated response.
        
        Args:
            original_message: Original message that triggered AI
            ai_content: AI-generated response content
            
        Returns:
            Saved AI response message
        """
        ai_message = Message(
            message_id=str(uuid.uuid4()),
            sender_id=original_message.receiver_id,  # AI responds as receiver
            receiver_id=original_message.sender_id,
            content=ai_content,
            message_type=MessageType.TEXT,
            timestamp=datetime.now(),
            is_ai_response=True,
            ai_disclaimer=self.AI_DISCLAIMER
        )
        
        self.save_message(ai_message)
        return ai_message
    
    # ========================================================================
    # Conversation History
    # ========================================================================
    
    def get_conversation(
        self, 
        user1_id: str, 
        user2_id: str,
        limit: int = 50
    ) -> List[Message]:
        """
        Get conversation history between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            limit: Maximum messages to return
            
        Returns:
            List of messages ordered by timestamp
        """
        query = """
        MATCH (m:Message)
        WHERE (m)<-[:SENDS]-(:User {user_id: $user1_id}) AND (m)-[:RECEIVED_BY]->(:User {user_id: $user2_id})
           OR (m)<-[:SENDS]-(:User {user_id: $user2_id}) AND (m)-[:RECEIVED_BY]->(:User {user_id: $user1_id})
        WITH m
        MATCH (sender:User)-[:SENDS]->(m)-[:RECEIVED_BY]->(receiver:User)
        RETURN m.message_id as message_id,
               sender.user_id as sender_id,
               receiver.user_id as receiver_id,
               m.content as content,
               m.message_type as message_type,
               m.timestamp as timestamp,
               m.is_ai_response as is_ai_response,
               m.ai_disclaimer as ai_disclaimer,
               m.is_read as is_read
        ORDER BY m.timestamp DESC
        LIMIT $limit
        """
        
        result = self.client.run_query(query, {
            "user1_id": user1_id,
            "user2_id": user2_id,
            "limit": limit
        })
        
        messages = []
        for row in result:
            timestamp = row.get("timestamp")
            if timestamp and hasattr(timestamp, 'to_native'):
                timestamp = timestamp.to_native()
            elif isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            else:
                timestamp = datetime.now()
            
            messages.append(Message(
                message_id=row["message_id"],
                sender_id=row["sender_id"],
                receiver_id=row["receiver_id"],
                content=row["content"],
                message_type=MessageType(row.get("message_type", "text")),
                timestamp=timestamp,
                is_ai_response=row.get("is_ai_response", False),
                ai_disclaimer=row.get("ai_disclaimer"),
                is_read=row.get("is_read", False)
            ))
        
        # Return in chronological order
        return list(reversed(messages))
    
    def get_unread_count(self, user_id: str) -> int:
        """
        Get count of unread messages for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Count of unread messages
        """
        query = """
        MATCH (m:Message)-[:RECEIVED_BY]->(u:User {user_id: $user_id})
        WHERE m.is_read = false
        RETURN count(m) as unread_count
        """
        
        result = self.client.run_query(query, {"user_id": user_id})
        return result[0]["unread_count"] if result else 0
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a message as read.
        
        Args:
            message_id: Message ID
            
        Returns:
            True if successful
        """
        query = """
        MATCH (m:Message {message_id: $message_id})
        SET m.is_read = true
        RETURN m
        """
        
        result = self.client.run_query(query, {"message_id": message_id})
        return len(result) > 0
    
    def mark_conversation_as_read(self, receiver_id: str, sender_id: str) -> int:
        """
        Mark all messages in a conversation as read.
        
        Args:
            receiver_id: User receiving messages
            sender_id: User who sent messages
            
        Returns:
            Number of messages marked as read
        """
        query = """
        MATCH (sender:User {user_id: $sender_id})-[:SENDS]->(m:Message)-[:RECEIVED_BY]->(receiver:User {user_id: $receiver_id})
        WHERE m.is_read = false
        SET m.is_read = true
        RETURN count(m) as updated_count
        """
        
        result = self.client.run_query(query, {
            "receiver_id": receiver_id,
            "sender_id": sender_id
        })
        return result[0]["updated_count"] if result else 0
    
    # ========================================================================
    # Contact List
    # ========================================================================
    
    def get_recent_contacts(self, user_id: str, limit: int = 20) -> List[Dict]:
        """
        Get recent contacts for a user based on message history.
        
        Args:
            user_id: User ID
            limit: Maximum contacts to return
            
        Returns:
            List of contacts with last message info
        """
        query = """
        MATCH (u:User {user_id: $user_id})
        MATCH (u)-[:SENDS|RECEIVED_BY]-(m:Message)-[:SENDS|RECEIVED_BY]-(other:User)
        WHERE other.user_id <> $user_id
        WITH other, max(m.timestamp) as last_message_time
        RETURN other.user_id as user_id,
               other.name as name,
               other.presence_status as presence_status,
               last_message_time
        ORDER BY last_message_time DESC
        LIMIT $limit
        """
        
        result = self.client.run_query(query, {
            "user_id": user_id,
            "limit": limit
        })
        
        contacts = []
        for row in result:
            last_time = row.get("last_message_time")
            if last_time and hasattr(last_time, 'to_native'):
                last_time = last_time.to_native()
            
            contacts.append({
                "user_id": row["user_id"],
                "name": row["name"],
                "presence_status": row.get("presence_status", "offline"),
                "last_message_time": last_time
            })
        
        return contacts

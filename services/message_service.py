# services/message_service.py
"""
Message Service - Human-First message routing and AI fallback.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import logging

from core.base import BaseService
from core.exceptions import MessageRoutingError
from services.presence_service import PresenceService, PresenceStatus, PresenceInfo

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages."""
    TEXT = "text"
    SCHEDULE_REQUEST = "schedule_request"
    SCHEDULE_CONFIRM = "schedule_confirm"
    CLAIM_SHARE = "claim_share"
    SYSTEM = "system"


class RouteType(str, Enum):
    """Where to route the message."""
    HUMAN_DIRECT = "human_direct"
    HUMAN_QUEUED = "human_queued"
    AI_FALLBACK = "ai_fallback"
    ERROR = "error"


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
    
    @classmethod
    def create(
        cls,
        sender_id: str,
        receiver_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT
    ) -> 'Message':
        """Factory method to create a new message."""
        return cls(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type,
            timestamp=datetime.now()
        )


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


class MessageService(BaseService):
    """
    Service for message routing with Human-First priority.
    
    Flow:
    1. Check receiver's presence status
    2. If ONLINE/AWAY/BUSY -> Route to human (direct or queued)
    3. If OFFLINE -> AI Fallback responds
    4. Save message to database
    """
    
    AI_DISCLAIMER = (
        "🤖 Đây là phản hồi tự động từ AI khi người dùng vắng mặt. "
        "Nội dung dựa trên thông tin đã được xác thực trong hồ sơ."
    )
    
    def __init__(
        self,
        presence_service: Optional[PresenceService] = None,
        neo4j_client=None
    ):
        super().__init__("MessageService")
        self._presence_service = presence_service
        self._neo4j_client = neo4j_client
    
    def set_services(
        self,
        presence_service: Optional[PresenceService] = None,
        neo4j_client=None
    ) -> None:
        """Set dependent services."""
        if presence_service:
            self._presence_service = presence_service
        if neo4j_client:
            self._neo4j_client = neo4j_client
    
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
        message = Message.create(sender_id, receiver_id, content, message_type)
        
        # Get receiver presence
        if self._presence_service:
            receiver_presence = self._presence_service.get_user_presence(receiver_id)
        else:
            receiver_presence = None
        
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
    
    def save_message(self, message: Message) -> Optional[Dict]:
        """Save message to database."""
        if not self._neo4j_client:
            logger.warning("No Neo4j client configured, message not persisted")
            return message.to_dict()
        
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
        CREATE (sender)-[:SENT]->(m)
        CREATE (m)-[:TO]->(receiver)
        RETURN m
        """
        
        try:
            result = self._neo4j_client.run_query(query, {
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
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            raise MessageRoutingError(
                f"Failed to save message: {e}",
                sender_id=message.sender_id,
                receiver_id=message.receiver_id
            )
    
    def get_conversation(
        self,
        user1_id: str,
        user2_id: str,
        limit: int = 50
    ) -> List[Message]:
        """Get conversation between two users."""
        if not self._neo4j_client:
            return []
        
        query = """
        MATCH (sender:User)-[:SENT]->(m:Message)-[:TO]->(receiver:User)
        WHERE (sender.user_id = $user1 AND receiver.user_id = $user2)
           OR (sender.user_id = $user2 AND receiver.user_id = $user1)
        RETURN m, sender.user_id as sender_id, receiver.user_id as receiver_id
        ORDER BY m.timestamp DESC
        LIMIT $limit
        """
        
        try:
            result = self._neo4j_client.run_query(query, {
                "user1": user1_id,
                "user2": user2_id,
                "limit": limit
            })
            
            messages = []
            for row in result:
                m = row.get("m", {})
                messages.append(Message(
                    message_id=m.get("message_id"),
                    sender_id=row.get("sender_id"),
                    receiver_id=row.get("receiver_id"),
                    content=m.get("content", ""),
                    message_type=MessageType(m.get("message_type", "text")),
                    timestamp=m.get("timestamp"),
                    is_ai_response=m.get("is_ai_response", False),
                    ai_disclaimer=m.get("ai_disclaimer"),
                    is_read=m.get("is_read", False)
                ))
            
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return []
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        if not self._neo4j_client:
            return True
        
        query = """
        MATCH (m:Message {message_id: $message_id})
        SET m.is_read = true
        RETURN m
        """
        
        try:
            self._neo4j_client.run_query(query, {"message_id": message_id})
            return True
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False
    
    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread messages for a user."""
        if not self._neo4j_client:
            return 0
        
        query = """
        MATCH (m:Message)-[:TO]->(u:User {user_id: $user_id})
        WHERE m.is_read = false
        RETURN count(m) as unread_count
        """
        
        try:
            result = self._neo4j_client.run_query(query, {"user_id": user_id})
            return result[0].get("unread_count", 0) if result else 0
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0

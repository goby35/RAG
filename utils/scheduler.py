# utils/scheduler.py - Personal Scheduling Module
"""
Scheduler Module for Human-First RAG.

Manages personal scheduling, appointments, and calendar integration.
AI can propose but CANNOT confirm appointments.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

from utils.neo4j_client import Neo4jClient


class EventStatus(Enum):
    """Status of a scheduled event."""
    PROPOSED = "proposed"           # Initial proposal
    PENDING_CONFIRMATION = "pending"  # Waiting for confirmation
    CONFIRMED = "confirmed"          # Both parties confirmed
    CANCELLED = "cancelled"          # Cancelled by either party
    COMPLETED = "completed"          # Event has passed
    RESCHEDULED = "rescheduled"      # Event time changed


class EventType(Enum):
    """Types of scheduled events."""
    INTERVIEW = "interview"          # Job interview
    MEETING = "meeting"              # General meeting
    CALL = "call"                    # Phone/video call
    COFFEE_CHAT = "coffee_chat"      # Informal chat
    PRESENTATION = "presentation"    # Demo/presentation


@dataclass
class Event:
    """Represents a scheduled event."""
    event_id: str
    title: str
    description: str
    event_type: EventType
    start_time: datetime
    end_time: datetime
    status: EventStatus
    proposer_id: str
    invitee_id: str
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    is_ai_proposed: bool = False
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "status": self.status.value,
            "proposer_id": self.proposer_id,
            "invitee_id": self.invitee_id,
            "location": self.location,
            "meeting_link": self.meeting_link,
            "is_ai_proposed": self.is_ai_proposed,
            "notes": self.notes,
            "duration_minutes": self.duration_minutes,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class TimeSlot:
    """Represents an available time slot."""
    start_time: datetime
    end_time: datetime
    is_available: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "is_available": self.is_available
        }


class PersonalScheduler:
    """
    Manages personal scheduling for users.
    
    Key Principle: AI can PROPOSE but cannot CONFIRM.
    Only humans can confirm appointments.
    """
    
    # Default working hours
    WORK_START_HOUR = 9
    WORK_END_HOUR = 18
    DEFAULT_SLOT_MINUTES = 30
    
    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize PersonalScheduler.
        
        Args:
            neo4j_client: Neo4j database client
        """
        self.client = neo4j_client
    
    # ========================================================================
    # Event CRUD
    # ========================================================================
    
    def propose_event(
        self,
        proposer_id: str,
        invitee_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        event_type: EventType = EventType.MEETING,
        description: str = "",
        location: Optional[str] = None,
        meeting_link: Optional[str] = None,
        is_ai_proposed: bool = False
    ) -> Event:
        """
        Propose a new event/appointment.
        
        Args:
            proposer_id: User proposing the event
            invitee_id: User being invited
            title: Event title
            start_time: Start time
            end_time: End time
            event_type: Type of event
            description: Event description
            location: Physical location (if any)
            meeting_link: Video call link (if any)
            is_ai_proposed: Whether AI proposed this
            
        Returns:
            Created Event object
        """
        event = Event(
            event_id=str(uuid.uuid4()),
            title=title,
            description=description,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            status=EventStatus.PROPOSED,
            proposer_id=proposer_id,
            invitee_id=invitee_id,
            location=location,
            meeting_link=meeting_link,
            is_ai_proposed=is_ai_proposed
        )
        
        self._save_event_to_db(event)
        return event
    
    def confirm_event(self, event_id: str, confirmer_id: str) -> Optional[Event]:
        """
        Confirm an event. Only human can call this.
        
        Args:
            event_id: Event ID
            confirmer_id: User confirming (must be invitee)
            
        Returns:
            Updated Event or None if failed
        """
        event = self.get_event(event_id)
        if not event:
            return None
        
        # Only invitee can confirm
        if event.invitee_id != confirmer_id:
            return None
        
        # Can only confirm PROPOSED or PENDING events
        if event.status not in [EventStatus.PROPOSED, EventStatus.PENDING_CONFIRMATION]:
            return None
        
        event.status = EventStatus.CONFIRMED
        self._update_event_status(event_id, EventStatus.CONFIRMED)
        
        return event
    
    def cancel_event(self, event_id: str, canceller_id: str, reason: str = "") -> Optional[Event]:
        """
        Cancel an event.
        
        Args:
            event_id: Event ID
            canceller_id: User cancelling (must be proposer or invitee)
            reason: Reason for cancellation
            
        Returns:
            Updated Event or None if failed
        """
        event = self.get_event(event_id)
        if not event:
            return None
        
        # Either party can cancel
        if canceller_id not in [event.proposer_id, event.invitee_id]:
            return None
        
        event.status = EventStatus.CANCELLED
        event.notes = f"Cancelled by {canceller_id}: {reason}"
        self._update_event_status(event_id, EventStatus.CANCELLED)
        
        return event
    
    def reschedule_event(
        self, 
        event_id: str, 
        new_start: datetime, 
        new_end: datetime,
        rescheduler_id: str
    ) -> Optional[Event]:
        """
        Reschedule an event to a new time.
        
        Args:
            event_id: Event ID
            new_start: New start time
            new_end: New end time
            rescheduler_id: User requesting reschedule
            
        Returns:
            Updated Event or None
        """
        event = self.get_event(event_id)
        if not event:
            return None
        
        # Either party can reschedule
        if rescheduler_id not in [event.proposer_id, event.invitee_id]:
            return None
        
        query = """
        MATCH (e:Event {event_id: $event_id})
        SET e.start_time = datetime($new_start),
            e.end_time = datetime($new_end),
            e.status = 'pending',
            e.notes = $notes
        RETURN e
        """
        
        self.client.run_query(query, {
            "event_id": event_id,
            "new_start": new_start.isoformat(),
            "new_end": new_end.isoformat(),
            "notes": f"Rescheduled by {rescheduler_id}"
        })
        
        event.start_time = new_start
        event.end_time = new_end
        event.status = EventStatus.PENDING_CONFIRMATION
        
        return event
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID."""
        query = """
        MATCH (e:Event {event_id: $event_id})
        OPTIONAL MATCH (e)-[:PROPOSED_BY]->(proposer:User)
        OPTIONAL MATCH (invitee:User)-[:HAS_EVENT]->(e)
        RETURN e, proposer.user_id as proposer_id, invitee.user_id as invitee_id
        """
        
        result = self.client.run_query(query, {"event_id": event_id})
        if not result:
            return None
        
        row = result[0]
        e = row["e"]
        
        return self._parse_event(e, row.get("proposer_id"), row.get("invitee_id"))
    
    # ========================================================================
    # Calendar Queries
    # ========================================================================
    
    def get_user_events(
        self, 
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status_filter: Optional[List[EventStatus]] = None
    ) -> List[Event]:
        """
        Get all events for a user.
        
        Args:
            user_id: User ID
            start_date: Filter events after this date
            end_date: Filter events before this date
            status_filter: Filter by status
            
        Returns:
            List of events
        """
        # Build query with filters
        filters = ["(u.user_id = $user_id)"]
        params = {"user_id": user_id}
        
        if start_date:
            filters.append("e.start_time >= datetime($start_date)")
            params["start_date"] = start_date.isoformat()
        
        if end_date:
            filters.append("e.start_time <= datetime($end_date)")
            params["end_date"] = end_date.isoformat()
        
        if status_filter:
            filters.append("e.status IN $statuses")
            params["statuses"] = [s.value for s in status_filter]
        
        query = f"""
        MATCH (u:User)-[:HAS_EVENT|PROPOSED_BY]-(e:Event)
        WHERE {' AND '.join(filters)}
        OPTIONAL MATCH (e)-[:PROPOSED_BY]->(proposer:User)
        OPTIONAL MATCH (invitee:User)-[:HAS_EVENT]->(e)
        RETURN e, proposer.user_id as proposer_id, invitee.user_id as invitee_id
        ORDER BY e.start_time ASC
        """
        
        result = self.client.run_query(query, params)
        
        events = []
        for row in result:
            event = self._parse_event(row["e"], row.get("proposer_id"), row.get("invitee_id"))
            if event:
                events.append(event)
        
        return events
    
    def get_upcoming_events(self, user_id: str, days: int = 7) -> List[Event]:
        """
        Get upcoming events for next N days.
        
        Args:
            user_id: User ID
            days: Number of days to look ahead
            
        Returns:
            List of upcoming events
        """
        now = datetime.now()
        end_date = now + timedelta(days=days)
        
        return self.get_user_events(
            user_id,
            start_date=now,
            end_date=end_date,
            status_filter=[EventStatus.CONFIRMED, EventStatus.PROPOSED, EventStatus.PENDING_CONFIRMATION]
        )
    
    def get_pending_confirmations(self, user_id: str) -> List[Event]:
        """
        Get events pending user's confirmation.
        
        Args:
            user_id: User ID (as invitee)
            
        Returns:
            List of events awaiting confirmation
        """
        query = """
        MATCH (u:User {user_id: $user_id})-[:HAS_EVENT]->(e:Event)
        WHERE e.status IN ['proposed', 'pending']
        OPTIONAL MATCH (e)-[:PROPOSED_BY]->(proposer:User)
        RETURN e, proposer.user_id as proposer_id, $user_id as invitee_id
        ORDER BY e.start_time ASC
        """
        
        result = self.client.run_query(query, {"user_id": user_id})
        
        events = []
        for row in result:
            event = self._parse_event(row["e"], row.get("proposer_id"), row.get("invitee_id"))
            if event:
                events.append(event)
        
        return events
    
    # ========================================================================
    # Availability
    # ========================================================================
    
    def get_available_slots(
        self, 
        user_id: str, 
        date: datetime,
        slot_duration_minutes: int = 30
    ) -> List[TimeSlot]:
        """
        Get available time slots for a user on a given date.
        
        Args:
            user_id: User ID
            date: Date to check
            slot_duration_minutes: Duration of each slot
            
        Returns:
            List of available TimeSlots
        """
        # Get existing events for the date
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        existing_events = self.get_user_events(
            user_id,
            start_date=start_of_day,
            end_date=end_of_day,
            status_filter=[EventStatus.CONFIRMED, EventStatus.PROPOSED]
        )
        
        # Generate all possible slots during work hours
        slots = []
        current_time = start_of_day.replace(hour=self.WORK_START_HOUR)
        work_end = start_of_day.replace(hour=self.WORK_END_HOUR)
        
        while current_time < work_end:
            slot_end = current_time + timedelta(minutes=slot_duration_minutes)
            
            # Check if slot conflicts with existing events
            is_available = True
            for event in existing_events:
                if self._times_overlap(current_time, slot_end, event.start_time, event.end_time):
                    is_available = False
                    break
            
            slots.append(TimeSlot(
                start_time=current_time,
                end_time=slot_end,
                is_available=is_available
            ))
            
            current_time = slot_end
        
        return slots
    
    def suggest_meeting_times(
        self,
        user1_id: str,
        user2_id: str,
        date: datetime,
        duration_minutes: int = 30,
        max_suggestions: int = 3
    ) -> List[TimeSlot]:
        """
        Suggest meeting times that work for both users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            date: Date to check
            duration_minutes: Meeting duration
            max_suggestions: Maximum slots to suggest
            
        Returns:
            List of mutually available TimeSlots
        """
        slots1 = self.get_available_slots(user1_id, date, duration_minutes)
        slots2 = self.get_available_slots(user2_id, date, duration_minutes)
        
        # Find overlapping available slots
        mutual_slots = []
        for s1 in slots1:
            if not s1.is_available:
                continue
            for s2 in slots2:
                if not s2.is_available:
                    continue
                if s1.start_time == s2.start_time and s1.end_time == s2.end_time:
                    mutual_slots.append(s1)
                    break
        
        return mutual_slots[:max_suggestions]
    
    # ========================================================================
    # AI Proposals (with restrictions)
    # ========================================================================
    
    def ai_propose_meeting(
        self,
        on_behalf_of_id: str,
        with_user_id: str,
        suggested_slots: List[TimeSlot],
        event_type: EventType = EventType.MEETING,
        title: str = "Meeting Request"
    ) -> Dict[str, Any]:
        """
        AI proposes a meeting on behalf of offline user.
        
        IMPORTANT: AI cannot confirm, only propose.
        
        Args:
            on_behalf_of_id: User AI is representing
            with_user_id: User requesting the meeting
            suggested_slots: Available slots to propose
            event_type: Type of meeting
            title: Meeting title
            
        Returns:
            Proposal details (not confirmed event)
        """
        if not suggested_slots:
            return {
                "success": False,
                "message": "Không có slot trống để đề xuất",
                "requires_human_confirmation": True
            }
        
        # Create proposed event (not confirmed)
        slot = suggested_slots[0]
        event = self.propose_event(
            proposer_id=with_user_id,  # Requester proposes
            invitee_id=on_behalf_of_id,  # Offline user is invitee
            title=title,
            start_time=slot.start_time,
            end_time=slot.end_time,
            event_type=event_type,
            description="Đề xuất bởi AI khi người dùng vắng mặt",
            is_ai_proposed=True
        )
        
        return {
            "success": True,
            "event": event.to_dict(),
            "message": f"📅 AI đã ghi nhận yêu cầu hẹn lịch. Đề xuất: {slot.start_time.strftime('%H:%M %d/%m/%Y')}",
            "requires_human_confirmation": True,
            "ai_disclaimer": "⚠️ Lịch hẹn này CẦN được xác nhận bởi người dùng. AI không có quyền xác nhận."
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _save_event_to_db(self, event: Event):
        """Save event to Neo4j."""
        query = """
        CREATE (e:Event {
            event_id: $event_id,
            title: $title,
            description: $description,
            event_type: $event_type,
            start_time: datetime($start_time),
            end_time: datetime($end_time),
            status: $status,
            location: $location,
            meeting_link: $meeting_link,
            is_ai_proposed: $is_ai_proposed,
            notes: $notes,
            created_at: datetime()
        })
        WITH e
        MATCH (proposer:User {user_id: $proposer_id})
        MATCH (invitee:User {user_id: $invitee_id})
        CREATE (e)-[:PROPOSED_BY]->(proposer)
        CREATE (invitee)-[:HAS_EVENT]->(e)
        RETURN e
        """
        
        self.client.run_query(query, {
            "event_id": event.event_id,
            "title": event.title,
            "description": event.description,
            "event_type": event.event_type.value,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "status": event.status.value,
            "location": event.location,
            "meeting_link": event.meeting_link,
            "is_ai_proposed": event.is_ai_proposed,
            "notes": event.notes,
            "proposer_id": event.proposer_id,
            "invitee_id": event.invitee_id
        })
    
    def _update_event_status(self, event_id: str, status: EventStatus):
        """Update event status in database."""
        query = """
        MATCH (e:Event {event_id: $event_id})
        SET e.status = $status, e.updated_at = datetime()
        RETURN e
        """
        self.client.run_query(query, {
            "event_id": event_id,
            "status": status.value
        })
    
    def _parse_event(self, e: Dict, proposer_id: str, invitee_id: str) -> Optional[Event]:
        """Parse event from database result."""
        if not e:
            return None
        
        start_time = e.get("start_time")
        end_time = e.get("end_time")
        created_at = e.get("created_at")
        
        # Convert Neo4j DateTime
        if start_time and hasattr(start_time, 'to_native'):
            start_time = start_time.to_native()
        if end_time and hasattr(end_time, 'to_native'):
            end_time = end_time.to_native()
        if created_at and hasattr(created_at, 'to_native'):
            created_at = created_at.to_native()
        
        try:
            return Event(
                event_id=e.get("event_id"),
                title=e.get("title", ""),
                description=e.get("description", ""),
                event_type=EventType(e.get("event_type", "meeting")),
                start_time=start_time,
                end_time=end_time,
                status=EventStatus(e.get("status", "proposed")),
                proposer_id=proposer_id or "",
                invitee_id=invitee_id or "",
                location=e.get("location"),
                meeting_link=e.get("meeting_link"),
                is_ai_proposed=e.get("is_ai_proposed", False),
                notes=e.get("notes", ""),
                created_at=created_at or datetime.now()
            )
        except Exception:
            return None
    
    def _times_overlap(self, start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1

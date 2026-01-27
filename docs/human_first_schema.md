# Human-First RAG - Graph Schema Design

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Human-First RAG Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │  Identity & Access   │  │   Communication      │  │  RAG & Knowledge │  │
│  │       Layer          │  │       Layer          │  │      Layer       │  │
│  ├──────────────────────┤  ├──────────────────────┤  ├──────────────────┤  │
│  │ • Authentication     │  │ • Human-Human Chat   │  │ • Neo4j Graph    │  │
│  │ • Session Management │  │ • AI Fallback        │  │ • Retrieval      │  │
│  │ • Presence Status    │  │ • Message Routing    │  │ • Temporal Rank  │  │
│  │ • Role Inference     │  │ • Scheduling         │  │ • ReBAC Filter   │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Graph Schema - Nodes

### 2.1 Core Nodes (Existing)

| Node | Properties | Description |
|------|------------|-------------|
| **User** | user_id, name, wallet_address, did, roles, reputation_score, bio, **presence_status**, **last_seen** | Người dùng với trạng thái online |
| **Claim** | claim_id, topic, content_summary, access_level, status, confidence_score... | Khẳng định của user |
| **Entity** | entity_id, name, canonical_id, entity_type | Skills, Organizations... |
| **Evidence** | evidence_id, url, evidence_type | Bằng chứng |

### 2.2 New Nodes (Human-First)

| Node | Properties | Description |
|------|------------|-------------|
| **Message** | message_id, content, sender_id, receiver_id, timestamp, is_ai_response, ai_disclaimer | Tin nhắn chat |
| **Conversation** | conversation_id, participants[], created_at, updated_at | Cuộc hội thoại |
| **Event** | event_id, title, description, start_time, end_time, status, location | Lịch hẹn |
| **Session** | session_id, user_id, login_at, logout_at, is_active | Phiên đăng nhập |

## 3. Graph Schema - Relationships

### 3.1 Existing Relationships

```cypher
(User)-[:MAKES_CLAIM]->(Claim)
(Claim)-[:ABOUT]->(Entity)
(Claim)-[:SUPPORTED_BY]->(Evidence)
(User)-[:VERIFIES]->(Claim)

// Social Graph
(User)-[:FRIEND]->(User)
(User)-[:COLLEAGUE]->(User)
(User)-[:RECRUITING]->(User)
```

### 3.2 New Relationships (Human-First)

```cypher
// Messaging
(User)-[:SENDS]->(Message)
(Message)-[:RECEIVED_BY]->(User)
(Message)-[:PART_OF]->(Conversation)
(Conversation)-[:BETWEEN]->(User)

// Scheduling
(User)-[:HAS_EVENT]->(Event)
(Event)-[:PROPOSED_BY]->(User)
(Event)-[:ACCEPTED_BY]->(User)
(Event)-[:RELATED_TO]->(Conversation)

// Session
(User)-[:HAS_SESSION]->(Session)

// Message -> Claim conversion
(Message)-[:CONVERTED_TO]->(Claim)
```

## 4. Presence Status

```
┌─────────────────────────────────────────────────────────────┐
│                    Presence Status                           │
├─────────────────────────────────────────────────────────────┤
│  ONLINE   → User đang hoạt động, chat trực tiếp            │
│  AWAY     → User đã không hoạt động > 5 phút               │
│  BUSY     → User đang bận, chỉ nhận tin nhắn quan trọng    │
│  OFFLINE  → User đã đăng xuất, AI có thể đại diện          │
└─────────────────────────────────────────────────────────────┘
```

## 5. Message Routing Logic

```
┌─────────────────────────────────────────────────────────────┐
│                 Message Routing Decision Tree                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Sender gửi tin nhắn tới Receiver                           │
│                    │                                         │
│                    ▼                                         │
│  ┌─────────────────────────────────┐                        │
│  │  Receiver.presence_status = ?   │                        │
│  └─────────────────────────────────┘                        │
│           │              │              │                    │
│         ONLINE         AWAY          OFFLINE                │
│           │              │              │                    │
│           ▼              ▼              ▼                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Direct Chat │ │ Notify +    │ │ AI Agent    │           │
│  │ Human-Human │ │ Queue Msg   │ │ Fallback    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│           │              │              │                    │
│           └──────────────┴──────────────┘                   │
│                          │                                   │
│                          ▼                                   │
│               Save Message to Graph                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 6. AI Agent Constraints

AI Agent khi đại diện User phải tuân theo các ràng buộc:

| Constraint | Description |
|------------|-------------|
| **NO_COMMIT** | Không được cam kết, hứa hẹn |
| **NO_NEGOTIATE** | Không được đàm phán lương, điều khoản |
| **NO_SENSITIVE** | Không tiết lộ thông tin nhạy cảm (owner, private) |
| **RAG_ONLY** | Chỉ trả lời dựa trên thông tin đã có trong RAG |
| **DISCLAIMER** | Luôn gắn nhãn "AI đại diện trả lời" |

## 7. Event/Scheduling Status

```
┌─────────────────────────────────────────────────────────────┐
│                    Event Status Flow                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PROPOSED → PENDING_CONFIRMATION → CONFIRMED → COMPLETED    │
│      │              │                   │          │        │
│      └──────────────┴───────────────────┴──────────┘        │
│                          │                                   │
│                     CANCELLED                                │
│                                                              │
│  Note: AI có thể PROPOSE nhưng KHÔNG được CONFIRM            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 8. Personal RAG Components

Mỗi User sở hữu 1 Personal RAG gồm:

```
┌─────────────────────────────────────────────────────────────┐
│                    Personal RAG                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Knowledge  │  │ Interaction │  │  Temporal   │          │
│  │   Context   │  │   Context   │  │   Context   │          │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤          │
│  │ • Claims    │  │ • Messages  │  │ • Verified  │          │
│  │ • Evidence  │  │ • Chat Hist │  │ • Freshness │          │
│  │ • Entities  │  │ • Contacts  │  │ • Expiry    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │   Social    │  │ Operational │                           │
│  │   Context   │  │   Context   │                           │
│  ├─────────────┤  ├─────────────┤                           │
│  │ • Friends   │  │ • Presence  │                           │
│  │ • Colleagues│  │ • Schedule  │                           │
│  │ • Access    │  │ • Avail.    │                           │
│  └─────────────┘  └─────────────┘                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 9. Cypher Examples

### 9.1 Get User with Presence

```cypher
MATCH (u:User {user_id: $user_id})
OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session {is_active: true})
RETURN u, s, 
       CASE WHEN s IS NOT NULL THEN 'ONLINE' ELSE u.presence_status END as status
```

### 9.2 Send Message (Human-to-Human)

```cypher
// Create message
CREATE (m:Message {
    message_id: $message_id,
    content: $content,
    timestamp: datetime(),
    is_ai_response: false
})
WITH m
MATCH (sender:User {user_id: $sender_id})
MATCH (receiver:User {user_id: $receiver_id})
CREATE (sender)-[:SENDS]->(m)
CREATE (m)-[:RECEIVED_BY]->(receiver)
RETURN m
```

### 9.3 Get Conversation History

```cypher
MATCH (u1:User {user_id: $user1})-[:SENDS|RECEIVED_BY]-(m:Message)-[:SENDS|RECEIVED_BY]-(u2:User {user_id: $user2})
RETURN m
ORDER BY m.timestamp ASC
```

### 9.4 Propose Event

```cypher
CREATE (e:Event {
    event_id: $event_id,
    title: $title,
    start_time: datetime($start_time),
    end_time: datetime($end_time),
    status: 'PROPOSED'
})
WITH e
MATCH (proposer:User {user_id: $proposer_id})
MATCH (invitee:User {user_id: $invitee_id})
CREATE (e)-[:PROPOSED_BY]->(proposer)
CREATE (invitee)-[:HAS_EVENT]->(e)
RETURN e
```

### 9.5 AI Fallback Query

```cypher
// Get claims for AI to answer (respecting ReBAC)
MATCH (target:User {user_id: $target_id})-[:MAKES_CLAIM]->(c:Claim)
WHERE c.access_level IN $allowed_tags
AND c.status IN ['verified', 'attested']  // Only verified for AI
RETURN c
ORDER BY c.confidence_score DESC
```

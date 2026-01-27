# Human-First RAG Application with Personal Knowledge Graph

Ứng dụng RAG (Retrieval-Augmented Generation) với Personal Knowledge Graph, hỗ trợ **Human-First Communication**, EAS (Ethereum Attestation Service) integration và Confidence Scoring.

## 🎯 Tính năng chính

### 👤 Human-First Core
- **Human-Human Chat First**: Chat người-người là mặc định, AI chỉ đại diện khi vắng mặt
- **Presence Status**: Trạng thái Online/Away/Busy/Offline
- **Personal Scheduling**: Lịch hẹn cá nhân với AI proposal (không tự confirm)
- **Role Inference**: Vai trò tự động suy ra từ Graph, không chọn thủ công
- **Living Profile**: Hồ sơ sống tích hợp Chat + Calendar + Claims

### Core Features
- **Multi-user Access Control**: Phân quyền Owner/Recruiter/Public
- **Graph-based Knowledge**: Nodes (User, Claim, Entity, Evidence, Message, Event) + Edges
- **Neo4j Graph Database**: Lưu trữ và truy vấn Knowledge Graph
- **Social Graph**: Quan hệ FRIEND, COLLEAGUE, RECRUITING giữa users

### 🆕 Advanced Features
- **🔍 Discovery Agent**: Tìm kiếm người dùng toàn cục theo skills/entities
- **💬 Personal RAG Chat**: Chatbot hỏi đáp với RAG cá nhân của từng user
- **🔐 ReBAC (Relationship-based Access Control)**: Phân quyền dựa trên mối quan hệ
- **⏰ Temporal Ranking**: Xếp hạng claims theo thời gian với time decay
- **📊 Combined Scoring**: Điểm tổng hợp = Semantic (40%) + Confidence (40%) + Freshness (20%)
- **🤖 AI Fallback Agent**: AI trả lời thay khi user offline (với ràng buộc)

### Integration Ready
- **Confidence Scoring**: Đánh giá độ tin cậy của thông tin
- **EAS Ready**: Chuẩn bị cho blockchain attestation integration
- **AI-powered Extraction**: Tự động extract claims từ text tự nhiên

---

## 📁 Cấu trúc dự án (Clean Architecture)

```
RAG/
├── app.py                      # Entry point chính (backward compatible)
├── app_refactored.py           # Entry point với clean architecture
├── app_neo4j.py                # Ứng dụng với Neo4j backend + RAG Chat
├── app_human_first.py          # Human-First RAG (RECOMMENDED)
├── config.py                   # Backward compatibility config exports
│
├── config/                     # 🆕 Configuration module (refactored)
│   ├── __init__.py             # Re-exports tất cả configs
│   ├── settings.py             # Application settings (API keys, weights)
│   ├── models.py               # LLM/Embedding model configs
│   ├── access.py               # Access control & ReBAC configs
│   ├── paths.py                # File path configs
│   └── entities.py             # Entity types, claim topics
│
├── core/                       # 🆕 Core infrastructure
│   ├── __init__.py
│   ├── exceptions.py           # Custom exceptions hierarchy
│   ├── interfaces.py           # Abstract interfaces (IEmbedder, IRepository...)
│   ├── base.py                 # Base classes (Singleton, BaseService...)
│   └── container.py            # Dependency Injection container
│
├── models/                     # Data Models
│   ├── __init__.py
│   └── schema.py               # Dataclasses: User, Claim, Entity, Evidence
│
├── repositories/               # 🆕 Data Access Layer
│   ├── __init__.py
│   ├── json_repository.py      # Generic thread-safe JSON storage
│   ├── user_repository.py      # User data access
│   ├── claim_repository.py     # Claim data access
│   └── entity_repository.py    # Entity data access
│
├── services/                   # 🆕 Business Logic Layer
│   ├── __init__.py
│   ├── embedding_service.py    # Text embedding với SentenceTransformer
│   ├── llm_service.py          # LLM interactions với OpenAI
│   ├── rag_service.py          # RAG pipeline với confidence scoring
│   ├── access_control_service.py  # ReBAC access control
│   ├── presence_service.py     # User presence management
│   ├── message_service.py      # Human-First message routing
│   └── claim_service.py        # Claim CRUD & confidence calculation
│
├── utils/                      # Utility modules (legacy, backward compatible)
│   ├── __init__.py
│   ├── neo4j_client.py         # Neo4j database client
│   ├── auth.py                 # Authentication & Session management
│   ├── presence.py             # Online/Offline status tracking
│   ├── chat_router.py          # Human-First message routing
│   ├── scheduler.py            # Personal scheduling & calendar
│   ├── ai_agent.py             # AI Fallback Agent (with constraints)
│   ├── discovery_agent.py      # Global user search by skills
│   ├── rebac.py                # Relationship-based Access Control
│   ├── temporal_ranking.py     # Time decay & combined scoring
│   ├── data_loader.py          # Load/save JSON & CSV data
│   ├── document_processor.py   # Tạo summary với OpenAI
│   ├── embeddings.py           # SentenceTransformer & FAISS index
│   ├── entity_linker.py        # Entity Linking
│   ├── gatekeeper.py           # Access control + Confidence Filter
│   ├── rag_engine.py           # RAG pipeline với Confidence
│   └── triple_extractor.py     # AI extract Claims từ text
│
├── ui/                         # UI components
│   ├── __init__.py
│   ├── sidebar.py              # Form nhập liệu thân thiện
│   └── main_content.py         # Query interface
│
├── data/                       # JSON Data Storage
│   ├── users.json              # User nodes
│   ├── claims.json             # Claim nodes (trung tâm logic)
│   ├── entities.json           # Entity nodes (skills, orgs...)
│   └── evidence.json           # Evidence nodes (links, files)
│
├── docs/                       # Documentation
│   └── human_first_schema.md   # Graph schema cho Human-First
│
├── docker-compose.yml          # Neo4j container setup
├── seed_data.py                # Script khởi tạo dữ liệu Neo4j
├── requirements.txt            # Dependencies
└── data_mock.csv               # Legacy data (backward compatible)
```

---

## 🏗️ Architecture

### Design Patterns

| Pattern | Location | Mô tả |
|---------|----------|-------|
| **Dependency Injection** | `core/container.py` | Quản lý dependencies, dễ test/mock |
| **Repository Pattern** | `repositories/` | Abstract data access layer |
| **Service Layer** | `services/` | Encapsulate business logic |
| **Interface Segregation** | `core/interfaces.py` | Define contracts |
| **Singleton** | `core/base.py` | Single instance cho services |

### Key Principles

- **SOLID Principles**: Mỗi module có single responsibility
- **Separation of Concerns**: Clear layers (data → business → presentation)
- **Backward Compatibility**: Legacy `utils/` và `config.py` vẫn hoạt động
- **Clean Architecture**: Dependencies hướng vào trong (UI → Services → Repositories → Core)

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│              (app.py, ui/sidebar.py, ui/main_content.py)    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  (RAGService, EmbeddingService, AccessControlService...)    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Repository Layer                           │
│   (UserRepository, ClaimRepository, EntityRepository)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Core Layer                               │
│       (Interfaces, Exceptions, Base Classes, Container)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Cách khởi tạo dự án

### 1. Clone/Tải dự án

```bash
cd D:\Study\uni\25_26\HKII\RAG
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
pip install streamlit tf-keras
```

### 3. Cấu hình API Key

**Option 1**: Tạo file `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-your-openai-api-key-here"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jpassword"
```

**Option 2**: Environment variables:

```bash
set OPENAI_API_KEY=sk-your-openai-api-key-here
set NEO4J_URI=bolt://localhost:7687
```

### 4. Khởi động Neo4j với Docker

```bash
# Khởi động Neo4j container
docker-compose up -d

# Kiểm tra container đang chạy
docker-compose ps

# Xem logs
docker-compose logs neo4j
```

Neo4j Browser: http://localhost:7474
- Username: `neo4j`
- Password: `neo4jpassword`

### 5. Seed dữ liệu mẫu

```bash
python seed_data.py --clear
```

### 6. Chạy ứng dụng

```bash
# Ứng dụng gốc (backward compatible)
streamlit run app.py

# Ứng dụng với clean architecture
streamlit run app_refactored.py

# Neo4j backend với Discovery Agent
streamlit run app_neo4j.py --server.port 8502

# Human-First RAG (RECOMMENDED)
streamlit run app_human_first.py --server.port 8503
```

---

## 💻 Usage Examples

### Sử dụng Services (Clean Architecture)

```python
from core.container import configure_container
from services import RAGService, EmbeddingService

# Configure DI container
container = configure_container()

# Get services
rag_service = container.resolve(RAGService)
embedding_service = container.resolve(EmbeddingService)

# Initialize và query
embedding_service.initialize()
result = rag_service.query(
    query="What skills does user have?",
    documents=documents,
    metadata=metadata,
    target_user_id="user_123",
    viewer_id="viewer_456"
)

print(result.answer)
print(f"Confidence: {result.confidence_avg:.0%}")
```

### Sử dụng Repositories

```python
from repositories import ClaimRepository, UserRepository

claim_repo = ClaimRepository()
user_repo = UserRepository()

# Query data
user = user_repo.get_by_id("user_123")
claims = claim_repo.get_by_user("user_123")
verified_claims = claim_repo.get_verified_claims("user_123")

# Get documents for RAG
documents, metadata = claim_repo.get_documents_and_metadata()
```

### Legacy Usage (Backward Compatible)

```python
# Vẫn hoạt động như trước
from config import EMBEDDING_MODEL, init_api_keys
from utils import load_data, simple_rag

init_api_keys()
data = load_data()
answer = simple_rag(query, docs, meta, target_id, viewer_id)
```

---

## 👤 Human-First Architecture

### Nguyên tắc cốt lõi

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Human-First RAG Principles                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. 👥 HUMAN-FIRST: Chat người-người là mặc định                            │
│  2. 🤖 AI FALLBACK: AI chỉ trả lời khi người dùng OFFLINE                   │
│  3. 📅 NO AUTO-CONFIRM: AI đề xuất lịch nhưng KHÔNG tự xác nhận             │
│  4. 🔐 GRAPH ROLES: Vai trò suy từ quan hệ, không chọn thủ công             │
│  5. 📋 LIVING PROFILE: Hồ sơ = Claims + Messages + Events                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Presence Status

| Status | Emoji | Mô tả | Routing |
|--------|-------|-------|---------|
| **ONLINE** | 🟢 | Đang hoạt động | → Chat trực tiếp |
| **AWAY** | 🟡 | Vắng > 5 phút | → Queue + Notify |
| **BUSY** | 🔴 | Đang bận | → Queue + Notify |
| **OFFLINE** | ⚫ | Đã logout | → AI Fallback |

### Message Routing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Message Routing                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  HR gửi tin nhắn cho Goby                                                   │
│            │                                                                 │
│            ▼                                                                 │
│  ┌─────────────────────────┐                                                │
│  │  Goby.presence = ?      │                                                │
│  └─────────────────────────┘                                                │
│       │         │         │                                                  │
│    ONLINE     AWAY     OFFLINE                                              │
│       │         │         │                                                  │
│       ▼         ▼         ▼                                                  │
│  ┌─────────┐ ┌─────────┐ ┌──────────────────┐                              │
│  │ Direct  │ │ Queue + │ │ AI Agent trả lời │                              │
│  │ to Goby │ │ Notify  │ │ (có disclaimer)  │                              │
│  └─────────┘ └─────────┘ └──────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### AI Agent Constraints

| Constraint | Mô tả |
|------------|-------|
| **NO_COMMIT** | Không thể cam kết, hứa hẹn thay người dùng |
| **NO_NEGOTIATE** | Không đàm phán lương, điều khoản |
| **NO_SENSITIVE** | Không tiết lộ thông tin private/owner |
| **RAG_ONLY** | Chỉ trả lời dựa trên claims đã xác thực |
| **DISCLAIMER** | Luôn gắn nhãn "AI đại diện trả lời" |

---

## 📊 Graph Schema

### Nodes

| Node Type | Mô tả | Key Properties |
|-----------|-------|----------------|
| **User** | Freelancer, Recruiter, Organization | `user_id`, `wallet_address`, `did`, `roles` |
| **Claim** | Khẳng định của user (TRUNG TÂM) | `content_summary`, `access_level`, `confidence_score`, `eas_uid` |
| **Entity** | Skill, Organization, Project... | `name`, `canonical_id`, `entity_type` |
| **Evidence** | Bằng chứng (GitHub, PDF...) | `url`, `evidence_type`, `file_hash` |

### Edges (Relationships)

```
User --[MAKES_CLAIM]--> Claim
Claim --[ABOUT]--> Entity
Claim --[SUPPORTED_BY]--> Evidence
User --[VERIFIES]--> Claim (EAS Attestation)

# Social Graph
User --[FRIEND]--> User
User --[COLLEAGUE]--> User
User --[RECRUITING]--> User
```

### Cypher Query Examples

```cypher
-- Xem tất cả users và claims
MATCH (u:User)-[:MAKES_CLAIM]->(c:Claim)
RETURN u.name, c.topic, c.status

-- Tìm bạn bè của một user
MATCH (u:User {user_id: 'goby'})-[:FRIEND]-(friend:User)
RETURN friend.name

-- Xem claims về một skill
MATCH (c:Claim)-[:ABOUT]->(e:Entity {name: 'Python'})
MATCH (u:User)-[:MAKES_CLAIM]->(c)
RETURN u.name, c.content_summary, c.status
```

---

## 🔐 Access Control

### Confidence Score Logic

| Trạng thái | Score | Mô tả |
|------------|-------|-------|
| Self-declared | 0.3 | Tự khai báo, chưa có bằng chứng |
| + Evidence | 0.5 | Có link GitHub/Portfolio |
| + EAS Attestation | 0.9 | Đã được xác thực trên blockchain |
| + Trusted Org | 1.0 | Xác thực từ tổ chức uy tín |

### ReBAC Access Levels

| Relationship | Access Tags | Mô tả |
|--------------|-------------|-------|
| **SELF** | `owner`, `connections_only`, `public` | Xem tất cả |
| **FRIEND** | `connections_only`, `public` | Xem claims bạn bè |
| **COLLEAGUE** | `connections_only`, `public` | Xem claims đồng nghiệp |
| **RECRUITING** | `connections_only`, `public` | Recruiter xem ứng viên |
| **STRANGER** | `public` | Chỉ xem public |

### Gatekeeper Logic

```
┌─────────────────────────────────────────────────────────────┐
│                    Gatekeeper Logic v2                       │
├─────────────────────────────────────────────────────────────┤
│ Bước 1 (Scope): Lọc Claims theo Target User ID              │
│ Bước 2 (Access Control):                                     │
│   - Owner (Viewer == Target): Xem TẤT CẢ                    │
│   - Recruiter: Xem public + verified (connections_only)     │
│   - Public/Anonymous: Chỉ xem public                        │
│ Bước 3 (Confidence Filter): Lọc theo minimum confidence     │
└─────────────────────────────────────────────────────────────┘
```

---

## ⏰ Temporal Ranking

### Time Decay Formula

```
Freshness Score = 1.0                           (if age ≤ 180 days)
                = 1 / (1 + log(1 + days/365))   (if age > 180 days)
                = MIN_SCORE (0.1)               (if expired)
```

### Combined Scoring

```python
final_score = (0.40 × semantic_score)    # Độ liên quan với query
            + (0.40 × confidence_score)  # Độ tin cậy của claim
            + (0.20 × freshness_score)   # Độ mới của thông tin
```

---

## 🧪 Testing

```python
from core.container import get_container, Container

# Clear container for testing
Container.clear_instance(Container)

# Configure with mocks
container = get_container()
container.register(EmbeddingService, instance=mock_embedding_service)

# Run tests...
```

---

## 🔄 Migration Guide

### From Legacy to Clean Architecture

```python
# ❌ Old way
from config import EMBEDDING_MODEL, init_api_keys
from utils import load_data, simple_rag

# ✅ New way
from config.models import ModelConfig
from config.settings import get_settings
from repositories import ClaimRepository
from services import RAGService
```

### Gradual Migration

Cả hai styles hoạt động đồng thời. Migrate module by module:

1. Sử dụng services mới cho features mới
2. Giữ legacy imports cho code cũ
3. Dần dần refactor từng module

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | Streamlit |
| **Graph Database** | Neo4j 5.x (Docker) |
| **Embedding** | SentenceTransformers (`paraphrase-mpnet-base-v2`) |
| **Vector Search** | FAISS |
| **LLM** | OpenAI GPT-4o-mini |
| **Data Storage** | Neo4j (primary), JSON (backup) |
| **Containerization** | Docker Compose |
| **Future** | EAS (Ethereum Attestation Service) |

## 📦 Dependencies

```txt
streamlit
openai
sentence-transformers
faiss-cpu
pandas
numpy
tf-keras
neo4j>=5.0.0
```

---

## 🚀 Quick Start Commands

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Start Neo4j
docker-compose up -d

# 3. Seed data
python seed_data.py --clear

# 4. Run app (choose one)
streamlit run app.py                    # JSON backend
streamlit run app_refactored.py         # Clean architecture
streamlit run app_neo4j.py              # Neo4j + Discovery
streamlit run app_human_first.py        # Human-First (RECOMMENDED)
```

---

## 📝 License

MIT License - Free to use for educational purposes.

## Author

Tran Thi Hong Ngoc - B2207546

# Multi-user Interactive RAG Application with Graph Schema

Ứng dụng RAG (Retrieval-Augmented Generation) với Knowledge Graph Schema, hỗ trợ EAS (Ethereum Attestation Service) integration và Confidence Scoring.

## 🎯 Tính năng chính

- **Multi-user Access Control**: Phân quyền Owner/Recruiter/Public
- **Graph-based Knowledge**: Nodes (User, Claim, Entity, Evidence) + Edges
- **Confidence Scoring**: Đánh giá độ tin cậy của thông tin
- **EAS Ready**: Chuẩn bị cho blockchain attestation integration
- **AI-powered Extraction**: Tự động extract claims từ text tự nhiên

## 📁 Cấu trúc dự án

```
RAG/
├── app.py                      # Entry point - khởi động ứng dụng
├── config.py                   # Configuration & constants
├── requirements.txt            # Dependencies
├── README.md                   # Documentation
│
├── .streamlit/
│   └── secrets.toml            # API keys (OpenAI) - KHÔNG COMMIT
│
├── models/                     # Data Models (NEW)
│   ├── __init__.py
│   └── schema.py               # User, Claim, Entity, Evidence classes
│
├── data/                       # JSON Data Storage (NEW)
│   ├── users.json              # User nodes
│   ├── claims.json             # Claim nodes (trung tâm logic)
│   ├── entities.json           # Entity nodes (skills, orgs...)
│   └── evidence.json           # Evidence nodes (links, files)
│
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── data_loader.py          # Load/save JSON & CSV data
│   ├── document_processor.py   # Tạo summary với OpenAI
│   ├── embeddings.py           # SentenceTransformer & FAISS index
│   ├── entity_linker.py        # Entity Linking (NEW)
│   ├── gatekeeper.py           # Access control + Confidence Filter
│   ├── rag_engine.py           # RAG pipeline với Confidence
│   └── triple_extractor.py     # AI extract Claims từ text
│
├── ui/                         # UI components
│   ├── __init__.py
│   ├── sidebar.py              # Form nhập liệu thân thiện
│   └── main_content.py         # Query interface
│
└── data_mock.csv               # Legacy data (backward compatible)
```

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

Tạo file `.streamlit/secrets.toml` với nội dung:

```toml
OPENAI_API_KEY = "sk-your-openai-api-key-here"
```

> **Lưu ý**: Thay `sk-your-openai-api-key-here` bằng API key thật từ [OpenAI Platform](https://platform.openai.com/api-keys)

### 4. Chạy ứng dụng

```bash
streamlit run app.py
```

Ứng dụng sẽ mở tại: http://localhost:8501

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
```

### Confidence Score Logic

| Trạng thái | Score | Mô tả |
|------------|-------|-------|
| Self-declared | 0.3 | Tự khai báo, chưa có bằng chứng |
| + Evidence | 0.5 | Có link GitHub/Portfolio |
| + EAS Attestation | 0.9 | Đã được xác thực trên blockchain |
| + Trusted Org | 1.0 | Xác thực từ tổ chức uy tín |

## 🔐 Gatekeeper Logic

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

## 🧠 RAG với Confidence

RAG Engine tích hợp Confidence Score vào prompt:

```
✅ [VERIFIED - EAS Attested] (Confidence: 90%)
  User goby có 5 năm kinh nghiệm Python...

📎 [Has Evidence] (Confidence: 50%)
  User goby xây dựng hệ thống RAG chatbot...

📝 [Self-Declared] (Confidence: 30%)
  User goby tốt nghiệp ĐH Bách Khoa...
```

AI sẽ trả lời với caveat phù hợp:
- "Đã được xác thực rằng..." cho verified claims
- "Theo khai báo của người dùng..." cho self-declared

## 📝 Core Modules

| Module | Chức năng |
|--------|-----------|
| `models/schema.py` | Data classes: User, Claim, Entity, Evidence |
| `config.py` | API keys, constants, confidence thresholds |
| `utils/data_loader.py` | Load/save JSON & CSV data |
| `utils/entity_linker.py` | Map entities về canonical_id |
| `utils/gatekeeper.py` | Access control + Confidence Filter |
| `utils/rag_engine.py` | RAG với Confidence-aware prompts |
| `utils/triple_extractor.py` | AI extract Claims từ text |

## 🔄 Entity Linking

Tránh Graph bị phân mảnh (fragmented):

```
Input: "Py", "Python 3", "Snake Lang"
       ↓ Entity Linker
Output: canonical_id = "tech_python"
```

## 🌐 EAS Integration (Future)

Chuẩn bị để tích hợp Ethereum Attestation Service:

```typescript
// Claim đã có sẵn các fields cho EAS
{
  "eas_uid": "0xabc123...",
  "attester_address": "0x9876...",
  "verified_at": "2024-06-15T12:00:00",
  "verified_by": "org_techcorp"
}
```

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **Embedding**: SentenceTransformers (`paraphrase-mpnet-base-v2`)
- **Vector Search**: FAISS
- **LLM**: OpenAI GPT-4o-mini
- **Data Storage**: JSON (ready for Neo4j migration)
- **Future**: EAS (Ethereum Attestation Service)

## 📦 Dependencies

```txt
streamlit
openai
sentence-transformers
faiss-cpu
pandas
numpy
tf-keras
```

## License

MIT License - Free to use for educational purposes.

## Author

Tran Thi Hong Ngoc - B2207546

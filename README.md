# Multi-user Interactive RAG Application

Ứng dụng RAG (Retrieval-Augmented Generation) cho phép nhiều người dùng truy vấn thông tin với hệ thống phân quyền dựa trên Viewer ID và Target User ID.

## Cấu trúc dự án

```
RAG/
├── app.py                      # Entry point - khởi động ứng dụng
├── config.py                   # Configuration & constants
├── data_mock.csv               # Dữ liệu mẫu (Knowledge Graph)
├── requirements.txt            # Dependencies
├── README.md                   # Documentation
│
├── .streamlit/
│   └── secrets.toml            # API keys (OpenAI)
│
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── data_loader.py          # Load/save CSV data
│   ├── document_processor.py   # Tạo summary với OpenAI
│   ├── embeddings.py           # SentenceTransformer & FAISS index
│   ├── gatekeeper.py           # Access control logic
│   ├── rag_engine.py           # RAG pipeline chính
│   └── triple_extractor.py     # AI extract triples từ text
│
└── ui/                         # UI components
    ├── __init__.py
    ├── sidebar.py              # Sidebar - Form nhập liệu
    └── main_content.py         # Main content - Query interface
```

## Cách khởi tạo dự án

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

## Mô tả các module

### Core Modules

| Module | Chức năng |
|--------|-----------|
| `config.py` | Chứa API keys, constants, model settings |
| `utils/data_loader.py` | Load/save dữ liệu CSV |
| `utils/document_processor.py` | Tạo document summary với OpenAI |
| `utils/embeddings.py` | Embedding với SentenceTransformer, FAISS index |
| `utils/gatekeeper.py` | Logic phân quyền (Owner/Recruiter/Public) |
| `utils/rag_engine.py` | Pipeline RAG: Retrieve + Generate |
| `utils/triple_extractor.py` | AI extract triples từ text tự nhiên |

### UI Modules

| Module | Chức năng |
|--------|-----------|
| `ui/sidebar.py` | Form nhập liệu thân thiện (giống LinkedIn) |
| `ui/main_content.py` | Viewer/Target selection, Query interface |

## Logic phân quyền (Gatekeeper)

```
┌─────────────────────────────────────────────────────────┐
│                    Gatekeeper Logic                      │
├─────────────────────────────────────────────────────────┤
│ Bước 1 (Scope): Lọc dữ liệu theo Target User ID         │
│ Bước 2 (Access Control):                                 │
│   - Owner (Viewer == Target): Xem TẤT CẢ                │
│   - Recruiter: Xem public + verified data               │
│   - Public/Anonymous: Chỉ xem public                    │
└─────────────────────────────────────────────────────────┘
```

## Cách nhập dữ liệu

### Form nhập liệu thân thiện

Thay vì nhập trực tiếp `Source -> Relation -> Target`, người dùng nhập:

1. **Loại thông tin**: Kinh nghiệm, Kỹ năng, Dự án, Chứng chỉ, Học vấn
2. **Nội dung mô tả**: Viết tự nhiên như trên LinkedIn
3. **Link bằng chứng**: URL GitHub, LinkedIn, Certificate...
4. **Chế độ hiển thị**: Public / Private / Connections Only
5. **Trạng thái xác minh**: Self-declared / Attested / Pending

### AI Auto-Extract

Hệ thống sử dụng OpenAI để tự động chuyển đổi:

**Input (User nhập)**:
```
"Tôi dùng Python để xây dựng backend cho dự án Tiki trong 2 năm"
```

**Output (AI extract)**:
```json
[
  {"Source": "User_A", "Relation": "HAS_SKILL", "Target": "Python"},
  {"Source": "User_A", "Relation": "WORKED_ON", "Target": "Tiki Backend"},
  {"Source": "User_A", "Relation": "HAS_EXPERIENCE", "Target": "2 years Backend Development"}
]
```

## Data Schema

File `data_mock.csv` có cấu trúc:

| Column | Mô tả | Ví dụ |
|--------|-------|-------|
| Source | User ID / Entity | `Goby`, `Alice` |
| Relation | Loại quan hệ | `HAS_SKILL`, `WORKED_ON` |
| Target | Đối tượng | `Python`, `TechCorp` |
| Evidence | Link bằng chứng | `github.com/...` |
| Access_Level | Quyền xem | `public`, `private` |
| Status | Trạng thái xác minh | `attested`, `pending` |

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **Embedding**: SentenceTransformers (`paraphrase-mpnet-base-v2`)
- **Vector Search**: FAISS
- **LLM**: OpenAI GPT-4o-mini
- **Data Storage**: CSV (có thể mở rộng sang Neo4j)

## License

MIT License - Free to use for educational purposes.

## Author

Tran Thi Hong Ngoc - B2207546

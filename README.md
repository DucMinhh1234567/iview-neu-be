# AI Interview Backend System

Hệ thống backend Flask cho ứng dụng phỏng vấn AI với Supabase (PostgreSQL + pgvector + Auth + Storage).

## Tính Năng Chính

- ✅ **Supabase Integration**: PostgreSQL database với pgvector extension
- ✅ **Authentication**: Supabase Auth với JWT tokens
- ✅ **File Storage**: Hybrid storage (Local/Supabase Storage)
- ✅ **Vector Search**: pgvector cho semantic similarity search
- ✅ **AI Integration**: Gemini 2.5-flash cho question generation và answer evaluation
- ✅ **Question Review Workflow**: Generate → Review → Edit → Approve workflow
- ✅ **Session Types**: EXAM, PRACTICE, INTERVIEW
- ✅ **Bloom Taxonomy**: Difficulty levels với hierarchical selection

## Cài Đặt

### 1. Clone repository và navigate to backend

```bash
cd be
```

### 2. Tạo virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 4. Cấu hình environment variables

```bash
cp env.example .env
# Chỉnh sửa .env với các giá trị thực tế
```

**Lưu ý:** File mẫu là `env.example` (không có dấu chấm ở đầu). Sau khi copy, đổi tên thành `.env` để Flask tự động load.

### 5. Setup Supabase Database

1. Tạo Supabase project
2. Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Run migration script từ `.docs/supabase.sql` (đã được update)
4. Tạo storage buckets:
   - Vào Supabase Dashboard → Storage
   - Tạo bucket `materials`:
     - Name: `materials`
     - Public: ✅ **Yes** (public bucket)
   - Tạo bucket `private`:
     - Name: `private`
     - Public: ❌ **No** (private bucket, cho CVs và JDs)
     - **Quan trọng:** Bucket này bắt buộc phải có để upload CV/JD

### 6. Chạy ứng dụng

```bash
python app.py
```

Ứng dụng sẽ chạy tại `http://localhost:5000`

## Environment Variables

Xem `.env.example` để biết chi tiết các biến môi trường cần thiết.

**Quan trọng:**
- `SUPABASE_URL`: URL của Supabase project
- `SUPABASE_KEY`: Service role key (cho backend operations)
- `SUPABASE_ANON_KEY`: Anon key (optional, cho public access)
- `GEMINI_API_KEY`: Google Gemini API key
- `USE_SUPABASE_STORAGE`: `false` cho development (local), `true` cho production

## Cấu Trúc Thư Mục

```
be/
├── app.py                    # Flask entry point
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── .env.example             # Environment template
├── README.md                # Documentation
│
├── blueprints/              # API routes
│   ├── auth.py
│   ├── materials.py
│   ├── sessions.py
│   ├── questions.py
│   ├── student_sessions.py
│   └── review.py
│
├── extensions/              # Core integrations
│   ├── supabase_client.py
│   ├── llm.py
│   └── auth_middleware.py
│
├── utils/                   # Utilities
│   ├── storage.py
│   ├── semantic_chunking.py
│   ├── vector_search.py
│   ├── question_generator.py
│   ├── answer_evaluator.py
│   └── bloom_taxonomy.py
│
└── models/                  # Database models
    ├── user.py
    ├── material.py
    ├── session.py
    ├── question.py
    └── student_session.py
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Đăng ký
- `POST /api/auth/login` - Đăng nhập
- `POST /api/auth/logout` - Đăng xuất
- `GET /api/auth/user` - Lấy thông tin user

### Materials (Lecturer only)
- `POST /api/materials/upload` - Upload PDF
- `GET /api/materials` - Danh sách materials
- `GET /api/materials/<id>` - Chi tiết material
- `GET /api/materials/<id>/download` - Download PDF
- `DELETE /api/materials/<id>` - Xóa material

### Sessions
- `POST /api/sessions/exam` - Tạo EXAM session
- `POST /api/sessions/practice` - Tạo PRACTICE session
- `POST /api/sessions/interview` - Tạo INTERVIEW session
- `GET /api/sessions` - Danh sách sessions
- `GET /api/sessions/<id>` - Chi tiết session

### Questions
- `POST /api/questions/generate` - Generate questions
- `GET /api/questions/session/<id>` - Get questions
- `PUT /api/questions/<id>` - Edit question
- `POST /api/questions/approve` - Approve questions
- `POST /api/questions/generate-answers` - Generate reference answers
- `PUT /api/questions/<id>/answer` - Edit reference answer
- `POST /api/questions/approve-answers` - Approve answers

### Session Script
- `POST /api/sessions/<id>/generate-script` - Generate script
- `GET /api/sessions/<id>/script` - Get script
- `PUT /api/sessions/<id>/script` - Edit script
- `POST /api/sessions/<id>/finalize` - Finalize session

### Student Sessions
- `POST /api/student-sessions/join` - Join session
- `POST /api/student-sessions/<id>/start` - Start session
- `GET /api/student-sessions/<id>/question` - Get next question
- `POST /api/student-sessions/<id>/answer` - Submit answer
- `POST /api/student-sessions/<id>/end` - End session
- `GET /api/student-sessions/<id>` - Get results
- `GET /api/student-sessions/history` - Get history

### Review (Lecturer only)
- `GET /api/review/sessions` - List sessions to review
- `GET /api/review/sessions/<id>/students` - List students
- `GET /api/review/student-sessions/<id>` - Get student session
- `PUT /api/review/answers/<id>/score` - Edit score
- `PUT /api/review/answers/<id>/feedback` - Edit feedback

## Workflow

### Question Generation Workflow
1. Generate questions (draft)
2. Lecturer reviews & edits questions
3. Approve questions
4. Generate reference answers
5. Lecturer reviews & edits answers
6. Approve answers
7. Generate opening/closing script
8. Lecturer reviews & edits script
9. Finalize session

### Student Participation Flow
1. Join session (password validation)
2. Start session
3. Get next question
4. Submit answer (AI evaluation)
5. Repeat until done
6. End session (overall evaluation)

## License

See original project license.


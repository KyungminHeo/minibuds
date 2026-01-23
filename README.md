# Minibuds - PDF RAG System

PDF 문서 기반 RAG(Retrieval-Augmented Generation) 시스템입니다. 문서를 업로드하고 AI와 대화형으로 정보를 검색할 수 있습니다.

## ✨ 주요 기능

- **PDF 문서 업로드 및 관리** - PDF 파일 업로드, 텍스트 추출, 청킹 처리
- **벡터 검색** - pgvector를 활용한 시맨틱 검색
- **RAG 기반 질의응답** - 문서 컨텍스트 기반 AI 응답 생성
- **LLM 다중 지원** - OpenAI, Google Gemini 지원
- **대화 관리** - 대화 이력 저장 및 조회

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| **Backend** | FastAPI, Python |
| **Database** | PostgreSQL + pgvector |
| **AI/ML** | OpenAI API, Google Gemini API |
| **PDF 처리** | pdfplumber |
| **ORM** | SQLAlchemy |

## 📁 프로젝트 구조

```
minibuds/
├── src/
│   └── app/
│       ├── main.py              # FastAPI 앱 진입점
│       ├── core/                # 설정, DB 연결
│       ├── models/              # SQLAlchemy 모델
│       ├── schemas/             # Pydantic 스키마
│       ├── crud/                # DB CRUD 작업
│       ├── routes/              # API 엔드포인트
│       │   ├── upload_route     # 파일 업로드
│       │   ├── search_route     # 검색
│       │   ├── conversation_route # 대화
│       │   ├── document_route   # 문서 관리
│       │   └── ask_route        # LLM 질의
│       └── services/
│           ├── ai/              # AI 서비스 (임베딩, 생성)
│           ├── chunk_service    # 청킹 처리
│           └── file_service     # 파일 처리
├── scripts/                     # 유틸리티 스크립트
└── tests/                       # 테스트 코드
```

## 🚀 시작하기

### 사전 요구사항

- Python 3.10+
- PostgreSQL (pgvector 확장)
- OpenAI API Key 또는 Google API Key

### 설치

1. **저장소 클론**
   ```bash
   git clone https://github.com/KyungminHeo/minibuds.git
   cd minibuds
   ```

2. **가상환경 생성 및 활성화**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   ```

3. **의존성 설치**
   ```bash
   pip install -r src/app/requirements.txt
   ```

4. **PostgreSQL + pgvector 실행** (Docker 사용)
   ```bash
   cd src/app
   docker-compose up -d
   ```

5. **환경변수 설정**
   
   `src/.env.development` 파일을 참고하여 `.env` 파일 생성:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/rag_db
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_API_KEY=your_google_api_key
   CHUNK_SIZE=1000
   CHUNK_OVERLAP=100
   ```

6. **서버 실행**
   ```bash
   cd src/app
   uvicorn main:app --reload
   ```

   서버가 `http://localhost:8000`에서 실행됩니다.

## 📡 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/api/v1/upload` | PDF 파일 업로드 |
| `GET` | `/api/v1/documents` | 문서 목록 조회 |
| `POST` | `/api/v1/search` | 문서 검색 |
| `POST` | `/api/v1/ask` | LLM 질의 |
| `POST` | `/api/v1/conversations` | 대화 생성 |
| `GET` | `/api/v1/conversations` | 대화 목록 조회 |

## 📝 License

This project is licensed under the MIT License.

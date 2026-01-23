from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.database import engine, Base
# Models를 import해야 테이블이 생성됩니다
from app.models import user, document, history, conversation
from app.routes import upload_route, search_route, user_route, conversation_route, document_route, ask_route

app = FastAPI(title="PDF RAG System")

# ✅ CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"  # Vite 개발 서버
    ],
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST, DELETE 등)
    allow_headers=["*"],  # 모든 헤더 허용
)

app.include_router(user_route.router, prefix="/api/v1")
app.include_router(document_route.router, prefix="/api/v1")
app.include_router(upload_route.router, prefix="/api/v1")
app.include_router(search_route.router, prefix="/api/v1")
app.include_router(conversation_route.router, prefix="/api/v1")
app.include_router(ask_route.router, prefix="/api/v1")

@app.on_event("startup")
def on_startup():
    # pgvector 확장 기능 활성화 (필수)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    
    # 테이블 자동 생성 (실무에선 Alembic 사용 권장)
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "RAG Server Running"}
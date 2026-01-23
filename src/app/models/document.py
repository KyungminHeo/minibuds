from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import String, Text, ForeignKey, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
from app.core.database import Base

# 플랫폼별 임베딩 차원
OPENAI_EMBEDDING_DIMENSION = 1536  # text-embedding-3-small
GEMINI_EMBEDDING_DIMENSION = 768   # text-embedding-004

def kst_now():
    return datetime.now(ZoneInfo("Asia/Seoul"))

# 문서 테이블 (플랫폼 무관 - 메타데이터만 저장)
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String, index=True)
    file_path: Mapped[str] = mapped_column(String)
    uploaded_at: Mapped[datetime] = mapped_column(default=kst_now)
    
    # 임베딩 비용 추적
    embedding_tokens: Mapped[int] = mapped_column(default=0)
    embedding_cost_usd: Mapped[float] = mapped_column(default=0.0)

    # N:1 관계 - 여러 문서가 한 사용자에 속함
    user = relationship("User", back_populates="documents")
    
    # 1:N 관계 - 플랫폼별 청크 테이블과 연결
    openai_chunks = relationship("OpenAIChunk", back_populates="document", cascade="all, delete")
    gemini_chunks = relationship("GeminiChunk", back_populates="document", cascade="all, delete")

# OpenAI 전용 청크 테이블 (1536차원)
class OpenAIChunk(Base):
    __tablename__ = "openai_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int] = mapped_column(default=1)
    
    # OpenAI text-embedding-3-small: 1536차원
    embedding = mapped_column(Vector(OPENAI_EMBEDDING_DIMENSION))
    
    # Full-Text Search용 tsvector 컬럼 (자동 생성 및 인덱스)
    content_tsv = mapped_column(
        TSVECTOR,
        index=True  # GIN 인덱스 생성
    )
    
    document = relationship("Document", back_populates="openai_chunks")

# Gemini 전용 청크 테이블 (768차원)
class GeminiChunk(Base):
    __tablename__ = "gemini_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int] = mapped_column(default=1)
    
    # Gemini text-embedding-004: 768차원
    embedding = mapped_column(Vector(GEMINI_EMBEDDING_DIMENSION))
    
    # Full-Text Search용 tsvector 컬럼 (자동 생성 및 인덱스)
    content_tsv = mapped_column(
        TSVECTOR,
        index=True  # GIN 인덱스 생성
    )
    
    document = relationship("Document", back_populates="gemini_chunks")
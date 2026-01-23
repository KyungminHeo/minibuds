from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base
import enum

def kst_now():
    return datetime.now(ZoneInfo("Asia/Seoul"))

class PlatformEnum(str, enum.Enum):
    """지원하는 AI 플랫폼"""
    OPENAI = "openai"
    GEMINI = "gemini"

class User(Base):
    """사용자 테이블 - AI 플랫폼 선택 정보 포함"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # 사용자가 선택한 AI 플랫폼 (openai 또는 gemini)
    platform: Mapped[str] = mapped_column(
        SQLEnum(PlatformEnum, native_enum=False, length=20),
        default=PlatformEnum.OPENAI,
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(default=kst_now)
    updated_at: Mapped[datetime] = mapped_column(default=kst_now, onupdate=kst_now)
    
    # 1:N 관계 - 한 사용자는 여러 문서를 가질 수 있음
    documents = relationship("Document", back_populates="user", cascade="all, delete")
    
    # 1:N 관계 - 한 사용자는 여러 대화 세션을 가질 수 있음
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete")

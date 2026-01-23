from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

def kst_now():
    return datetime.now(ZoneInfo("Asia/Seoul"))

class Conversation(Base):
    """대화 세션 테이블 - GPT/Gemini처럼 대화를 그룹화"""
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))  # 대화 제목
    
    created_at: Mapped[datetime] = mapped_column(default=kst_now)
    updated_at: Mapped[datetime] = mapped_column(default=kst_now, onupdate=kst_now)
    
    # N:1 관계 - 한 세션은 한 사용자에게 속함
    user = relationship("User", back_populates="conversations")
    
    # 1:N 관계 - 한 세션은 여러 메시지를 가짐
    messages = relationship("ChatHistory", back_populates="conversation", cascade="all, delete-orphan")

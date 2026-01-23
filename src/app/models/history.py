from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import Text, Integer, Float, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

def kst_now():
    return datetime.now(ZoneInfo("Asia/Seoul"))

# 채팅 히스토리 테이블 (사용자별 비용 추적)
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    
    # 비용 추적 필드
    platform: Mapped[str] = mapped_column(String(20))  # 사용된 플랫폼
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)  # 총 토큰 수
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)   # 입력 토큰
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)  # 출력 토큰
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)  # 예상 비용 (USD)
    
    created_at: Mapped[datetime] = mapped_column(default=kst_now)
    
    # N:1 관계
    user = relationship("User")
    conversation = relationship("Conversation", back_populates="messages")
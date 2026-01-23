"""
Chat History CRUD - 사용자별 비용 추적
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.history import ChatHistory

def create_chat_history(
    db: Session, 
    user_id: int,
    conversation_id: int,
    question: str, 
    answer: str, 
    platform: str,
    token_info: dict,
    estimated_cost: float
) -> ChatHistory:
    """채팅 기록 저장 (비용 추적 포함)"""
    history = ChatHistory(
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        answer=answer,
        platform=platform,
        total_tokens=token_info.get("total_tokens", 0),
        input_tokens=token_info.get("input_tokens", 0),
        output_tokens=token_info.get("output_tokens", 0),
        estimated_cost_usd=estimated_cost
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history

def get_user_total_cost(db: Session, user_id: int) -> float:
    """사용자의 총 누적 비용 조회"""
    result = db.query(func.sum(ChatHistory.estimated_cost_usd)).filter(
        ChatHistory.user_id == user_id
    ).scalar()
    return result or 0.0

def get_user_chat_history(db: Session, user_id: int, skip: int = 0, limit: int = 50):
    """사용자의 채팅 기록 조회"""
    return db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.created_at.desc()).offset(skip).limit(limit).all()

def get_conversation_messages(db: Session, conversation_id: int, skip: int = 0, limit: int = 100):
    """특정 대화 세션의 메시지 조회 (시간순 정렬)"""
    return db.query(ChatHistory).filter(
        ChatHistory.conversation_id == conversation_id
    ).order_by(ChatHistory.created_at.asc()).offset(skip).limit(limit).all()

"""
Conversation CRUD - 대화 세션 관리
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.conversation import Conversation
from app.models.history import ChatHistory
from datetime import datetime
from zoneinfo import ZoneInfo

def kst_now():
    return datetime.now(ZoneInfo("Asia/Seoul"))

def create_conversation(db: Session, user_id: int, title: str) -> Conversation:
    """새 대화 세션 생성"""
    conversation = Conversation(
        user_id=user_id,
        title=title
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def get_conversation(db: Session, conversation_id: int) -> Conversation:
    """대화 세션 조회"""
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()

def list_user_conversations(db: Session, user_id: int, skip: int = 0, limit: int = 50):
    """사용자의 대화 세션 목록 조회 (최근 업데이트 순)"""
    return db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(desc(Conversation.updated_at)).offset(skip).limit(limit).all()

def update_conversation_title(db: Session, conversation_id: int, new_title: str) -> Conversation:
    """대화 세션 제목 수정"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise ValueError(f"Conversation {conversation_id}를 찾을 수 없습니다.")
    
    conversation.title = new_title
    db.commit()
    db.refresh(conversation)
    return conversation

def update_conversation_timestamp(db: Session, conversation_id: int):
    """대화 세션의 마지막 업데이트 시간 갱신 (새 메시지 추가 시)"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = kst_now()
        db.commit()

def delete_conversation(db: Session, conversation_id: int) -> bool:
    """대화 세션 삭제 (CASCADE로 관련 메시지도 삭제)"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        return False
    
    db.delete(conversation)
    db.commit()
    return True

def get_conversation_message_count(db: Session, conversation_id: int) -> int:
    """대화 세션의 메시지 개수 조회"""
    return db.query(func.count(ChatHistory.id)).filter(
        ChatHistory.conversation_id == conversation_id
    ).scalar() or 0

def list_user_conversations_with_counts(db: Session, user_id: int, skip: int = 0, limit: int = 50):
    """
    사용자의 대화 세션 목록 + 메시지 수를 한 번의 쿼리로 조회 (N+1 방지)
    
    Returns:
        List[Tuple[Conversation, int]]: [(conversation, message_count), ...]
    """
    # 서브쿼리: 대화별 메시지 수
    msg_count_subquery = (
        db.query(
            ChatHistory.conversation_id,
            func.count(ChatHistory.id).label("msg_count")
        )
        .group_by(ChatHistory.conversation_id)
        .subquery()
    )
    
    # 메인 쿼리: Conversation LEFT JOIN 메시지 수
    results = (
        db.query(Conversation, func.coalesce(msg_count_subquery.c.msg_count, 0))
        .outerjoin(msg_count_subquery, Conversation.id == msg_count_subquery.c.conversation_id)
        .filter(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return results

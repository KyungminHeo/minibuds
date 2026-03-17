"""
Conversation 관리 API - GPT/Gemini 스타일 대화 세션
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.dtos import (
    ConversationCreate, 
    ConversationResponse, 
    ConversationWithMessages,
    MessageResponse
)
from app.crud import conversation_crud, history_crud, user_crud

router = APIRouter(tags=["Conversations"])

@router.post("/conversations/", response_model=ConversationResponse)
def create_conversation(user_id: int, conversation_in: ConversationCreate, db: Session = Depends(get_db)):
    """새 대화 세션 생성"""
    # 사용자 존재 확인
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    
    conversation = conversation_crud.create_conversation(db, user_id, conversation_in.title)
    
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0
    )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """대화 세션 정보 조회"""
    conversation = conversation_crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(404, "대화 세션을 찾을 수 없습니다.")
    
    message_count = conversation_crud.get_conversation_message_count(db, conversation_id)
    
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count
    )

@router.get("/users/{user_id}/conversations", response_model=List[ConversationResponse])
def list_user_conversations(user_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """사용자의 대화 세션 목록 조회 (최근 업데이트 순)"""
    # 사용자 존재 확인
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    
    conversations_with_counts = conversation_crud.list_user_conversations_with_counts(db, user_id, skip, limit)
    
    result = []
    for conv, msg_count in conversations_with_counts:
        result.append(ConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=msg_count
        ))
    
    return result

@router.get("/conversations/{conversation_id}/messages", response_model=ConversationWithMessages)
def get_conversation_messages(conversation_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """대화 세션의 메시지 목록 조회"""
    conversation = conversation_crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(404, "대화 세션을 찾을 수 없습니다.")
    
    messages = history_crud.get_conversation_messages(db, conversation_id, skip, limit)
    
    message_responses = [
        MessageResponse(
            id=msg.id,
            question=msg.question,
            answer=msg.answer,
            created_at=msg.created_at,
            platform=msg.platform,
            total_tokens=msg.total_tokens,
            estimated_cost_usd=msg.estimated_cost_usd
        )
        for msg in messages
    ]
    
    return ConversationWithMessages(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=message_responses
    )

@router.patch("/conversations/{conversation_id}/title")
def update_conversation_title(conversation_id: int, user_id: int, new_title: str, db: Session = Depends(get_db)):
    """대화 세션 제목 수정 (권한 검증 포함)"""
    conversation = conversation_crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(404, "대화 세션을 찾을 수 없습니다.")
    if conversation.user_id != user_id:
        raise HTTPException(403, "해당 대화 세션을 수정할 권한이 없습니다.")
    
    try:
        updated = conversation_crud.update_conversation_title(db, conversation_id, new_title)
        return {"message": f"제목이 '{updated.title}'로 변경되었습니다."}
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, user_id: int, db: Session = Depends(get_db)):
    """대화 세션 삭제 (메시지도 함께 삭제, 권한 검증 포함)"""
    conversation = conversation_crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(404, "대화 세션을 찾을 수 없습니다.")
    if conversation.user_id != user_id:
        raise HTTPException(403, "해당 대화 세션을 삭제할 권한이 없습니다.")
    
    success = conversation_crud.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(500, "대화 세션 삭제에 실패했습니다.")
    
    return {"message": "대화 세션이 삭제되었습니다."}

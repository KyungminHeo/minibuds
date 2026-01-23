from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

# Pydantic 데이터 검증 모델

# --- User 관련 ---
class UserCreate(BaseModel):
    username: str
    email: str
    platform: str  # "openai" or "gemini"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    platform: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserStats(BaseModel):
    """사용자 비용 통계"""
    user_id: int
    total_cost_usd: float
    total_queries: int

# --- Document 관련 ---
class DocumentCreate(BaseModel):
    filename: str
    file_path: str

class DocumentResponse(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    embedding_tokens: int = 0
    embedding_cost_usd: float = 0.0
    
    class Config:
        from_attributes = True

# --- Search & Chat 관련 ---
class SearchResult(BaseModel):
    id: int
    document_id: int
    file_name: str
    file_path: str
    page_number: Optional[int]
    content: str
    score: float  # RRF 점수 (Hybrid Search) 또는 유사도 점수

class ChatRequest(BaseModel):
    user_id: int  # 사용자 ID 추가
    question: str
    conversation_id: Optional[int] = None  # 대화 세션 ID (없으면 새 세션 생성)

class ChatResponse(BaseModel):
    question: str
    answer: str
    references: List[SearchResult] # 답변에 참고한 문서 리스트
    platform_used: str  # 사용된 플랫폼
    total_tokens: int
    estimated_cost_usd: float  # 이번 요청의 예상 비용
    conversation_id: int  # 생성 또는 사용된 대화 세션 ID

# --- Ask (LLM Only) 관련 ---
class AskRequest(BaseModel):
    """LLM Only 요청 (RAG 검색 없음)"""
    user_id: int
    question: str
    conversation_id: Optional[int] = None
    system_prompt: Optional[str] = None  # 커스텀 시스템 프롬프트 (선택)

class AskResponse(BaseModel):
    """LLM Only 응답 (참조 문서 없음)"""
    question: str
    answer: str
    platform_used: str
    total_tokens: int
    estimated_cost_usd: float
    conversation_id: int

# --- Conversation 관련 ---
class ConversationCreate(BaseModel):
    title: str

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    """대화 세션 내 개별 메시지"""
    id: int
    question: str
    answer: str
    created_at: datetime
    platform: str
    total_tokens: int
    estimated_cost_usd: float
    
    class Config:
        from_attributes = True

class ConversationWithMessages(BaseModel):
    """대화 세션과 메시지 목록"""
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]

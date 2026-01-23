"""
LLM Only 엔드포인트 - RAG 검색 없이 순수 LLM 대화
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.dtos import AskRequest, AskResponse
from app.services.ai.factory import AIServiceFactory
from app.services.ai.cost import CostCalculator
from app.services.ai.context_builder import build_conversation_context
from app.crud import history_crud, user_crud

router = APIRouter(tags=["Ask"])


@router.post("/ask/", response_model=AskResponse)
def ask_llm(request: AskRequest, db: Session = Depends(get_db)):
    """
    LLM Only 대화 (RAG 검색 없음)
    
    - 문서 검색/임베딩 없이 순수 LLM 대화
    - 이전 대화 컨텍스트는 유지
    - 커스텀 시스템 프롬프트 지원
    """
    
    # 1. 사용자 조회 및 플랫폼 확인
    user = user_crud.get_user(db, request.user_id)
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    
    platform = user.platform
    
    # 2. 대화 세션 처리 (conversation_id 없으면 새로 생성)
    from app.crud import conversation_crud
    
    if request.conversation_id:
        # 기존 세션 사용
        conversation = conversation_crud.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(404, "대화 세션을 찾을 수 없습니다.")
        if conversation.user_id != user.id:
            raise HTTPException(403, "해당 대화 세션에 접근할 수 없습니다.")
        conversation_id = request.conversation_id
    else:
        # 새 세션 생성 (제목은 질문의 첫 50자)
        title = request.question[:50] + ("..." if len(request.question) > 50 else "")
        new_conversation = conversation_crud.create_conversation(db, user.id, title)
        conversation_id = new_conversation.id
    
    # 3. 이전 대화 히스토리 조회 (최근 10개 - LLM Only는 더 많이)
    previous_messages = []
    if request.conversation_id:
        previous_messages = history_crud.get_conversation_messages(
            db, conversation_id, limit=10
        )
    
    # 4. LLM 서비스 선택
    llm_service = AIServiceFactory.get_llm_service(platform)
    
    # 5. 대화 컨텍스트 구성 (이전 대화만, 문서 검색 없음)
    conversation_context = build_conversation_context(
        previous_messages, 
        request.question
    )
    
    # 6. 커스텀 시스템 프롬프트 (선택)
    custom_prompt = request.system_prompt if request.system_prompt and request.system_prompt != "string" else None
    
    # 7. LLM 답변 생성 (RAG 아닌 순수 LLM 대화)
    answer_text, token_info = llm_service.generate_chat(
        query=request.question,
        context=conversation_context,  # 이전 대화 컨텍스트만
        system_prompt=custom_prompt
    )
    
    # 8. 비용 계산
    estimated_cost = CostCalculator.calculate_llm_cost(
        platform,
        token_info["input_tokens"],
        token_info["output_tokens"]
    )
    
    # 9. 히스토리 저장
    history_crud.create_chat_history(
        db, 
        user.id,
        conversation_id,
        request.question, 
        answer_text, 
        platform,
        token_info,
        estimated_cost
    )
    
    # 10. 대화 세션의 updated_at 갱신
    conversation_crud.update_conversation_timestamp(db, conversation_id)
    
    return AskResponse(
        question=request.question,
        answer=answer_text,
        platform_used=platform,
        total_tokens=token_info["total_tokens"],
        estimated_cost_usd=estimated_cost,
        conversation_id=conversation_id
    )

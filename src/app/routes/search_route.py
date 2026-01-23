from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.dtos import ChatRequest, ChatResponse, SearchResult
from app.services.ai.factory import AIServiceFactory
from app.services.ai.cost import CostCalculator
from app.services.ai.context_builder import build_conversation_context, rewrite_query_with_context
from app.crud import document_crud, history_crud, user_crud

router = APIRouter(tags=["Search"])

@router.post("/chat/", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """사용자의 플랫폼 기반 문서 검색 및 답변 생성"""
    
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
    
    # 3. 이전 대화 히스토리 조회 (최근 5개)
    previous_messages = []
    if request.conversation_id:
        previous_messages = history_crud.get_conversation_messages(
            db, conversation_id, limit=5
        )
    
    # 4. 플랫폼별 서비스 선택
    embed_service = AIServiceFactory.get_embedding_service(platform)
    llm_service = AIServiceFactory.get_llm_service(platform)
    
    # 5. 쿼리 재작성 (대명사 해결 - "그의 기술은?" → "허경민의 기술은?")
    search_query = rewrite_query_with_context(
        previous_messages, 
        request.question, 
        llm_service
    )
    
    # 6. 재작성된 쿼리로 임베딩 생성 및 검색 (Hybrid Search)
    query_vec = embed_service.create_embedding(search_query)
    results = document_crud.search_similar_chunks_hybrid(
        db, 
        platform, 
        user.id, 
        query_vec, 
        query_text=search_query,  # 재작성된 질문으로 Full-Text Search
        top_k=10
    )
    
    # [DEBUG] 검색 결과 로깅
    print(f"\n{'='*60}")
    print(f"[DEBUG] 원본 질문: {request.question}")
    print(f"[DEBUG] 재작성된 검색 쿼리: {search_query}")
    print(f"[DEBUG] 검색 결과 수: {len(results)}")
    for i, (chunk, score) in enumerate(results[:5]):  # 상위 5개만
        print(f"\n[DEBUG] 청크 {i+1} (score={score:.4f}, doc_id={chunk.document_id}, page={chunk.page_number}):")
        print(f"        {chunk.content[:150]}...")
    print(f"{'='*60}\n")
    
    # 7. 문서 Context 구성
    if not results:
        document_context = ""
    else:
        document_context = "\n\n".join([chunk.content for chunk, score in results])
    
    # 8. 대화 히스토리 Context 구성 (LLM 프롬프트용)
    conversation_context = build_conversation_context(
        previous_messages, 
        request.question
    )
    
    # 9. 최종 Context = 대화 히스토리 + 문서 내용
    if conversation_context:
        full_context = f"{conversation_context}\n\n[참고 문서]\n{document_context}"
    else:
        full_context = document_context
    
    # 10. LLM 답변 생성
    answer_text, token_info = llm_service.generate_answer(request.question, full_context)
    
    # 11. 비용 계산
    estimated_cost = CostCalculator.calculate_llm_cost(
        platform,
        token_info["input_tokens"],
        token_info["output_tokens"]
    )
    
    # 12. 히스토리 저장 (conversation_id 포함)
    history_crud.create_chat_history(
        db, 
        user.id,
        conversation_id,  # 대화 세션 ID 추가
        request.question, 
        answer_text, 
        platform,
        token_info,
        estimated_cost
    )
    
    # 13. 대화 세션의 updated_at 갱신
    conversation_crud.update_conversation_timestamp(db, conversation_id)
    
    # 14. 응답 데이터 구성 (점수 기반 필터링)
    MIN_SCORE_THRESHOLD = 0.005  # 최소 점수 기준
    references = []
    
    if results:
        # 상위 점수 기준으로 필터링 (상위 점수의 50% 미만은 제외)
        top_score = results[0][1]
        relative_threshold = top_score * 0.5
        
        for chunk, score in results:
            # 점수가 너무 낮으면 제외
            if score < MIN_SCORE_THRESHOLD or score < relative_threshold:
                continue
                
            ref = SearchResult(
                id=chunk.id,
                document_id=chunk.document_id,
                file_name=chunk.document.filename,
                file_path=chunk.document.file_path,
                page_number=chunk.page_number,
                content=chunk.content[:200] + "...",
                score=score
            )
            references.append(ref)
    
    return ChatResponse(
        question=request.question,
        answer=answer_text,
        references=references,
        platform_used=platform,
        total_tokens=token_info["total_tokens"],
        estimated_cost_usd=estimated_cost,
        conversation_id=conversation_id
    )
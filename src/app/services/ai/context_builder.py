"""
대화 컨텍스트 빌더 - 이전 대화 히스토리를 프롬프트에 포함

[왜 필요한가?]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
사용자가 "그게 뭐야?", "더 자세히 설명해줘" 같은 후속 질문을 할 때
이전 대화 맥락 없이는 "그"가 무엇인지 알 수 없습니다.

[해결책]
1. 이전 대화를 LLM 프롬프트에 포함
2. 대화가 길어지면 토큰 제한 내에서 최근 대화만 포함
3. 대명사가 포함된 질문을 독립적 질문으로 재작성 (검색 정확도 향상)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from typing import List, TYPE_CHECKING
from app.models.history import ChatHistory

# 순환 import 방지: 타입 힌트에만 사용
if TYPE_CHECKING:
    from app.services.ai.base import BaseLLMService


def build_conversation_context(previous_messages: List[ChatHistory], current_question: str, max_history_tokens: int = 2000) -> str:
    """
    이전 대화 히스토리를 프롬프트 컨텍스트로 변환
    
    [반환 예시]
    [이전 대화]
    사용자: 허경민에 대해 알려줘
    AI: 허경민은 덱스컨설팅 소속 개발자입니다...
    
    [현재 질문]
    그가 사용하는 기술은?
    
    Args:
        previous_messages: ChatHistory 객체 리스트 (시간순 정렬)
        current_question: 현재 사용자 질문
        max_history_tokens: 히스토리에 할당할 최대 토큰 수
        
    Returns:
        포맷된 대화 컨텍스트 문자열
    """
    if not previous_messages:
        return ""
    
    # 최신 메시지부터 역순으로 토큰 제한까지 포함
    context_parts = []
    estimated_tokens = 0
    
    for msg in reversed(previous_messages):
        # 간단한 토큰 추정 (한글 1글자 ≈ 1.5토큰)
        msg_tokens = int((len(msg.question) + len(msg.answer)) * 1.5)
        
        if estimated_tokens + msg_tokens > max_history_tokens:
            break
        
        context_parts.insert(0, f"사용자: {msg.question}\nAI: {msg.answer}")
        estimated_tokens += msg_tokens
    
    if not context_parts:
        return ""
    
    return "[이전 대화]\n" + "\n\n".join(context_parts) + "\n\n[현재 질문]\n" + current_question


def rewrite_query_with_context(previous_messages: List[ChatHistory], current_question: str, llm_service: "BaseLLMService") -> str:
    """
    대명사/참조를 해결한 독립적 질문으로 재작성
    
    [왜 필요한가?]
    검색(임베딩) 시 "그의 기술 스택은?"만으로는 
    "허경민"을 찾을 수 없습니다.
    → "허경민의 기술 스택은 무엇인가요?"로 재작성
    
    Args:
        previous_messages: 이전 대화 목록
        current_question: 현재 질문 (대명사 포함 가능)
        llm_service: LLM 서비스 인스턴스 (팩토리에서 생성된 BaseLLMService)
        
    Returns:
        독립적으로 이해 가능한 재작성된 질문
    """
    if not previous_messages:
        return current_question
    
    # 최근 2개 대화만 참조 (토큰 절약)
    recent = previous_messages[-2:]
    history_text = "\n".join([
        f"Q: {m.question}\nA: {m.answer[:300]}..." if len(m.answer) > 300 else f"Q: {m.question}\nA: {m.answer}"
        for m in recent
    ])
    
    rewrite_prompt = f"""아래 대화 기록을 참고하여, 현재 질문을 대명사 없이 독립적인 질문으로 재작성하세요.
    재작성된 질문만 출력하세요. 추가 설명 없이 질문만 작성하세요.

    [대화 기록]
    {history_text}

    [현재 질문]
    {current_question}

    [재작성된 질문]"""
    
    try:
        rewritten, _ = llm_service.generate_answer(rewrite_prompt, "")
        rewritten = rewritten.strip()
        
        # 재작성 실패 시 원본 반환
        if not rewritten or len(rewritten) < 3:
            return current_question
            
        return rewritten
    except Exception:
        # LLM 호출 실패 시 원본 질문 사용
        return current_question
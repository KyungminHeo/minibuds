"""
Gemini 플랫폼 전용 LLM 서비스
OpenAI와 동일한 인터페이스 구현
"""
from typing import Tuple
from app.services.ai.base import BaseLLMService
from app.services.ai.client import get_google_client, retry_on_google_errors
from app.services.ai.utils import truncate_text

class GeminiLLMService(BaseLLMService):
    def __init__(self):
        self.client = get_google_client()
        self.model = "gemini-2.5-flash"
        # Context 길이 제한
        self.max_context_tokens = 10000

    @retry_on_google_errors
    def generate_answer(self, query: str, context: str) -> Tuple[str, dict]:
        """
        질문과 컨텍스트 기반 답변 생성
        
        Returns:
            (답변 텍스트, 토큰 정보)
        """
         # Context가 너무 길면 자름
        safe_context = truncate_text(context, self.max_context_tokens)

        system_prompt = f"""
        당신은 전문적인 문서 분석 및 질의응답 비서입니다.
        아래 [Context]에 제공된 정보에만 기반하여 사용자의 질문에 답변하세요.
        문서에 없는 내용은 추측하지 말고 "제공된 문서에서 정보를 찾을 수 없습니다"라고 답하세요.
        """
       
        prompt = f"""

        [Context]
        {safe_context}
        
        [질문]
        {query}
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "system_instruction": system_prompt,
                "temperature": 0.2, # RAG는 사실 기반이므로 낮게 설정
            }
        )
        
        answer = response.text
        
        # Gemini 토큰 정보 추출
        usage = response.usage_metadata if hasattr(response, 'usage_metadata') else None
        
        token_info = {
            "total_tokens": usage.total_token_count if usage else 0,
            "input_tokens": usage.prompt_token_count if usage else 0,
            "output_tokens": usage.candidates_token_count if usage else 0
        }
        
        return answer, token_info

    @retry_on_google_errors
    def generate_chat(self, query: str, context: str = "", system_prompt: str = None) -> Tuple[str, dict]:
        """
        순수 LLM 대화 (RAG 아님)
        
        - 문서 기반 제약 없음
        - 일반적인 AI 어시스턴트로 동작
        - 커스텀 시스템 프롬프트 지원
        
        Returns:
            (답변 텍스트, 토큰 정보)
        """
        safe_context = truncate_text(context, self.max_context_tokens) if context else ""
        
        # 기본 시스템 프롬프트 (RAG 제약 없음)
        default_system_prompt = """
        당신은 친절하고 전문적인 AI 어시스턴트입니다.
        사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.
        모르는 내용은 솔직하게 모른다고 말하고, 필요시 추가 정보를 요청하세요.
        """
        
        final_system_prompt = system_prompt if system_prompt else default_system_prompt
        
        # 대화 컨텍스트가 있으면 포함
        if safe_context:
            prompt = f"""
            {safe_context}

            [질문]
            {query}
            """
        else:
            prompt = query
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "system_instruction": final_system_prompt,
                "temperature": 0.7,  # 일반 대화는 좀 더 창의적으로
            }
        )
        
        answer = response.text
        
        usage = response.usage_metadata if hasattr(response, 'usage_metadata') else None
        
        token_info = {
            "total_tokens": usage.total_token_count if usage else 0,
            "input_tokens": usage.prompt_token_count if usage else 0,
            "output_tokens": usage.candidates_token_count if usage else 0
        }
        
        return answer, token_info

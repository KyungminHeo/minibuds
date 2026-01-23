"""
OpenAI 플랫폼 전용 LLM 서비스
기존 로직 유지: Context 잘라내기, retry
"""
from typing import Tuple
from app.services.ai.base import BaseLLMService
from app.services.ai.client import get_openai_client, retry_on_openai_errors
from app.services.ai.utils import truncate_text

class OpenAILLMService(BaseLLMService):
    def __init__(self):
        self.client = get_openai_client()
        self.model = "gpt-4o-mini"
        # 입력 프롬프트(Context + 질문)가 모델의 한계를 넘지 않도록 제한
        self.max_context_tokens = 10000 

    @retry_on_openai_errors
    def generate_answer(self, query: str, context: str) -> Tuple[str, dict]:
        """
        질문과 컨텍스트 기반 답변 생성
        
        Returns:
            (답변 텍스트, 토큰 정보)
        """
        # Context가 너무 길면 자름 (비용 절감 및 에러 방지)
        safe_context = truncate_text(context, self.max_context_tokens)

        system_prompt = f"""
        당신은 전문적인 문서 분석 및 질의응답 비서입니다.
        아래 [Context]에 제공된 정보에만 기반하여 사용자의 질문에 답변하세요.
        문서에 없는 내용은 추측하지 말고 "제공된 문서에서 정보를 찾을 수 없습니다"라고 답하세요.
        
        [Context]
        {safe_context}
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0
        )
        
        answer = response.choices[0].message.content
        
        # 토큰 정보 추출
        token_info = {
            "total_tokens": response.usage.total_tokens if response.usage else 0,
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0
        }
        
        return answer, token_info

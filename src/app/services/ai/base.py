"""
AI Service 인터페이스 정의
각 플랫폼(OpenAI, Gemini)은 이 인터페이스를 구현해야 합니다.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple

class BaseEmbeddingService(ABC):
    """임베딩 서비스 추상 클래스"""
    
    @abstractmethod
    def create_embedding(self, text: str) -> List[float]:
        """단일 텍스트의 임베딩 생성"""
        pass
    
    @abstractmethod
    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트의 임베딩을 배치로 생성 (성능 최적화)"""
        pass

class BaseLLMService(ABC):
    """LLM(질문 생성) 서비스 추상 클래스"""
    
    @abstractmethod
    def generate_answer(self, query: str, context: str) -> Tuple[str, dict]:
        """
        질문과 컨텍스트를 받아 답변 생성
        
        Returns:
            (답변 텍스트, 토큰 정보 딕셔너리)
            토큰 정보: {
                "total_tokens": int,
                "input_tokens": int,
                "output_tokens": int
            }
        """
        pass
    
    @abstractmethod
    def generate_chat(self, query: str, context: str = "", system_prompt: str = None) -> Tuple[str, dict]:
        """
        순수 LLM 대화 (RAG 검색 없음)
        
        - 문서 기반 제약 없이 일반적인 AI 어시스턴트로 동작
        - 커스텀 시스템 프롬프트 지원
        
        Returns:
            (답변 텍스트, 토큰 정보 딕셔너리)
        """
        pass

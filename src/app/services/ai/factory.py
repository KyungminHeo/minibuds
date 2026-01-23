"""
AI Service Factory - 플랫폼별 서비스 인스턴스 생성
"""
from app.services.ai.base import BaseEmbeddingService, BaseLLMService
from app.services.ai.openai_embedding import OpenAIEmbeddingService
from app.services.ai.gemini_embedding import GeminiEmbeddingService
from app.services.ai.openai_generation import OpenAILLMService
from app.services.ai.gemini_generation import GeminiLLMService

class AIServiceFactory:
    """플랫폼에 따라 AI 서비스 인스턴스를 생성하는 팩토리"""
    
    @staticmethod
    def get_embedding_service(platform: str) -> BaseEmbeddingService:
        """플랫폼에 맞는 임베딩 서비스 반환"""
        platform = platform.lower().strip()
        
        if platform == "openai":
            return OpenAIEmbeddingService()
        elif platform == "gemini":
            return GeminiEmbeddingService()
        else:
            raise ValueError(f"지원하지 않는 플랫폼: {platform}")
    
    @staticmethod
    def get_llm_service(platform: str) -> BaseLLMService:
        """플랫폼에 맞는 LLM 서비스 반환"""
        platform = platform.lower().strip()
        
        if platform == "openai":
            return OpenAILLMService()
        elif platform == "gemini":
            return GeminiLLMService()
        else:
            raise ValueError(f"지원하지 않는 플랫폼: {platform}")
    
    @staticmethod
    def get_chunk_model_class(platform: str):
        """플랫폼에 맞는 Chunk 모델 클래스 반환"""
        from app.models.document import OpenAIChunk, GeminiChunk
        
        platform = platform.lower().strip()
        
        if platform == "openai":
            return OpenAIChunk
        elif platform == "gemini":
            return GeminiChunk
        else:
            raise ValueError(f"지원하지 않는 플랫폼: {platform}")
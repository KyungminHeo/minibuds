"""
Gemini 플랫폼 전용 임베딩 서비스
OpenAI와 동일한 인터페이스 구현: 배치 처리, retry

🔥 중요: Anti-Caching 전략 + 한국어 검색 개선
- 매 호출마다 새 클라이언트 생성
- contents를 구조화된 형식으로 전달
- SEMANTIC_SIMILARITY로 한국어 의미 이해 개선
"""
from typing import List
from app.services.ai.base import BaseEmbeddingService
from app.services.ai.client import get_google_client, retry_on_google_errors

class GeminiEmbeddingService(BaseEmbeddingService):
    def __init__(self):
        # 모델명만 저장, 클라이언트는 매 호출마다 생성 (초강력 캐싱 방지)
        self.model = "models/text-embedding-004"
        # Gemini 배치 처리 제한
        self.max_batch_size = 100

    @retry_on_google_errors
    def create_embedding(self, text: str) -> List[float]:
        """
        단일 텍스트 임베딩 생성
        핵심 1: 매 호출마다 클라이언트를 새로 생성 (SDK 레벨 캐싱 완전 차단)
        핵심 2: contents를 구조화된 형식으로 전달 (객체 재사용 방지)
        핵심 3: SEMANTIC_SIMILARITY로 한국어 의미 이해 개선
        """
        # 매번 새 클라이언트 생성 (SDK 레벨 캐싱 방지)
        client = get_google_client()
        
        # contents와 config를 완전히 새로 생성
        result = client.models.embed_content(
            model=self.model,
            contents=[{
                "parts": [{"text": text}],
                "role": "user"
            }],
            config={
                "task_type": "SEMANTIC_SIMILARITY"  # 한국어 의미 이해 개선 (title 사용 불가)
            }
        )
        
        return result.embeddings[0].values

    @retry_on_google_errors
    def _send_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Gemini API로 배치 전송
        핵심: 각 텍스트마다 완전히 새로운 클라이언트 생성
        """
        embeddings = []
        for text in texts:
            # 매 루프마다 새 클라이언트 생성 (참조 오염 완전 차단)
            client = get_google_client()
            
            # 매번 새로운 contents와 config 객체 전달
            result = client.models.embed_content(
                model=self.model,
                contents=[{
                    "parts": [{"text": text}],
                    "role": "user"
                }],
                config={
                    "task_type": "SEMANTIC_SIMILARITY"  # 한국어 의미 이해 개선 (title 사용 불가)
                }
            )
            embeddings.append(result.embeddings[0].values)
        return embeddings

    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 리스트를 배치로 나누어 임베딩 생성 (async 래퍼)
        """
        return self._create_embeddings_batch_sync(texts)
    
    def _create_embeddings_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 리스트를 배치로 나누어 임베딩 생성 (동기 버전 - run_in_executor용)
        """
        all_embeddings = []
        
        # 배치 크기로 나눔
        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i:i + self.max_batch_size]
            embeddings = self._send_batch(batch)
            all_embeddings.extend(embeddings)
            print(f"[Embedding] Processed {min(i + self.max_batch_size, len(texts))}/{len(texts)} texts")
        
        return all_embeddings


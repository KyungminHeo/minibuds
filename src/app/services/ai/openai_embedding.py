"""
OpenAI 플랫폼 전용 임베딩 서비스
기존 로직 유지: 배치 처리, 토큰 제한, retry

🔥 중요: Gemini와 동일한 Anti-Caching 전략 적용
- 매 호출마다 새 클라이언트 생성
- user 파라미터로 각 요청을 고유하게 만들어 SDK 내부 캐싱 방지
"""
from typing import List
import hashlib
from app.services.ai.base import BaseEmbeddingService
from app.services.ai.client import get_openai_client, retry_on_openai_errors
from app.services.ai.utils import num_tokens_from_string

class OpenAIEmbeddingService(BaseEmbeddingService):
    def __init__(self):
        # 클라이언트는 매 호출마다 생성 (초강력 캐싱 방지)
        self.model = "text-embedding-3-small"
        # OpenAI 임베딩 API의 한 번 요청당 최대 토큰 제한 등을 고려한 안전값
        self.max_tokens_per_batch = 8000 

    @retry_on_openai_errors
    def create_embedding(self, text: str) -> List[float]:
        """
        단일 텍스트 임베딩 생성
        핵심 1: 매 호출마다 클라이언트를 새로 생성 (SDK 레벨 캐싱 완전 차단)
        핵심 2: user 파라미터로 각 요청을 고유하게 만들기 (SDK 내부 캐싱 방지)
        """
        # 매번 새 클라이언트 생성 (SDK 레벨 캐싱 방지)
        client = get_openai_client()
        
        # 텍스트 전처리
        text = text.replace("\n", " ")
        
        # 텍스트 해시로 고유한 user ID 생성 (SDK 내부 캐싱 우회)
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        
        # user 파라미터로 각 요청을 고유하게 만듦
        response = client.embeddings.create(
            input=[text],
            model=self.model,
            user=f"user_{text_hash}"  # 🔥 고유한 user로 SDK 캐싱 방지
        )
        return response.data[0].embedding

    @retry_on_openai_errors
    def _send_batch(self, inputs: List[str]) -> List[List[float]]:
        """
        실제 OpenAI로 배치를 전송하는 내부 메서드
        핵심: 배치마다 새 클라이언트 생성 및 고유한 user ID
        """
        # 매번 새 클라이언트 생성 (참조 오염 완전 차단)
        client = get_openai_client()
        
        # 배치 전체의 해시로 고유한 user ID 생성
        batch_content = "||".join(inputs)
        batch_hash = hashlib.md5(batch_content.encode()).hexdigest()[:8]
        
        # user 파라미터로 배치 요청을 고유하게 만듦
        response = client.embeddings.create(
            input=inputs,
            model=self.model,
            user=f"batch_{batch_hash}"  # 🔥 고유한 user로 SDK 캐싱 방지
        )
        # 결과 순서 보장 (index 기준 정렬)
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [data.embedding for data in sorted_data]

    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 리스트를 받아서 토큰 제한을 넘지 않도록 나누어(Batch) 임베딩을 생성합니다. (async 래퍼)
        """
        return self._create_embeddings_batch_sync(texts)
    
    def _create_embeddings_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 리스트를 받아서 토큰 제한을 넘지 않도록 나누어(Batch) 임베딩을 생성합니다.
        (동기 버전 - run_in_executor용)
        """
        all_embeddings = []
        batch = []
        batch_tokens = 0
        processed = 0
        
        for text in texts:
            text = text.replace("\n", " ")
            tokens = num_tokens_from_string(text)
            
            # 현재 배치가 꽉 차거나, 토큰 제한을 넘으려 하면 전송
            if batch and (batch_tokens + tokens > self.max_tokens_per_batch):
                embeddings = self._send_batch(batch)
                all_embeddings.extend(embeddings)
                processed += len(batch)
                print(f"[Embedding] Processed {processed}/{len(texts)} texts")
                batch = []
                batch_tokens = 0
            
            batch.append(text)
            batch_tokens += tokens
            
        # 남은 배치 전송
        if batch:
            embeddings = self._send_batch(batch)
            all_embeddings.extend(embeddings)
            processed += len(batch)
            print(f"[Embedding] Processed {processed}/{len(texts)} texts")
            
        return all_embeddings

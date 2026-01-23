import backoff
from openai import OpenAI, RateLimitError, APITimeoutError, InternalServerError, APIConnectionError
from google import genai
from app.core.config import settings
from typing import Callable

# --- OpenAI 클라이언트 관리 ---
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_openai_client() -> OpenAI:
    """OpenAI 클라이언트 인스턴스를 반환합니다."""
    return openai_client

def retry_on_openai_errors(func: Callable):
    """OpenAI API 호출 실패 시 재시도 데코레이터"""
    return backoff.on_exception(
        backoff.expo,
        (RateLimitError, APITimeoutError, InternalServerError, APIConnectionError),
        max_tries=5,
        jitter=backoff.full_jitter
    )(func)

# --- Google Gemini 클라이언트 관리 ---
def get_google_client():
    """Google Gemini 클라이언트 객체를 반환합니다. 매 요청마다 새로운 인스턴스 생성."""
    # 임베딩 캐싱 버그 방지를 위해 매번 새 클라이언트 생성
    return genai.Client(api_key=settings.GOOGLE_API_KEY)

def retry_on_google_errors(func: Callable):
    """Google Gemini API 호출 실패 시 재시도 데코레이터 (범용 처리)"""
    # Google API의 다양한 통신/서버 에러 처리를 위해 범용 Exception 처리 적용
    return backoff.on_exception(
        backoff.expo,
        (Exception), # 실제로는 google.api_core.exceptions의 특정 에러들을 추가해야 함
        max_tries=5,
        jitter=backoff.full_jitter
    )(func)
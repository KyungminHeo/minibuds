import tiktoken
from app.core.config import settings

# 전역 인코더 로드 (비용 절감)
# gpt-4o, gpt-4o-mini, text-embedding-3-small 등은 'cl100k_base' 또는 'o200k_base'를 씁니다.
# 호환성을 위해 cl100k_base를 기본으로 사용하거나 모델에 맞춰 가져옵니다.
try:
    encoding = tiktoken.get_encoding("cl100k_base")
except Exception:
    encoding = tiktoken.get_encoding("gpt2")

def num_tokens_from_string(string: str) -> int:
    """텍스트의 토큰 개수를 반환합니다."""
    return len(encoding.encode(string))

def truncate_text(text: str, max_tokens: int) -> str:
    """텍스트가 max_tokens를 넘으면 자릅니다."""
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    
    # 토큰을 자르고 다시 텍스트로 복원
    return encoding.decode(tokens[:max_tokens])
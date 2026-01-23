"""
플랫폼별 비용 계산 유틸리티
토큰 사용량을 기반으로 USD 비용을 추정합니다.
"""

class CostCalculator:
    """AI API 사용 비용 계산기"""
    
    # 2024년 12월 기준 가격 (1M 토큰당 USD)
    OPENAI_PRICES = {
        "gpt-4o-mini": {
            "input": 0.15,    # $0.15 / 1M input tokens
            "output": 0.60    # $0.60 / 1M output tokens
        },
        "text-embedding-3-small": {
            "input": 0.02,    # $0.02 / 1M tokens
            "output": 0.0
        }
    }
    
    GEMINI_PRICES = {
        "gemini-2.0-flash": {
            "input": 0.10,   # $0.075 / 1M input tokens (128k 이하)
            "output": 0.40    # $0.30 / 1M output tokens
        },
        "gemini-2.0-flash-lite": {  # 모델명 변경
            "input": 0.075,
            "output": 0.30
        },
        "text-embedding-004": {
            "input": 0.00,    # 무료
            "output": 0.0
        }
    }
    
    @staticmethod
    def calculate_llm_cost(platform: str, input_tokens: int, output_tokens: int) -> float:
        """
        LLM 사용 비용 계산
        
        Args:
            platform: "openai" or "gemini"
            input_tokens: 입력 토큰 수
            output_tokens: 출력 토큰 수
            
        Returns:
            예상 비용 (USD)
        """
        platform = platform.lower()
        
        if platform == "openai":
            prices = CostCalculator.OPENAI_PRICES["gpt-4o-mini"]
        elif platform == "gemini":
            prices = CostCalculator.GEMINI_PRICES["gemini-2.0-flash"]
        else:
            return 0.0
        
        # 1M 토큰당 가격이므로 1,000,000으로 나눔
        input_cost = (input_tokens / 1_000_000) * prices["input"]
        output_cost = (output_tokens / 1_000_000) * prices["output"]
        
        return round(input_cost + output_cost, 6)  # 소수점 6자리까지
    
    @staticmethod
    def calculate_embedding_cost(platform: str, total_tokens: int) -> float:
        """
        임베딩 사용 비용 계산
        
        Args:
            platform: "openai" or "gemini"
            total_tokens: 총 토큰 수
            
        Returns:
            예상 비용 (USD)
        """
        platform = platform.lower()
        
        if platform == "openai":
            prices = CostCalculator.OPENAI_PRICES["text-embedding-3-small"]
        elif platform == "gemini":
            prices = CostCalculator.GEMINI_PRICES["text-embedding-004"]
        else:
            return 0.0
        
        cost = (total_tokens / 1_000_000) * prices["input"]
        return round(cost, 6)

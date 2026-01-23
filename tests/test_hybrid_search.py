"""
Hybrid Search 검증 테스트 스크립트

이 스크립트는 Hybrid Search 기능이 제대로 작동하는지 테스트합니다.
"""
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_hybrid_search(user_id: int, question: str) -> Dict[str, Any]:
    """
    Hybrid Search 엔드포인트 테스트
    
    Args:
        user_id: 사용자 ID
        question: 검색 질문
    
    Returns:
        API 응답 결과
    """
    url = f"{BASE_URL}/chat/"
    payload = {
        "user_id": user_id,
        "question": question
    }
    
    print(f"\n{'='*60}")
    print(f"테스트 질문: {question}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"\n✓ 응답 성공!")
        print(f"\n답변: {result.get('answer', 'N/A')[:200]}...")
        print(f"\n검색된 문서 개수: {len(result.get('references', []))}")
        print(f"사용된 플랫폼: {result.get('platform_used', 'N/A')}")
        print(f"총 토큰: {result.get('total_tokens', 'N/A')}")
        
        if result.get('references'):
            print(f"\n상위 5개 검색 결과:")
            for i, ref in enumerate(result['references'][:5], 1):
                print(f"  {i}. {ref.get('file_name', 'N/A')} (페이지 {ref.get('page_number', 'N/A')}) - Score: {ref.get('distance', 'N/A'):.4f}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 요청 실패: {e}")
        return {}
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        return {}

def main():
    """메인 테스트 실행"""
    print("="*60)
    print("Hybrid Search 검증 테스트")
    print("="*60)
    
    # 테스트 케이스들
    test_cases = [
        {
            "user_id": 1,
            "question": "연차 신청 방법",
            "description": "정확한 키워드 포함 테스트"
        },
        {
            "user_id": 1,
            "question": "휴가는 어떻게 내나요?",
            "description": "의미는 비슷하지만 단어가 다른 테스트"
        },
        {
            "user_id": 1,
            "question": "회사 복지 제도",
            "description": "광범위한 질문 테스트"
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n[테스트 {i}/{len(test_cases)}] {test_case['description']}")
        result = test_hybrid_search(test_case['user_id'], test_case['question'])
        results.append({
            "test_case": test_case,
            "result": result
        })
    
    print("\n\n" + "="*60)
    print("테스트 완료!")
    print("="*60)
    print(f"총 {len(test_cases)}개 테스트 실행")
    print(f"성공: {sum(1 for r in results if r['result'])}개")
    print(f"실패: {sum(1 for r in results if not r['result'])}개")

if __name__ == "__main__":
    main()

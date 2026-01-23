"""
간단한 E2E 테스트 스크립트
서버가 실행 중이어야 합니다: uvicorn app.main:app --reload
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_create_users():
    """사용자 생성 테스트"""
    print("\n=== 1. 사용자 생성 테스트 ===")
    
    # OpenAI 사용자
    response = requests.post(
        f"{BASE_URL}/users/",
        json={
            "username": "test_openai",
            "email": "test_openai@example.com",
            "platform": "openai"
        }
    )
    print(f"OpenAI 사용자 생성: {response.status_code}")
    if response.status_code == 200:
        user1 = response.json()
        print(f"  - ID: {user1['id']}, Platform: {user1['platform']}")
    
    # Gemini 사용자
    response = requests.post(
        f"{BASE_URL}/users/",
        json={
            "username": "test_gemini",
            "email": "test_gemini@example.com",
            "platform": "gemini"
        }
    )
    print(f"Gemini 사용자 생성: {response.status_code}")
    if response.status_code == 200:
        user2 = response.json()
        print(f"  - ID: {user2['id']}, Platform: {user2['platform']}")

def test_get_user():
    """사용자 조회 테스트"""
    print("\n=== 2. 사용자 조회 테스트 ===")
    
    response = requests.get(f"{BASE_URL}/users/1")
    if response.status_code == 200:
        user = response.json()
        print(f"사용자 조회 성공: {user['username']} ({user['platform']})")
    else:
        print(f"사용자 조회 실패: {response.status_code}")

def test_upload_pdf():
    """PDF 업로드 테스트 (파일이 있어야 함)"""
    print("\n=== 3. PDF 업로드 테스트 ===")
    print("⚠️  실제 PDF 파일 경로를 지정해야 합니다.")
    
    # 예시 (실제 파일 경로로 변경 필요)
    # with open("test.pdf", "rb") as f:
    #     response = requests.post(
    #         f"{BASE_URL}/upload/?user_id=1",
    #         files={"file": f}
    #     )
    #     print(f"업로드 결과: {response.status_code}")

def test_chat():
    """채팅 테스트 (문서가 업로드되어 있어야 함)"""
    print("\n=== 4. 채팅 테스트 ===")
    print("⚠️  먼저 PDF를 업로드해야 합니다.")
    
    response = requests.post(
        f"{BASE_URL}/chat/",
        json={
            "user_id": 1,
            "question": "안녕하세요, 테스트입니다."
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"답변: {result['answer'][:100]}...")
        print(f"플랫폼: {result['platform_used']}")
        print(f"토큰: {result['total_tokens']}")
        print(f"비용: ${result['estimated_cost_usd']:.6f}")
    else:
        print(f"채팅 실패: {response.status_code} - {response.text}")

def test_user_stats():
    """사용자 통계 조회"""
    print("\n=== 5. 사용자 통계 조회 ===")
    
    response = requests.get(f"{BASE_URL}/users/1/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"총 비용: ${stats['total_cost_usd']:.6f}")
        print(f"총 쿼리: {stats['total_queries']}")
    else:
        print(f"통계 조회 실패: {response.status_code}")

if __name__ == "__main__":
    print("🧪 Multi-Platform RAG System 테스트")
    print("서버가 http://localhost:8000 에서 실행 중이어야 합니다.\n")
    
    try:
        # 서버 연결 확인
        response = requests.get("http://localhost:8000/")
        print(f"✅ 서버 연결 성공: {response.json()}")
        
        # 테스트 실행
        test_create_users()
        test_get_user()
        test_upload_pdf()
        # test_chat()  # PDF 업로드 후 주석 해제
        # test_user_stats()  # 채팅 후 주석 해제
        
        print("\n✅ 테스트 완료!")
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("먼저 서버를 시작하세요: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

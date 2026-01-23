import sys
sys.path.insert(0, 'e:/Folders/Canston/minibuds/src')

from app.core.database import SessionLocal
from app.services.ai.factory import AIServiceFactory
from app.crud import document_crud

# 1. DB 세션
db = SessionLocal()

# 2. 임베딩 생성
platform = "gemini"
embed_service = AIServiceFactory.get_embedding_service(platform)
query = "허경민 덱스컨설팅에서 이력 좀 간략하게 설명해줄래?"
query_vec = embed_service.create_embedding(query)

print(f"Query embedding dimension: {len(query_vec)}")

# 3. 검색 실행
results = document_crud.search_similar_chunks_hybrid(
    db, 
    platform, 
    user_id=1, 
    query_vector=query_vec, 
    query_text=query,
    top_k=10
)

print(f"\nTotal results: {len(results)}")
print("\n=== Search Results ===")
for i, (chunk, score) in enumerate(results, 1):
    print(f"\n{i}. Document ID: {chunk.document_id}")
    print(f"   Score: {score:.6f}")
    print(f"   Content preview: {chunk.content[:100]}...")
    print(f"   Filename: {chunk.document.filename}")

db.close()

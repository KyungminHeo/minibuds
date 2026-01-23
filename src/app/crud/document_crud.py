"""
Document CRUD - 플랫폼별 Chunk 테이블 지원
"""
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from app.models.document import Document, OpenAIChunk, GeminiChunk
from app.schemas.dtos import DocumentCreate

# 문서 관련 DB 동작
def create_document(db: Session, user_id: int, doc_in: DocumentCreate) -> Document:
    """사용자별 문서 생성"""
    db_doc = Document(
        user_id=user_id,
        filename=doc_in.filename, 
        file_path=doc_in.file_path
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

def update_document_embedding_cost(db: Session, document_id: int, tokens: int, cost: float):
    """문서의 임베딩 토큰 수와 비용 업데이트"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if document:
        document.embedding_tokens = tokens
        document.embedding_cost_usd = cost
        db.commit()
        db.refresh(document)

def get_document(db: Session, document_id: int) -> Document:
    """문서 조회"""
    return db.query(Document).filter(Document.id == document_id).first()

def get_user_documents(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Document]:
    """사용자의 문서 목록 조회 (페이지네이션 지원)"""
    return db.query(Document)\
        .filter(Document.user_id == user_id)\
        .order_by(Document.uploaded_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

def delete_document(db: Session, document_id: int, user_id: int) -> bool:
    """
    문서 삭제 (사용자 검증 포함)
    CASCADE로 관련 chunks도 자동 삭제됨
    
    Returns:
        True: 삭제 성공
        False: 문서가 없거나 권한 없음
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == user_id  # 본인 문서만 삭제 가능
    ).first()
    
    if not document:
        return False
    
    db.delete(document)
    db.commit()
    return True

def create_chunks(db: Session, document_id: int, platform: str, chunks_data: List[Dict[str, Any]], batch_size: int = 100):
    """
    플랫폼별 청크 생성 (배치 처리)
    
    대용량 문서의 경우 한 번에 커밋하면 DB 연결이 끊어질 수 있으므로
    batch_size 개씩 나누어 저장합니다.
    
    Args:
        document_id: 문서 ID
        platform: "openai" or "gemini"
        chunks_data: [{"content": "...", "embedding": [...], "page_number": 1}, ...]
        batch_size: 한 번에 저장할 청크 수 (기본값: 50)
    """
    # 플랫폼에 따라 다른 테이블 사용
    if platform.lower() == "openai":
        ChunkModel = OpenAIChunk
    else:
        ChunkModel = GeminiChunk
    
    # 배치 단위로 나누어 처리 (대용량 문서 연결 끊김 방지)
    total_chunks = len(chunks_data)
    for i in range(0, total_chunks, batch_size):
        batch = chunks_data[i:i + batch_size]
        
        db_chunks = [
            ChunkModel(
                document_id=document_id,
                content=data["content"],
                embedding=data["embedding"],
                page_number=data.get("page_number", 1),
                content_tsv=func.to_tsvector('simple', data["content"])  # GIN 인덱스 사용으로 전체 텍스트 가능
            )
            for data in batch
        ]
        db.add_all(db_chunks)
        db.commit()  # 배치마다 커밋하여 연결 유지
        
        # 진행 상황 로깅 (디버깅용)
        print(f"[Chunk] Saved {min(i + batch_size, total_chunks)}/{total_chunks} chunks")

# ========================================
# Hybrid Search Functions (Vector + Full-Text)
# ========================================

def _vector_search(db: Session, ChunkModel, user_id: int, query_vector: List[float], top_k: int) -> List[Tuple[int, float]]:
    """
    벡터 유사도 검색만 수행 (내부 함수)
    
    Returns:
        [(chunk_id, distance), ...]
    """
    distance = ChunkModel.embedding.cosine_distance(query_vector)
    
    stmt = (
        select(ChunkModel.id, distance)
        .join(Document)
        .where(Document.user_id == user_id)
        .order_by(distance)
        .limit(top_k)
    )
    
    results = db.execute(stmt).all()
    return [(row[0], row[1]) for row in results]


def _fulltext_search(db: Session, ChunkModel, user_id: int, query_text: str, top_k: int) -> List[Tuple[int, float]]:
    """
    전문(Full-Text) 검색만 수행 (내부 함수)
    
    Returns:
        [(chunk_id, rank), ...]
    """
    # PostgreSQL의 to_tsquery를 사용하여 검색 쿼리 생성
    # 특수문자를 공백으로 대체 (tsquery 문법 오류 방지 + 단어 분리 유지)
    import re
    sanitized_text = re.sub(r'[()&|!:*\'\"\\]', ' ', query_text)  # 공백으로 대체
    
    # 검색어를 공백 기준으로 나누고 | (OR) 연산자로 결합 (한국어 검색 개선)
    search_tokens = [token for token in sanitized_text.strip().split() if token]
    if not search_tokens:
        return []  # 검색어가 없으면 빈 결과 반환
    
    tsquery = ' | '.join(search_tokens)  # OR 연산: 하나라도 매치되면 결과 반환
    
    # ts_rank를 사용하여 관련도 점수 계산
    rank = func.ts_rank(ChunkModel.content_tsv, func.to_tsquery('simple', tsquery))
    
    stmt = (
        select(ChunkModel.id, rank)
        .join(Document)
        .where(Document.user_id == user_id)
        .where(ChunkModel.content_tsv.op('@@')(func.to_tsquery('simple', tsquery)))
        .order_by(rank.desc())
        .limit(top_k)
    )
    
    results = db.execute(stmt).all()
    return [(row[0], row[1]) for row in results]


def _reciprocal_rank_fusion(
    vector_results: List[Tuple[int, float]],
    fulltext_results: List[Tuple[int, float]],
    k: int = 60,
    vector_weight: float = 0.3,  # Vector Search 가중치: 30%
    fulltext_weight: float = 0.7  # Full-Text Search 가중치: 70% (한국어 키워드 매칭 강화)
) -> List[Tuple[int, float]]:
    """
    Reciprocal Rank Fusion (RRF) 알고리즘으로 검색 결과 병합 (가중치 적용)
    
    RRF 공식: score(d) = vector_weight * (1/(k+rank_v)) + fulltext_weight * (1/(k+rank_f))
    
    Args:
        vector_results: [(chunk_id, distance), ...]
        fulltext_results: [(chunk_id, rank), ...]
        k: RRF 상수 (기본값 60)
        vector_weight: Vector Search 가중치 (기본값 0.3)
        fulltext_weight: Full-Text Search 가중치 (기본값 0.7)
    
    Returns:
        [(chunk_id, rrf_score), ...] (점수 내림차순 정렬)
    """
    rrf_scores: Dict[int, float] = {}
    
    # Vector Search 결과 처리 (가중치 30%)
    for rank, (chunk_id, _) in enumerate(vector_results, start=1):
        score = vector_weight * (1.0 / (k + rank))
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score
    
    # Full-Text Search 결과 처리 (가중치 70% - 한국어 키워드 매칭 강화)
    for rank, (chunk_id, _) in enumerate(fulltext_results, start=1):
        score = fulltext_weight * (1.0 / (k + rank))
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score
    
    # 점수순으로 정렬하여 반환
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


def search_similar_chunks_hybrid(
    db: Session, 
    platform: str, 
    user_id: int, 
    query_vector: List[float], 
    query_text: str,
    top_k: int = 10,
    search_multiplier: int = 3  # 내부적으로 top_k * multiplier 만큼 검색
) -> List[Tuple[Any, float]]:
    """
    하이브리드 검색: Vector Search + Full-Text Search + RRF
    
    Args:
        platform: "openai" or "gemini"
        user_id: 검색할 사용자 ID
        query_vector: 질문 임베딩 벡터
        query_text: 검색 키워드 (원본 질문 텍스트)
        top_k: 최종 반환할 개수
        search_multiplier: 1차 검색 배수 (top_k * multiplier 만큼 검색)
        
    Returns:
        List of tuples: [(chunk, rrf_score), ...]
    """
    # 플랫폼에 따라 모델 선택
    if platform.lower() == "openai":
        ChunkModel = OpenAIChunk
    else:
        ChunkModel = GeminiChunk
    
    # 1차 검색: 넉넉하게 가져오기 (top_k의 3배)
    initial_top_k = top_k * search_multiplier
    
    # Vector Search 수행
    vector_results = _vector_search(db, ChunkModel, user_id, query_vector, initial_top_k)
    
    # Full-Text Search 수행
    try:
        fulltext_results = _fulltext_search(db, ChunkModel, user_id, query_text, initial_top_k)
    except Exception as e:
        # Full-Text Search 실패 시 트랜잭션 롤백 후 Vector Search 결과만 사용
        db.rollback()  # 트랜잭션 롤백 - InFailedSqlTransaction 방지
        print(f"Full-text search failed: {e}, falling back to vector-only search")
        fulltext_results = []
    
    # RRF로 결과 병합
    rrf_results = _reciprocal_rank_fusion(vector_results, fulltext_results)
    
    # 상위 top_k개의 chunk_id 추출
    top_chunk_ids = [chunk_id for chunk_id, _ in rrf_results[:top_k]]
    
    if not top_chunk_ids:
        return []
    
    # chunk_id로 실제 Chunk 객체 재조회 (순서 유지)
    stmt = (
        select(ChunkModel)
        .join(Document)
        .where(ChunkModel.id.in_(top_chunk_ids))
        .where(Document.user_id == user_id)
    )
    
    chunks = db.execute(stmt).scalars().all()
    
    # 원래 순서대로 정렬 (RRF 점수 순)
    chunk_dict = {chunk.id: chunk for chunk in chunks}
    rrf_score_dict = {chunk_id: score for chunk_id, score in rrf_results}
    
    ordered_results = [
        (chunk_dict[chunk_id], rrf_score_dict[chunk_id]) 
        for chunk_id in top_chunk_ids 
        if chunk_id in chunk_dict
    ]
    
    return ordered_results

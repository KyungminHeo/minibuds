import os
import logging
import asyncio

logger = logging.getLogger(__name__)
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.schemas.dtos import DocumentCreate, DocumentResponse
from app.services import file_service, chunk_service
from app.services.ai.factory import AIServiceFactory
from app.services.ai.cost import CostCalculator
from app.services.ai.utils import num_tokens_from_string
from app.crud import document_crud, user_crud

# ThreadPool for non-blocking DB operations
# 업로드 중에도 다른 API 요청이 처리될 수 있도록 함
db_executor = ThreadPoolExecutor(max_workers=4)

router = APIRouter(tags=["Upload"])

@contextmanager
def upload_transaction(db: Session, file_path: str):
    """업로드 트랜잭션 - 실패 시 파일 삭제 + DB 롤백"""
    try:
        yield
        db.commit()
    except Exception as e:
        db.rollback()
        # 실패 시 물리적 파일도 삭제
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e

@router.post("/upload/", response_model=DocumentResponse)
async def upload_pdf(
    user_id: int,  # 사용자 ID (쿼리 파라미터)
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """PDF 업로드 및 임베딩 생성 (사용자의 플랫폼 기반)"""
    
    loop = asyncio.get_event_loop()
    
    # 1. 사용자 확인 및 플랫폼 조회 (run_in_executor로 비블로킹)
    user = await loop.run_in_executor(db_executor, lambda: user_crud.get_user(db, user_id))
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    
    platform = user.platform
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "PDF 파일만 가능합니다.")

    # 2. 파일 크기 검증
    file_service.validate_file_size(file)

    # 3. 파일 저장 (run_in_executor로 비블로킹)
    saved_path = await loop.run_in_executor(db_executor, lambda: file_service.save_file_locally(file))

    with upload_transaction(db, saved_path):
        file_service.validate_pdf(saved_path, file.filename) # 검증 추가
    
    try:
        # 3. 텍스트 추출 (run_in_executor로 비블로킹 - PDF 파싱은 오래 걸림!)
        pages_content = await loop.run_in_executor(
            db_executor, 
            lambda: list(file_service.extract_text_with_pages(saved_path))  # 제너레이터 -> 리스트 변환
        )
        if not pages_content:
            raise ValueError("텍스트 추출 실패")

        # 4. 문서 정보 DB 저장 (run_in_executor로 비블로킹)
        doc_schema = DocumentCreate(filename=file.filename, file_path=saved_path)
        created_doc = await loop.run_in_executor(
            db_executor,
            lambda: document_crud.create_document(db, user_id, doc_schema)
        )

        # 5. 청킹 (run_in_executor로 비블로킹 - 문장 경계 인식 청킹)
        chunks_data = await loop.run_in_executor(
            db_executor,
            lambda: list(chunk_service.chunk_text_with_metadata(pages_content))  # 제너레이터 -> 리스트 변환
        )

        # 6. 플랫폼별 임베딩 서비스 선택
        embed_service = AIServiceFactory.get_embedding_service(platform)
        
        # 텍스트 리스트만 추출
        texts_to_embed = [item['text'] for item in chunks_data]
        
        # 7. 토큰 수 계산 (임베딩 생성 전)
        total_tokens = sum(num_tokens_from_string(text) for text in texts_to_embed)
        
        # 8. 임베딩 요청 (run_in_executor로 비블로킹 - 가장 오래 걸리는 작업!)
        embeddings = await loop.run_in_executor(
            db_executor,
            lambda: embed_service._create_embeddings_batch_sync(texts_to_embed)
        )
        
        # 9. 임베딩 비용 계산
        embedding_cost = CostCalculator.calculate_embedding_cost(platform, total_tokens)
        
        # 10. 데이터 조립
        db_chunks_inputs = []
        for i, item in enumerate(chunks_data):
            db_chunks_inputs.append({
                "content": item['text'],
                "embedding": embeddings[i], # 순서대로 매핑
                "page_number": item['page']
            })
        
        # 11. 데이터 저장 (새 세션 사용 - 세션 타임아웃 방지)
        # 임베딩 생성 시간이 길어서 기존 db 세션이 끊길 수 있음 -> 새 세션 생성하여 저장
        # 반환값: 새 세션에서 조회한 Document 객체 (끊어진 세션 회피)
        def save_results_with_new_session(doc_id: int, plat: str, chunks: list, tokens: int, cost: float):
            with SessionLocal() as new_db:
                try:
                    # 1. 청크 저장
                    document_crud.create_chunks(new_db, doc_id, plat, chunks)
                    # 2. 비용 업데이트
                    document_crud.update_document_embedding_cost(new_db, doc_id, tokens, cost)
                    # 3. 커밋 확인
                    new_db.commit()
                    # 4. 새 세션에서 문서 다시 조회 (세션 바인딩 문제 해결)
                    updated_doc = document_crud.get_document(new_db, doc_id)
                    
                    # 세션 밖에서도 접근 가능하도록 속성을 명시적으로 로드
                    if updated_doc:
                        # lazy loading 방지를 위해 필요한 속성 미리 접근
                        _ = updated_doc.id
                        _ = updated_doc.filename
                        _ = updated_doc.uploaded_at
                        _ = updated_doc.embedding_tokens
                        _ = updated_doc.embedding_cost_usd
                        new_db.expunge(updated_doc)  # 세션에서 분리하여 독립적으로 만듦
                    return updated_doc
                except Exception as e:
                    new_db.rollback()
                    raise e

        final_doc = await loop.run_in_executor(
            db_executor,
            lambda: save_results_with_new_session(created_doc.id, platform, db_chunks_inputs, total_tokens, embedding_cost)
        )

        return final_doc

    except Exception as e:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(500, detail=str(e))

@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """문서 삭제 (임베딩 및 물리적 파일 포함)"""
    
    # 1. 사용자 확인
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    
    # 2. 문서 조회 (삭제 전에 파일 경로 저장)
    document = document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(404, "문서를 찾을 수 없습니다.")
    
    # 3. 권한 확인
    if document.user_id != user_id:
        raise HTTPException(403, "해당 문서를 삭제할 권한이 없습니다.")
    
    file_path = document.file_path
    
    # 4. DB에서 문서 삭제 (CASCADE로 chunks 자동 삭제)
    success = document_crud.delete_document(db, document_id, user_id)
    
    if not success:
        raise HTTPException(500, "문서 삭제에 실패했습니다.")
    
    # 5. 물리적 파일 삭제
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # 파일 삭제 실패해도 DB는 이미 삭제됨 (로그만 남김)
        logger.warning(f"Failed to delete physical file {file_path}: {e}")
    
    return {
        "message": "문서가 성공적으로 삭제되었습니다.",
        "document_id": document_id,
        "filename": document.filename
    }

"""
Document 관리 API - 문서 조회 및 삭제
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.dtos import DocumentResponse
from app.crud import document_crud

router = APIRouter(tags=["Documents"])

@router.get("/users/{user_id}/documents", response_model=List[DocumentResponse])
def list_user_documents(
    user_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """사용자의 문서 목록 조회 (페이지네이션 지원)"""
    documents = document_crud.get_user_documents(db, user_id, skip, limit)
    return documents

@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """단일 문서 조회"""
    document = document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(404, "문서를 찾을 수 없습니다.")
    return document
"""
User 관리 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.dtos import UserCreate, UserResponse, UserStats
from app.crud import user_crud, history_crud

router = APIRouter(tags=["Users"])

@router.post("/users/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """새 사용자 생성"""
    # 이메일 중복 체크
    existing_user = user_crud.get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(400, "이미 존재하는 이메일입니다.")
    
    # 사용자명 중복 체크
    existing_username = user_crud.get_user_by_username(db, user_in.username)
    if existing_username:
        raise HTTPException(400, "이미 존재하는 사용자명입니다.")
    
    # 플랫폼 유효성 검사
    if user_in.platform.lower() not in ["openai", "gemini"]:
        raise HTTPException(400, "지원하지 않는 플랫폼입니다. (openai 또는 gemini)")
    
    # 플랫폼을 소문자로 정규화하여 저장
    normalized_user = UserCreate(
        username=user_in.username,
        email=user_in.email,
        platform=user_in.platform.lower()
    )
    
    return user_crud.create_user(db, normalized_user)

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """사용자 정보 조회"""
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    return user

@router.get("/users/{user_id}/stats", response_model=UserStats)
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    """사용자 사용 통계 (비용, 쿼리 수)"""
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    
    total_cost = history_crud.get_user_total_cost(db, user_id)
    total_queries = history_crud.get_user_total_query_count(db, user_id)
    
    return UserStats(
        user_id=user_id,
        total_cost_usd=total_cost,
        total_queries=total_queries
    )

@router.patch("/users/{user_id}/platform")
def update_user_platform(user_id: int, new_platform: str, db: Session = Depends(get_db)):
    """사용자 플랫폼 변경"""
    if new_platform.lower() not in ["openai", "gemini"]:
        raise HTTPException(400, "지원하지 않는 플랫폼입니다. (openai 또는 gemini)")
    
    try:
        updated_user = user_crud.update_user_platform(db, user_id, new_platform.lower())
        return {"message": f"플랫폼이 {updated_user.platform}으로 변경되었습니다."}
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.get("/users/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """사용자 목록 조회"""
    return user_crud.list_users(db, skip, limit)

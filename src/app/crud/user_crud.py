"""
User CRUD - 사용자 생성, 조회, 플랫폼 변경
"""
from sqlalchemy.orm import Session
from app.models.user import User, PlatformEnum
from app.schemas.dtos import UserCreate

def create_user(db: Session, user_in: UserCreate) -> User:
    """새 사용자 생성"""
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        platform=user_in.platform
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int) -> User | None:
    """사용자 조회"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> User | None:
    """이메일로 사용자 조회"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> User | None:
    """사용자명으로 조회"""
    return db.query(User).filter(User.username == username).first()

def update_user_platform(db: Session, user_id: int, platform: str) -> User:
    """사용자의 플랫폼 변경 (향후 마이그레이션 기능과 연계 가능)"""
    user = get_user(db, user_id)
    if not user:
        raise ValueError(f"User not found: {user_id}")
    
    user.platform = platform
    db.commit()
    db.refresh(user)
    return user

def list_users(db: Session, skip: int = 0, limit: int = 100):
    """사용자 목록 조회"""
    return db.query(User).offset(skip).limit(limit).all()

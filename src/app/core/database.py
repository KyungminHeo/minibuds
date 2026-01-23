from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# DB 세션 관리
engine = create_engine(
    settings.DATABASE_URL,
    # 1. 연결이 살아있는지 먼저 체크 (이게 끊김 에러를 막아줍니다)
    pool_pre_ping=True,
    # 2. 5분(300초)마다 연결을 재설정해서 유령 연결 방지
    pool_recycle=300,
    # 3. 동시 연결 풀 설정 (대용량 처리 시 안정성 향상)
    pool_size=5,           # 기본 유지 연결 수
    max_overflow=10,       # 최대 추가 연결 (총 15개까지)
    pool_timeout=60,       # 연결 대기 시간 60초 (기본 30초)
    # 4. Supabase Pooler 사용 시 필수 (Prepared Statement 비활성화)
    connect_args={"prepare_threshold": None}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        # 세션이 이미 끊어진 경우에도 안전하게 종료
        try:
            db.close()
        except Exception:
            # 연결이 끊어진 세션은 그냥 무시
            pass
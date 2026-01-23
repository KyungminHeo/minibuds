from pydantic_settings import BaseSettings

# 환경변수 로드 (설정 및 DB 연결)
class Settings(BaseSettings):
    OPENAI_API_KEY: str
    GOOGLE_API_KEY: str
    DATABASE_URL: str
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100

    class Config:
        env_file = ".env.development"
        env_file_encoding = "utf-8"

settings = Settings()
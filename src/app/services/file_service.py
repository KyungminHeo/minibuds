import os
import shutil
import pdfplumber
from typing import Generator
from fastapi import UploadFile
from app.core.exceptions import DocumentValidationError, EmptyDocumentError

# PDF 텍스트 추출
FILE_DIR = "files"
os.makedirs(FILE_DIR, exist_ok=True)

def save_file_locally(file: UploadFile) -> str:
    file_path = os.path.join(FILE_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path

def extract_text_with_pages(file_path: str) -> Generator[dict, None, None]:
    """PDF -> yield {'page': 1, 'text': '...'} 형식으로 페이지별 텍스트 반환 (제너레이터)"""
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                yield {"page": i + 1, "text": text}
                
def validate_pdf(file_path: str, filename: str) -> bool:
    """PDF 파일 유효성 검증"""
    try:
        with pdfplumber.open(file_path) as pdf:
            # 1. 페이지 수 확인
            if len(pdf.pages) == 0:
                return DocumentValidationError("PDF에 페이지가 없습니다.")
            
            # 2. 텍스트 추출 가능 여부 확인
            has_text = False
            for page in pdf.pages[:4]: # 처음 4페이지만 확인 (성능)
                if page.extract_text():
                    has_text = True
                    break
                
            if not has_text:
                raise EmptyDocumentError(filename)
            
            return True
    except pdfplumber.PDFSyntaxError:
        raise DocumentValidationError("손상된 PDF 파일입니다.")
    except Exception as e:
        raise DocumentValidationError(f"PDF 검증 실패: {str(e)}")
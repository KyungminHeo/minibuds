from fastapi import HTTPException

class DocumentValidationError(HTTPException):
    """문서 검증 실패"""
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)
        

class EmbeddingGenerationError(HTTPException):
    """임베딩 생성 실패"""
    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)
        
        
class EmptyDocumentError(HTTPException):
    """텍스트 추출 불가 (이미지 PDF 등)"""
    def __init__(self, filename: str):
        super().__init__(
            status_code=422, 
            detail=f"'{filename}'에서 텍스트를 추출할 수 없습니다. 이미지 전용 PDF일 수 있습니다."
        )
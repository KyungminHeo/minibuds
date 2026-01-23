"""
청킹 서비스 - 문장 경계 인식 청킹

왜 문장 단위로 분할하는가?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
임베딩 모델은 **의미 단위**로 텍스트를 이해합니다.
문장이 중간에 잘리면 의미가 왜곡되어 검색 품질이 저하됩니다.

[문제 예시 - 고정 길이 분할]
원본: "허경민은 덱스컨설팅에서 5년간 근무했습니다."
청크1: "허경민은 덱스컨설팅에서 5"  ← 의미 불완전
청크2: "년간 근무했습니다"           ← 주어 없음

[해결 - 문장 경계 분할]
청크: "허경민은 덱스컨설팅에서 5년간 근무했습니다."  ← 완전한 문장
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from typing import Generator, Tuple, List
from app.core.config import settings


# ============================================================
# 문장 종결 패턴 정의
# ============================================================
# 한국어와 영어 문장 종결 패턴
# 한국어는 "다.", "요.", "죠." 등으로 끝나는 경우가 많음
SENTENCE_ENDINGS = [
    # 한국어 종결 패턴 (길이가 긴 것부터 매칭해야 정확)
    "습니다.", "였습니다.", "됩니다.", "합니다.",
    "세요.", "네요.", "군요.", "죠.",
    "다.", "요.", "음.",
    # 영어/공통 종결 패턴
    ".", "!", "?",
]


def find_page_number(char_index: int, page_boundaries: List[Tuple[int, int]]) -> int:
    """
    글자 인덱스로 해당 위치의 페이지 번호를 찾습니다.
    
    [동작 원리]
    page_boundaries = [(0, 1), (150, 2), (320, 3)]
    → 인덱스 0~149: 페이지 1
    → 인덱스 150~319: 페이지 2
    → 인덱스 320~: 페이지 3
    
    Args:
        char_index: 전체 텍스트에서의 글자 위치 (0부터 시작)
        page_boundaries: [(시작_인덱스, 페이지_번호), ...] 리스트
        
    Returns:
        해당 위치의 페이지 번호
    """
    # 역순으로 탐색 (마지막 페이지부터)
    # 이유: char_index보다 작거나 같은 첫 번째 경계를 찾기 위함
    for i in range(len(page_boundaries) - 1, -1, -1):
        start_idx, page_num = page_boundaries[i]
        if char_index >= start_idx:
            return page_num
    
    # 기본값: 첫 페이지
    return 1


def find_sentence_end(text: str, start: int, max_end: int) -> int:
    """
    주어진 범위 내에서 가장 마지막 문장 종결 위치를 찾습니다.
    
    [동작 원리]
    text[start:max_end] 범위에서 SENTENCE_ENDINGS를 뒤에서부터 찾음
    → 문장이 완전하게 끝나는 위치 반환
    
    Args:
        text: 전체 텍스트
        start: 검색 시작 위치
        max_end: 검색 종료 위치 (최대 청크 길이)
        
    Returns:
        문장 종결 위치 (찾지 못하면 max_end 반환)
    """
    search_text = text[start:max_end]
    best_pos = -1
    
    # 모든 종결 패턴에서 가장 뒤에 있는 것 찾기
    for ending in SENTENCE_ENDINGS:
        # rfind: 뒤에서부터 찾음 (마지막 등장 위치)
        pos = search_text.rfind(ending)
        if pos != -1:
            # 실제 종결 위치 = 찾은 위치 + 종결어 길이
            actual_end = pos + len(ending)
            if actual_end > best_pos:
                best_pos = actual_end
    
    if best_pos != -1:
        return start + best_pos  # 절대 위치로 변환
    
    # 문장 끝을 찾지 못한 경우: 최대 길이 사용
    return max_end


def chunk_text_with_metadata(pages: list[dict]) -> Generator[dict, None, None]:
    """
    PDF 페이지들을 문장 경계 기준으로 청킹합니다.
    
    [핵심 로직]
    1. 모든 페이지 텍스트를 하나로 합침 (페이지 경계 정보 보존)
    2. 문장 끝(., !, ?, 다., 요. 등)에서 분할
    3. 오버랩 적용으로 문맥 유지
    4. 각 청크가 어느 페이지에서 왔는지 추적
    
    [기존 코드 vs 새 코드]
    기존: 페이지별 독립 청킹 → 페이지 경계에서 문장 끊김
    새코드: 전체 통합 후 문장 단위 청킹 → 문맥 유지
    
    Args:
        pages: [{'page': 1, 'text': '...'}, ...] 형식의 페이지 리스트
        
    Yields:
        {'text': '청크 내용', 'page': 페이지_번호} 형식의 딕셔너리
    """
    chunk_size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP
    
    # ========================================
    # STEP 1: 전체 텍스트 합치기 + 페이지 경계 기록
    # ========================================
    # 왜 합치는가?
    # → 페이지 1 끝: "Python, FastAPI 기반 시스템을 개발"
    # → 페이지 2 시작: "했습니다."
    # → 합치면: "Python, FastAPI 기반 시스템을 개발했습니다." (완전한 문장!)
    
    all_text = ""
    page_boundaries: List[Tuple[int, int]] = []  # (시작_인덱스, 페이지_번호)
    
    for page_data in pages:
        # 현재 텍스트 길이 = 이 페이지의 시작 인덱스
        page_boundaries.append((len(all_text), page_data['page']))
        # 페이지 텍스트 추가 (공백으로 구분)
        all_text += page_data['text'] + " "
    
    text_length = len(all_text)
    
    # 빈 문서 처리
    if text_length == 0:
        return
    
    # ========================================
    # STEP 2: 문장 경계 인식 청킹
    # ========================================
    start = 0
    
    while start < text_length:
        # 2-1. 최대 청크 길이 계산
        max_end = min(start + chunk_size, text_length)
        
        # 2-2. 문장 끝 위치 찾기
        # → 청크가 문장 중간에서 끊기지 않도록!
        if max_end < text_length:
            # 아직 텍스트가 남아있으면 문장 끝 탐색
            end = find_sentence_end(all_text, start, max_end)
        else:
            # 마지막 청크는 그대로 사용
            end = max_end
        
        # 2-3. 청크 추출
        chunk_text = all_text[start:end].strip()
        
        # 2-4. 페이지 번호 찾기 (청크 시작 위치 기준)
        page_num = find_page_number(start, page_boundaries)
        
        # 2-5. 유효한 청크만 yield
        if chunk_text:
            yield {"text": chunk_text, "page": page_num}
        
        # ========================================
        # STEP 3: 다음 청크 시작 위치 계산 (오버랩 적용)
        # ========================================
        # 왜 오버랩?
        # → 청크 경계에서 중요한 정보가 잘리는 것 방지
        # → 예: 오버랩 50이면 마지막 50글자가 다음 청크에도 포함
        
        # 다음 시작 = 현재 끝 - 오버랩
        next_start = end - overlap
        
        # 무한 루프 방지: 최소한 1글자는 전진
        if next_start <= start:
            next_start = start + 1
        
        start = next_start

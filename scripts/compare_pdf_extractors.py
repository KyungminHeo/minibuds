"""
PDF 텍스트 추출 라이브러리 비교 스크립트
pypdf vs pdfplumber
"""
import sys
sys.path.insert(0, 'e:/Folders/Canston/minibuds/src')

from pypdf import PdfReader

# pdfplumber 설치 확인
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("⚠️ pdfplumber가 설치되어 있지 않습니다. pip install pdfplumber 로 설치해주세요.")

def extract_with_pypdf(file_path: str) -> list[dict]:
    """pypdf로 텍스트 추출 (현재 방식)"""
    reader = PdfReader(file_path)
    results = []
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            results.append({"page": i + 1, "text": text})
    
    return results

def extract_with_pdfplumber(file_path: str) -> list[dict]:
    """pdfplumber로 텍스트 추출"""
    if not PDFPLUMBER_AVAILABLE:
        return []
    
    results = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            tables = page.extract_tables()
            
            result = {
                "page": i + 1, 
                "text": text if text else "",
                "tables": tables if tables else []
            }
            results.append(result)
    
    return results

def compare_extraction(file_path: str):
    """두 라이브러리 비교"""
    print(f"\n{'='*60}")
    print(f"📄 파일: {file_path}")
    print(f"{'='*60}")
    
    # pypdf 추출
    print("\n🔹 pypdf 추출 결과:")
    print("-" * 40)
    pypdf_results = extract_with_pypdf(file_path)
    for result in pypdf_results[:2]:  # 처음 2페이지만 출력
        print(f"\n[페이지 {result['page']}]")
        text_preview = result['text'][:500] if result['text'] else "(텍스트 없음)"
        print(text_preview)
        if len(result['text']) > 500:
            print(f"... (총 {len(result['text'])} 글자)")
    
    # pdfplumber 추출
    if PDFPLUMBER_AVAILABLE:
        print("\n\n🔹 pdfplumber 추출 결과:")
        print("-" * 40)
        plumber_results = extract_with_pdfplumber(file_path)
        for result in plumber_results[:2]:  # 처음 2페이지만 출력
            print(f"\n[페이지 {result['page']}]")
            text_preview = result['text'][:500] if result['text'] else "(텍스트 없음)"
            print(text_preview)
            if result['text'] and len(result['text']) > 500:
                print(f"... (총 {len(result['text'])} 글자)")
            
            # 표 정보 출력
            if result['tables']:
                print(f"\n📊 발견된 표: {len(result['tables'])}개")
                for j, table in enumerate(result['tables'][:2]):  # 처음 2개 표만
                    print(f"  표 {j+1}: {len(table)}행 x {len(table[0]) if table else 0}열")
                    # 표 내용 미리보기
                    for row in table[:3]:  # 처음 3행만
                        print(f"    {row}")
    
    # 비교 요약
    print(f"\n\n📋 비교 요약:")
    print("-" * 40)
    pypdf_total = sum(len(r['text']) for r in pypdf_results)
    print(f"pypdf 총 추출 글자수: {pypdf_total:,}")
    
    if PDFPLUMBER_AVAILABLE:
        plumber_total = sum(len(r['text']) for r in plumber_results)
        plumber_tables = sum(len(r['tables']) for r in plumber_results)
        print(f"pdfplumber 총 추출 글자수: {plumber_total:,}")
        print(f"pdfplumber 발견 표 개수: {plumber_tables}")
        
        diff = plumber_total - pypdf_total
        if diff > 0:
            print(f"✅ pdfplumber가 {diff:,}글자 더 많이 추출")
        elif diff < 0:
            print(f"⚠️ pypdf가 {abs(diff):,}글자 더 많이 추출")
        else:
            print("📌 추출 글자수 동일")

if __name__ == "__main__":
    # 테스트할 PDF 파일들
    test_files = [
        "e:/Folders/Canston/minibuds/src/files/허경민 이력서.pdf",
        "e:/Folders/Canston/minibuds/src/files/사회복지정책론_기말[3].pdf",
    ]
    
    for file_path in test_files:
        try:
            compare_extraction(file_path)
        except Exception as e:
            print(f"❌ {file_path} 처리 오류: {e}")

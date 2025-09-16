#!/usr/bin/env python3
"""
CKA PDF 질문답변 및 이미지 추출기 - 메인 실행 파일

사용법:
    python main.py [PDF파일경로] [옵션]
    
예시:
    python main.py "CKA V13.95.pdf"
    python main.py "CKA V13.95.pdf" --sequential
    python main.py "CKA V13.95.pdf" --simple
    python main.py --help
"""

import sys
import os
import argparse
from typing import Optional

# 로컬 모듈 임포트
try:
    from models import QuestionAnswer, ExtractionStats
    from extractor import extract_cka_data, PDFExtractionError
    from utils import (
        validate_pdf_path, print_dependency_status, 
        save_questions_only, save_answers_only, save_combined_qa, 
        save_as_json, save_as_csv, get_file_info
    )
    # 순차적 추출기는 선택적 임포트
    try:
        from sequential_extractor import extract_cka_data_sequential
        HAS_SEQUENTIAL = True
    except ImportError:
        HAS_SEQUENTIAL = False
        
except ImportError as e:
    print(f"모듈 임포트 오류: {e}")
    print("필요한 파일들이 같은 디렉토리에 있는지 확인해주세요.")
    sys.exit(1)

def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description="CKA PDF에서 질문답변과 이미지를 추출합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py "CKA V13.95.pdf"              # 개선된 추출 (기본값)
  python main.py input.pdf --sequential        # 순차적 추출 (base64)
  python main.py input.pdf --simple            # 간단한 추출 (기존 방식)
  python main.py --check-deps                  # 의존성 확인만
  
출력 파일:
  - cka_questions_only.txt     : 질문만 모음
  - cka_answers_only.txt       : 답변만 모음  
  - cka_questions_answers.txt  : 질문과 답변 결합
  - cka_qa_data.json          : JSON 형태 데이터
  - cka_qa_data.csv           : CSV 형태 데이터
  - extracted_images/         : 추출된 이미지 파일들 (파일명 방식)
        """
    )
    
    parser.add_argument(
        "pdf_path", 
        nargs="?",
        help="PDF 파일 경로"
    )
    
    parser.add_argument(
        "--sequential", 
        action="store_true",
        help="순차적 추출 사용 (텍스트-이미지 순서 보존, base64 인코딩)"
    )
    
    parser.add_argument(
        "--enhanced", 
        action="store_true",
        help="개선된 추출 사용 (Question/Answer 이미지 분리)"
    )
    
    parser.add_argument(
        "--simple", 
        action="store_true",
        help="간단한 추출 사용 (기존 방식)"
    )
    
    parser.add_argument(
        "--output-dir", 
        default=".",
        help="출력 디렉토리 (기본값: 현재 디렉토리)"
    )
    
    parser.add_argument(
        "--check-deps", 
        action="store_true",
        help="의존성 라이브러리 확인만 수행"
    )
    
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="최소한의 출력만 표시"
    )
    
    parser.add_argument(
        "--no-csv", 
        action="store_true",
        help="CSV 파일 생성 안함"
    )
    
    return parser.parse_args()

def check_pdf_file(pdf_path: str) -> bool:
    """PDF 파일 존재 및 유효성 확인"""
    try:
        validate_pdf_path(pdf_path)
        return True
    except (ValueError, FileNotFoundError) as e:
        print(f"오류: {e}")
        return False

def get_pdf_path_interactive() -> Optional[str]:
    """대화형으로 PDF 파일 경로 입력받기"""
    while True:
        pdf_path = input("PDF 파일 경로를 입력하세요 (또는 'q'로 종료): ").strip()
        
        if pdf_path.lower() == 'q':
            return None
        
        if not pdf_path:
            print("파일 경로를 입력해주세요.")
            continue
        
        # 따옴표 제거
        pdf_path = pdf_path.strip('"\'')
        
        if check_pdf_file(pdf_path):
            return pdf_path
        
        print("다시 입력해주세요.\n")

def display_file_info(pdf_path: str):
    """PDF 파일 정보 표시"""
    info = get_file_info(pdf_path)
    if info.get('exists'):
        print(f"파일 크기: {info['size_formatted']}")

def save_all_outputs(qa_pairs, extraction_method, args):
    """모든 출력 파일 저장"""
    output_dir = args.output_dir
    
    # 출력 디렉토리 생성
    if output_dir != "." and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 파일 경로 설정
    def get_output_path(filename):
        return os.path.join(output_dir, filename)
    
    try:
        if not args.quiet:
            print("파일 저장 중...")
        
        # 텍스트 파일들
        save_questions_only(qa_pairs, get_output_path("cka_questions_only.txt"))
        save_answers_only(qa_pairs, get_output_path("cka_answers_only.txt"))
        save_combined_qa(qa_pairs, get_output_path("cka_questions_answers.txt"))
        
        # JSON 파일 (웹페이지용)
        basic_data = []
        for qa in qa_pairs:
            # Sequential 방식에서는 images가 dict 객체들의 리스트일 수 있음
            images_data = qa.images
            if images_data and isinstance(images_data[0], dict):
                # Sequential 방식: 이미 올바른 형태
                pass
            elif images_data and isinstance(images_data[0], str):
                # 기존 파일 방식: 파일명만 있는 경우 (현재는 지원하지 않음)
                images_data = []
            
            qa_dict = {
                'question_no': qa.question_no,
                'question': qa.question,
                'answer': qa.answer,
                'has_images': qa.has_images,
                'images': images_data or []
            }
            basic_data.append(qa_dict)
            
        save_as_json(basic_data, get_output_path("cka_qa_data.json"))
        
        # CSV 파일 (순차적 방식은 복잡한 이미지 데이터로 인해 스킵)
        if not args.no_csv and extraction_method != 'sequential':
            save_as_csv(qa_pairs, get_output_path("cka_qa_data.csv"))
        elif extraction_method == 'sequential' and not args.quiet:
            print("순차적 방식은 CSV 생성을 건너뜁니다 (base64 이미지 데이터 포함)")
        
        return True
        
    except Exception as e:
        print(f"파일 저장 중 오류: {e}")
        return False

def display_results(qa_pairs, stats, extraction_method, args):
    """결과 표시"""
    if args.quiet:
        print(f"완료: {stats.total_questions}개 문제, {stats.total_images}개 이미지")
        return
    
    # 통계 정보
    print(stats)
    
    # 추출 방식별 안내
    if extraction_method == 'sequential':
        print("\n=== 순차적 추출 방식 결과 ===")
        print("- 이미지가 JSON에 base64로 포함됨")
        print("- 별도 이미지 폴더 불필요")
        print("- 텍스트와 이미지 순서 보존")
    else:
        print(f"\n=== {'개선된' if extraction_method == 'enhanced' else '기본'} 추출 방식 결과 ===")
        print("- 이미지가 별도 파일로 저장됨")
        print("- extracted_images/ 폴더와 함께 사용")
    
    # 파일 목록
    print("\n=== 생성된 파일 ===")
    files = [
        "cka_questions_only.txt - 질문만 모음",
        "cka_answers_only.txt - 답변만 모음",
        "cka_questions_answers.txt - 질문과 답변 결합",
        "cka_qa_data.json - JSON 형태 데이터 (웹페이지용)"
    ]
    
    if extraction_method != 'sequential':
        files.append("extracted_images/ - 추출된 이미지 파일들")
        if not args.no_csv:
            files.append("cka_qa_data.csv - CSV 형태 데이터")
    
    for file_desc in files:
        print(f"  {file_desc}")
    
    # 이미지가 포함된 문제들
    image_questions = [qa for qa in qa_pairs if qa.has_images]
    if image_questions:
        print(f"\n=== 이미지가 포함된 문제 목록 ===")
        for qa in image_questions[:10]:  # 최대 10개만 표시
            if extraction_method == 'sequential':
                q_count = len([img for img in qa.images if img.get('type') == 'question'])
                a_count = len([img for img in qa.images if img.get('type') == 'answer'])
                print(f"문제 {qa.question_no}: Question {q_count}개, Answer {a_count}개 이미지")
            else:
                print(f"문제 {qa.question_no}: {len(qa.images)}개 이미지")
        
        if len(image_questions) > 10:
            print(f"... 외 {len(image_questions) - 10}개 문제")
    
    # 웹페이지 안내
    print(f"\n=== 사용 안내 ===")
    print("1. 웹페이지에서 cka_qa_data.json 파일을 업로드하세요")
    if extraction_method == 'sequential':
        print("2. 이미지가 JSON에 포함되어 있어 바로 사용 가능합니다")
    else:
        print("2. extracted_images 폴더도 함께 업로드하세요")
    print("3. Question과 Answer 영역에 따라 이미지가 분리되어 표시됩니다")

def main():
    """메인 함수"""
    args = parse_arguments()
    
    # 의존성 확인만 수행
    if args.check_deps:
        print_dependency_status()
        return
    
    print("CKA PDF 질문답변 및 이미지 추출기")
    print("=" * 50)
    
    # 의존성 확인
    if not print_dependency_status():
        print("필수 라이브러리를 설치한 후 다시 실행해주세요.")
        return
    
    # PDF 파일 경로 확정
    pdf_path = args.pdf_path
    
    if not pdf_path:
        # 명령행에서 파일이 제공되지 않은 경우
        default_files = ["CKA V13.95.pdf", "cka.pdf", "CKA.pdf"]
        
        # 기본 파일명들 확인
        for default_file in default_files:
            if os.path.exists(default_file):
                pdf_path = default_file
                print(f"기본 파일 사용: {pdf_path}")
                break
        
        if not pdf_path:
            pdf_path = get_pdf_path_interactive()
            if not pdf_path:
                print("프로그램을 종료합니다.")
                return
    
    # PDF 파일 확인
    if not check_pdf_file(pdf_path):
        return
    
    if not args.quiet:
        print(f"\nPDF 파일: {pdf_path}")
        display_file_info(pdf_path)
        print()
    
    try:
        # 추출 방식 결정
        if args.sequential:
            if not HAS_SEQUENTIAL:
                print("오류: sequential_extractor.py 파일이 없습니다.")
                print("순차적 추출을 사용하려면 sequential_extractor.py가 필요합니다.")
                return
            extraction_method = 'sequential'
        elif args.simple:
            extraction_method = 'simple'
        elif args.enhanced:
            extraction_method = 'enhanced'
        else:
            extraction_method = 'enhanced'  # 기본값
        
        if not args.quiet:
            method_names = {
                'sequential': "[SEQUENTIAL] 순차적 추출 방식 (텍스트-이미지 순서 보존, base64)",
                'enhanced': "[ENHANCED] 개선된 추출 방식 (Question/Answer 이미지 분리)", 
                'simple': "[SIMPLE] 기본 추출 방식 (기존 방식)"
            }
            print(method_names[extraction_method])
        
        # 추출 실행
        print("PDF에서 텍스트 및 이미지 추출 중...")
        
        if extraction_method == 'sequential':
            qa_pairs, stats = extract_cka_data_sequential(pdf_path)
        else:
            use_enhanced = (extraction_method == 'enhanced')
            qa_pairs, stats = extract_cka_data(pdf_path, use_enhanced=use_enhanced)
        
        if not qa_pairs:
            print("문제를 찾을 수 없습니다. PDF 형식을 확인해주세요.")
            return
        
        # 파일 저장
        if save_all_outputs(qa_pairs, extraction_method, args):
            # 결과 표시
            display_results(qa_pairs, stats, extraction_method, args)
        else:
            print("일부 파일 저장에 실패했습니다.")
    
    except PDFExtractionError as e:
        print(f"PDF 추출 오류: {e}")
        print("\n문제 해결 방법:")
        print("1. PDF 파일이 손상되지 않았는지 확인")
        print("2. 필요한 라이브러리가 모두 설치되었는지 확인")
        print("   pip install pdfplumber PyMuPDF PyPDF2")
        if args.sequential:
            print("3. 순차적 추출은 PyMuPDF가 필수입니다")
    
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    
    except Exception as e:
        print(f"예상치 못한 오류가 발생했습니다: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
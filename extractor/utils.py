"""
CKA PDF 추출기 - 유틸리티 함수들
"""

import re
import os
import json
import csv
from typing import List, Dict, Any, Optional
from models import QuestionAnswer, StructuredQuestionAnswer, ExtractionStats

def create_output_directory(dir_name: str = "extracted_images") -> str:
    """출력 디렉토리 생성"""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
        print(f"디렉토리 생성: {dir_name}")
    return dir_name

def clean_question_text(text: str) -> str:
    """질문 텍스트 정리"""
    if not text:
        return ""
    
    # 불필요한 텍스트 제거
    patterns_to_remove = [
        r'IT Certification Guaranteed, The Easy Way!\s*\d*',
        r'Task Weight:\s*\d+%\s*',
        r'Task\s*',
        r'Score:\s*\d+%\s*',
        r'Context\s*',
        r'^\s*Answer:\s*.*$'  # Answer: 이후 모든 내용 제거
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # 여러 줄바꿈을 정리
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)  # 여러 공백을 하나로
    
    return text.strip()

def clean_answer_text(text: str) -> str:
    """답변 텍스트 정리"""
    if not text:
        return "[답변이 제공되지 않음]"
    
    # 불필요한 텍스트 제거
    patterns_to_remove = [
        r'IT Certification Guaranteed, The Easy Way!\s*\d*',
        r'^Solution:\s*',
        r'^solution\s*$'
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)
    
    # 여러 줄바꿈을 정리
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    
    # 빈 답변 처리
    if not text or text.lower() == 'solution':
        return "[답변이 제공되지 않음]"
    
    return text

def extract_question_numbers_from_text(text: str) -> List[int]:
    """텍스트에서 모든 문제 번호 추출"""
    pattern = r'QUESTION NO:\s*(\d+)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [int(match) for match in matches]

def split_text_by_questions(text: str) -> Dict[int, str]:
    """텍스트를 문제별로 분할"""
    # QUESTION NO:를 기준으로 분할
    sections = re.split(r'(QUESTION NO:\s*\d+)', text, flags=re.IGNORECASE)
    
    question_texts = {}
    current_question_no = None
    
    for i, section in enumerate(sections):
        # QUESTION NO: 패턴 확인
        question_match = re.match(r'QUESTION NO:\s*(\d+)', section, re.IGNORECASE)
        
        if question_match:
            current_question_no = int(question_match.group(1))
        elif current_question_no is not None and section.strip():
            # 문제 내용
            question_texts[current_question_no] = section.strip()
    
    return question_texts

def separate_question_and_answer(content: str) -> tuple[str, str]:
    """문제 내용에서 질문과 답변을 분리"""
    # Answer:를 기준으로 분리
    answer_split = re.split(r'Answer:\s*', content, 1, flags=re.IGNORECASE)
    
    if len(answer_split) == 2:
        question_text = answer_split[0].strip()
        answer_text = answer_split[1].strip()
        
        # 다음 질문이 포함되어 있으면 제거
        answer_text = re.sub(r'\s*QUESTION NO:\s*\d+.*$', '', answer_text, 
                           flags=re.DOTALL | re.IGNORECASE)
        
        return clean_question_text(question_text), clean_answer_text(answer_text)
    else:
        # Answer: 가 없는 경우
        return clean_question_text(content), "[답변이 제공되지 않음]"

def calculate_statistics(qa_pairs: List[QuestionAnswer]) -> ExtractionStats:
    """통계 정보 계산"""
    stats = ExtractionStats()
    stats.total_questions = len(qa_pairs)
    
    for qa in qa_pairs:
        if qa.answer != "[답변이 제공되지 않음]":
            stats.questions_with_answers += 1
        if qa.has_images:
            stats.questions_with_images += 1
            stats.total_images += len(qa.images)
    
    return stats

def save_questions_only(qa_pairs: List[QuestionAnswer], filename: str = "cka_questions_only.txt"):
    """질문만 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("CKA 시험 문제 모음\n")
        f.write("=" * 50 + "\n\n")
        
        for qa in qa_pairs:
            f.write(f"문제 {qa.question_no}:\n")
            f.write(f"{qa.question}\n")
            if qa.has_images:
                # Sequential 방식 호환을 위한 이미지 정보 표시
                if qa.images and isinstance(qa.images[0], dict):
                    img_count = len(qa.images)
                    f.write(f"[이미지 포함: {img_count}개 (base64 인코딩)]\n")
                else:
                    f.write(f"[이미지 포함: {', '.join(qa.images)}]\n")
            f.write("\n" + "-" * 50 + "\n\n")

def save_answers_only(qa_pairs: List[QuestionAnswer], filename: str = "cka_answers_only.txt"):
    """답변만 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("CKA 시험 답변 모음\n")
        f.write("=" * 50 + "\n\n")
        
        for qa in qa_pairs:
            f.write(f"문제 {qa.question_no} 답변:\n")
            f.write(f"{qa.answer}\n")
            if qa.has_images:
                # Sequential 방식 호환을 위한 이미지 정보 표시
                if qa.images and isinstance(qa.images[0], dict):
                    img_count = len(qa.images)
                    f.write(f"[관련 이미지: {img_count}개 (base64 인코딩)]\n")
                else:
                    f.write(f"[관련 이미지: {', '.join(qa.images)}]\n")
            f.write("\n" + "-" * 50 + "\n\n")

def save_combined_qa(qa_pairs: List[QuestionAnswer], filename: str = "cka_questions_answers.txt"):
    """질문과 답변을 함께 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("CKA (Certified Kubernetes Administrator) 시험 문제집\n")
        f.write("=" * 70 + "\n\n")
        
        for qa in qa_pairs:
            f.write(f"문제 {qa.question_no}:\n")
            f.write(f"{qa.question}\n")
            if qa.has_images:
                # Sequential 방식 호환을 위한 이미지 정보 표시
                if qa.images and isinstance(qa.images[0], dict):
                    img_count = len(qa.images)
                    f.write(f"[포함된 이미지: {img_count}개 (base64 인코딩)]\n")
                else:
                    f.write(f"[포함된 이미지: {', '.join(qa.images)}]\n")
            f.write(f"\n답변:\n{qa.answer}\n\n")
            f.write("=" * 70 + "\n\n")

def save_as_json(data: List[Dict[str, Any]], filename: str = "cka_qa_data.json"):
    """JSON 형태로 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_as_csv(qa_pairs: List[QuestionAnswer], filename: str = "cka_qa_data.csv"):
    """CSV 형태로 저장"""
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['question_no', 'question', 'answer', 'images', 'has_images'])
        writer.writeheader()
        
        for qa in qa_pairs:
            writer.writerow({
                'question_no': qa.question_no,
                'question': qa.question,
                'answer': qa.answer,
                'images': str(len(qa.images)) + '개 (base64)' if qa.images and isinstance(qa.images[0], dict) else (', '.join(qa.images) if qa.images else ''),
                'has_images': qa.has_images
            })

def validate_pdf_path(pdf_path: str) -> str:
    """PDF 파일 경로 검증"""
    if not pdf_path:
        raise ValueError("PDF 파일 경로가 제공되지 않았습니다.")
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError(f"PDF 파일이 아닙니다: {pdf_path}")
    
    return pdf_path

def check_dependencies() -> Dict[str, bool]:
    """필요한 라이브러리 설치 여부 확인"""
    dependencies = {}
    
    try:
        import pdfplumber
        dependencies['pdfplumber'] = True
    except ImportError:
        dependencies['pdfplumber'] = False
    
    try:
        import fitz  # PyMuPDF
        dependencies['pymupdf'] = True
    except ImportError:
        dependencies['pymupdf'] = False
    
    try:
        import PyPDF2
        dependencies['pypdf2'] = True
    except ImportError:
        dependencies['pypdf2'] = False
    
    return dependencies

def print_dependency_status():
    """의존성 상태 출력"""
    print("=== PDF 처리 라이브러리 확인 ===")
    
    deps = check_dependencies()
    
    if deps.get('pdfplumber'):
        print("[O] pdfplumber 설치됨 (권장)")
    else:
        print("[X] pdfplumber 미설치 - pip install pdfplumber")
    
    if deps.get('pymupdf'):
        print("[O] PyMuPDF 설치됨 (이미지 추출에 필요)")
    else:
        print("[X] PyMuPDF 미설치 - pip install PyMuPDF (이미지 추출에 필요)")
    
    if deps.get('pypdf2'):
        print("[O] PyPDF2 설치됨")
    else:
        print("[X] PyPDF2 미설치 - pip install PyPDF2")
    
    if not deps.get('pymupdf'):
        print("\n경고: 이미지 추출 기능을 사용하려면 PyMuPDF가 필요합니다!")
        print("설치 명령: pip install PyMuPDF")
    
    if not any(deps.values()):
        print("\n경고: PDF 처리 라이브러리가 하나도 설치되지 않았습니다!")
        return False
    
    print()
    return True

def format_file_size(size_bytes: int) -> str:
    """파일 크기를 읽기 쉬운 형태로 변환"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def get_file_info(filepath: str) -> Dict[str, Any]:
    """파일 정보 조회"""
    if not os.path.exists(filepath):
        return {}
    
    stat = os.stat(filepath)
    return {
        'size': stat.st_size,
        'size_formatted': format_file_size(stat.st_size),
        'modified': stat.st_mtime,
        'exists': True
    }
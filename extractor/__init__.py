"""
CKA PDF 추출기 패키지

Certified Kubernetes Administrator 시험 문제를 PDF에서 추출하고
웹앱에서 사용할 수 있는 형태로 변환하는 도구입니다.
"""

__version__ = "1.0.0"
__author__ = "CKA Quiz App Team"
__description__ = "CKA PDF Question and Image Extractor"

# 주요 클래스와 함수들을 패키지 레벨에서 접근 가능하도록 함
from .models import (
    QuestionAnswer,
    StructuredQuestionAnswer, 
    ExtractionStats,
    PDFExtractionError,
    ImageExtractionError,
    TextParsingError
)

from .sequential_extractor import (
    PDFExtractor,
    ContentAnalyzer,
    SimpleExtractor,
    extract_cka_data
)

from .utils import (
    clean_question_text,
    clean_answer_text,
    save_questions_only,
    save_answers_only,
    save_combined_qa,
    save_as_json,
    save_as_csv,
    check_dependencies,
    print_dependency_status
)

__all__ = [
    # 모델들
    'QuestionAnswer',
    'StructuredQuestionAnswer',
    'ExtractionStats',
    'PDFExtractionError',
    'ImageExtractionError', 
    'TextParsingError',
    
    # 추출기들
    'PDFExtractor',
    'ContentAnalyzer',
    'SimpleExtractor',
    'extract_cka_data',
    
    # 유틸리티들
    'clean_question_text',
    'clean_answer_text',
    'save_questions_only',
    'save_answers_only', 
    'save_combined_qa',
    'save_as_json',
    'save_as_csv',
    'check_dependencies',
    'print_dependency_status'
]
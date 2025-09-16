"""
CKA PDF 추출기 - 데이터 모델 정의
"""

from dataclasses import dataclass
from typing import List, Optional, Union
from enum import Enum

class ContentType(Enum):
    """콘텐츠 타입 정의"""
    TEXT = "text"
    IMAGE = "image"

@dataclass
class ImageInfo:
    """이미지 정보"""
    filename: str
    position: float  # 페이지 내 Y 좌표 (위치)
    width: int
    height: int
    page_num: int

@dataclass
class TextBlock:
    """텍스트 블록 정보"""
    content: str
    position: float  # 페이지 내 Y 좌표 (위치)
    page_num: int
    font_size: Optional[float] = None

@dataclass
class ContentElement:
    """콘텐츠 요소 (텍스트 또는 이미지)"""
    type: ContentType
    content: Union[str, ImageInfo]
    position: float
    page_num: int

@dataclass
class QuestionAnswer:
    """질문-답변 쌍 (기본)"""
    question_no: int
    question: str
    answer: str
    images: List[str] = None
    has_images: bool = False
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        self.has_images = len(self.images) > 0

@dataclass
class StructuredQuestionAnswer:
    """구조화된 질문-답변 쌍 (텍스트와 이미지 순서 포함)"""
    question_no: int
    question_content: List[ContentElement]
    answer_content: List[ContentElement]
    raw_question: str
    raw_answer: str
    total_images: int = 0
    
    def __post_init__(self):
        # 이미지 개수 계산
        question_images = sum(1 for elem in self.question_content if elem.type == ContentType.IMAGE)
        answer_images = sum(1 for elem in self.answer_content if elem.type == ContentType.IMAGE)
        self.total_images = question_images + answer_images
    
    def to_basic_qa(self) -> QuestionAnswer:
        """기본 QuestionAnswer 형태로 변환"""
        # 모든 이미지 파일명 추출
        all_images = []
        for elem in self.question_content + self.answer_content:
            if elem.type == ContentType.IMAGE:
                all_images.append(elem.content.filename)
        
        return QuestionAnswer(
            question_no=self.question_no,
            question=self.raw_question,
            answer=self.raw_answer,
            images=all_images,
            has_images=len(all_images) > 0
        )
    
    def to_web_format(self) -> dict:
        """웹페이지용 형태로 변환"""
        def content_to_dict(content_list):
            result = []
            for elem in content_list:
                if elem.type == ContentType.TEXT:
                    result.append({
                        'type': 'text',
                        'content': elem.content,
                        'position': elem.position
                    })
                else:  # IMAGE
                    result.append({
                        'type': 'image',
                        'filename': elem.content.filename,
                        'position': elem.position,
                        'width': elem.content.width,
                        'height': elem.content.height
                    })
            return result
        
        return {
            'question_no': self.question_no,
            'question': self.raw_question,
            'answer': self.raw_answer,
            'question_content': content_to_dict(self.question_content),
            'answer_content': content_to_dict(self.answer_content),
            'images': [elem.content.filename for elem in self.question_content + self.answer_content 
                      if elem.type == ContentType.IMAGE],
            'has_images': self.total_images > 0,
            'total_images': self.total_images
        }

@dataclass
class ExtractionStats:
    """추출 통계 정보"""
    total_questions: int = 0
    questions_with_answers: int = 0
    questions_with_images: int = 0
    total_images: int = 0
    processing_time: float = 0.0
    
    @property
    def answer_completion_rate(self) -> float:
        """답변 완성도 (백분율)"""
        if self.total_questions == 0:
            return 0.0
        return (self.questions_with_answers / self.total_questions) * 100
    
    @property
    def image_inclusion_rate(self) -> float:
        """이미지 포함률 (백분율)"""
        if self.total_questions == 0:
            return 0.0
        return (self.questions_with_images / self.total_questions) * 100
    
    def __str__(self) -> str:
        return f"""
=== 추출 결과 통계 ===
총 문제 수: {self.total_questions}
답변이 있는 문제: {self.questions_with_answers}
답변이 없는 문제: {self.total_questions - self.questions_with_answers}
이미지가 있는 문제: {self.questions_with_images}
총 이미지 수: {self.total_images}
답변 완성도: {self.answer_completion_rate:.1f}%
이미지 포함률: {self.image_inclusion_rate:.1f}%
처리 시간: {self.processing_time:.2f}초
"""

class PDFExtractionError(Exception):
    """PDF 추출 관련 예외"""
    pass

class ImageExtractionError(Exception):
    """이미지 추출 관련 예외"""
    pass

class TextParsingError(Exception):
    """텍스트 파싱 관련 예외"""
    pass
"""
순차적 텍스트-이미지 추출기
PDF를 읽으면서 텍스트와 이미지를 순서대로 추출하여 하나의 구조화된 데이터로 생성
"""

import os
import re
import time
import base64
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from models import QuestionAnswer, ExtractionStats, PDFExtractionError

# PDF 처리 라이브러리 임포트
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

@dataclass
class ContentElement:
    """콘텐츠 요소 (텍스트 또는 이미지)"""
    type: str  # 'text' 또는 'image'
    content: Union[str, Dict[str, str]]  # 텍스트 또는 이미지 데이터
    position: float  # 페이지 내 Y 좌표
    page_num: int
    element_index: int  # 페이지 내 요소 순서

@dataclass  
class QuestionAnswerStructured:
    """구조화된 질문-답변 쌍"""
    question_no: int
    question_elements: List[ContentElement]  # Question 영역의 모든 요소들
    answer_elements: List[ContentElement]    # Answer 영역의 모든 요소들
    raw_question_text: str
    raw_answer_text: str

class SequentialExtractor:
    """PDF를 순차적으로 읽어서 텍스트와 이미지를 함께 추출"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        if not HAS_PYMUPDF:
            raise PDFExtractionError("순차적 추출을 위해서는 PyMuPDF가 필요합니다.")
    
    def extract_sequential_content(self) -> List[ContentElement]:
        """PDF를 페이지별로 읽어서 텍스트와 이미지를 순서대로 추출"""
        all_elements = []
        
        try:
            doc = fitz.open(self.pdf_path)
            
            for page_num in range(doc.page_count):
                print(f"페이지 {page_num + 1} 처리 중...")
                page = doc[page_num]
                
                # 페이지의 모든 요소들 수집
                page_elements = self._extract_page_elements(page, page_num)
                
                # 페이지 내에서 Y 좌표 순으로 정렬 (읽기 순서)
                page_elements.sort(key=lambda x: (x.position, x.element_index))
                
                all_elements.extend(page_elements)
            
            doc.close()
            print(f"총 {len(all_elements)}개 요소 추출 완료")
            
        except Exception as e:
            raise PDFExtractionError(f"순차적 콘텐츠 추출 실패: {e}")
        
        return all_elements
    
    def _extract_page_elements(self, page, page_num: int) -> List[ContentElement]:
        """한 페이지에서 텍스트와 이미지 요소들을 추출"""
        elements = []
        element_index = 0
        
        # 1. 텍스트 블록들 추출
        text_elements = self._extract_text_blocks(page, page_num, element_index)
        elements.extend(text_elements)
        element_index += len(text_elements)
        
        # 2. 이미지들 추출
        image_elements = self._extract_image_blocks(page, page_num, element_index)
        elements.extend(image_elements)
        
        return elements
    
    def _extract_text_blocks(self, page, page_num: int, start_index: int) -> List[ContentElement]:
        """페이지에서 텍스트 블록들을 추출"""
        text_elements = []
        
        try:
            blocks = page.get_text("dict")["blocks"]
            
            for block_idx, block in enumerate(blocks):
                if "lines" in block:  # 텍스트 블록
                    # 블록의 모든 텍스트 수집
                    block_text = ""
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        block_text += line_text.strip() + "\n"
                    
                    block_text = block_text.strip()
                    
                    if block_text:  # 빈 텍스트가 아닌 경우만
                        element = ContentElement(
                            type='text',
                            content=block_text,
                            position=block["bbox"][1],  # Y 좌표
                            page_num=page_num,
                            element_index=start_index + block_idx
                        )
                        text_elements.append(element)
        
        except Exception as e:
            print(f"페이지 {page_num + 1} 텍스트 추출 오류: {e}")
        
        return text_elements
    
    def _extract_image_blocks(self, page, page_num: int, start_index: int) -> List[ContentElement]:
        """페이지에서 이미지들을 추출하고 base64로 인코딩"""
        image_elements = []
        
        try:
            image_list = page.get_images(full=True)
            
            for img_idx, img in enumerate(image_list):
                try:
                    # 이미지 데이터 추출
                    xref = img[0]
                    pix = fitz.Pixmap(page.parent, xref)
                    
                    # CMYK를 RGB로 변환
                    if pix.n - pix.alpha >= 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    # base64로 인코딩
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
                    # 이미지 위치 정보
                    img_rects = page.get_image_rects(xref)
                    if img_rects:
                        y_position = img_rects[0][1]
                        width = int(img_rects[0][2] - img_rects[0][0])
                        height = int(img_rects[0][3] - img_rects[0][1])
                    else:
                        y_position = 0
                        width = pix.width
                        height = pix.height
                    
                    # 이미지 메타데이터
                    image_data = {
                        'base64': img_base64,
                        'format': 'png',
                        'width': width,
                        'height': height,
                        'page': page_num + 1,
                        'index': img_idx + 1
                    }
                    
                    element = ContentElement(
                        type='image',
                        content=image_data,
                        position=y_position,
                        page_num=page_num,
                        element_index=start_index + img_idx
                    )
                    
                    image_elements.append(element)
                    pix = None
                    
                except Exception as e:
                    print(f"페이지 {page_num + 1}, 이미지 {img_idx + 1} 처리 실패: {e}")
                    continue
        
        except Exception as e:
            print(f"페이지 {page_num + 1} 이미지 추출 오류: {e}")
        
        return image_elements
    
    def parse_qa_from_sequential_content(self, elements: List[ContentElement]) -> List[QuestionAnswerStructured]:
        """순차적 콘텐츠에서 Question-Answer 쌍을 파싱"""
        qa_pairs = []
        
        # 전체 텍스트를 재구성하여 문제 경계 찾기
        full_text = ""
        element_positions = []  # 각 요소가 전체 텍스트에서 시작하는 위치
        
        for element in elements:
            if element.type == 'text':
                element_positions.append((len(full_text), element))
                full_text += element.content + "\n"
            else:  # image
                element_positions.append((len(full_text), element))
                full_text += f"[IMAGE_{element.page_num}_{element.element_index}]\n"
        
        # QUESTION NO: 패턴으로 문제 경계 찾기
        question_boundaries = self._find_question_boundaries(full_text)
        
        # 각 문제별로 요소들 분류
        for question_no, boundaries in question_boundaries.items():
            try:
                question_elements, answer_elements = self._classify_elements_by_boundaries(
                    element_positions, boundaries
                )
                
                # 원시 텍스트 추출
                raw_question = self._extract_raw_text(question_elements, is_question=True)
                raw_answer = self._extract_raw_text(answer_elements, is_question=False)
                
                qa_structured = QuestionAnswerStructured(
                    question_no=question_no,
                    question_elements=question_elements,
                    answer_elements=answer_elements,
                    raw_question_text=raw_question,
                    raw_answer_text=raw_answer
                )
                
                qa_pairs.append(qa_structured)
                
                # 간단한 진행 상황만 출력
                q_images = len([e for e in question_elements if e.type == 'image'])
                a_images = len([e for e in answer_elements if e.type == 'image'])
                if (q_images + a_images) > 0:
                    print(f"문제 {question_no}: Question {q_images}개, Answer {a_images}개 이미지")
                
            except Exception as e:
                print(f"문제 {question_no} 파싱 실패: {e}")
                continue
        
        return qa_pairs
    
    def _find_question_boundaries(self, full_text: str) -> Dict[int, Dict[str, int]]:
        """전체 텍스트에서 각 문제의 경계 찾기"""
        boundaries = {}
        
        # QUESTION NO: 패턴 찾기
        question_matches = list(re.finditer(r'QUESTION NO:\s*(\d+)', full_text, re.IGNORECASE))
        for i, match in enumerate(question_matches):
            question_no = int(match.group(1))
            question_start = match.start()
            
            # 다음 문제의 시작점
            if i + 1 < len(question_matches):
                question_end = question_matches[i + 1].start()
            else:
                question_end = len(full_text)
            
            # 해당 문제 영역에서 Answer: 찾기
            question_text = full_text[question_start:question_end]
            answer_match = re.search(r'Answer:\s*', question_text, re.IGNORECASE)
            
            if answer_match:
                # Answer: 텍스트의 끝부분부터 실제 답변 시작
                answer_marker_end = question_start + answer_match.end()
                boundaries[question_no] = {
                    'question_start': question_start,
                    'question_end': question_start + answer_match.start(),  # Answer: 마커 전까지가 질문
                    'answer_start': answer_marker_end,  # Answer: 마커 다음부터 답변
                    'answer_end': question_end
                }
            else:
                # Answer: 가 없는 경우
                boundaries[question_no] = {
                    'question_start': question_start,
                    'question_end': question_end,
                    'answer_start': question_end,
                    'answer_end': question_end
                }
        
        return boundaries
    
    def _classify_elements_by_boundaries(self, element_positions: List[Tuple[int, ContentElement]], 
                                       boundaries: Dict[str, int]) -> Tuple[List[ContentElement], List[ContentElement]]:
        """경계 정보를 바탕으로 요소들을 Question/Answer로 분류"""
        question_elements = []
        answer_elements = []
        
        question_start = boundaries['question_start']
        question_end = boundaries['question_end']
        answer_start = boundaries['answer_start']
        answer_end = boundaries['answer_end']
        
        for text_pos, element in element_positions:
            if element.type == 'image':
                # 이미지는 단순히 위치로 분류
                if question_start <= text_pos < question_end:
                    question_elements.append(element)
                elif answer_start <= text_pos < answer_end:
                    answer_elements.append(element)
            else:
                # 텍스트의 경우 Answer: 마커로 분할 필요 여부 확인
                element_content = element.content
                answer_match = re.search(r'Answer:\s*', element_content, re.IGNORECASE)
                
                if answer_match and question_start <= text_pos < answer_end:
                    # Answer: 마커가 포함된 텍스트 블록을 분할
                    question_part = element_content[:answer_match.start()].strip()
                    answer_part = element_content[answer_match.end():].strip()
                    
                    # Question 부분
                    if question_part:
                        question_element = ContentElement(
                            type='text',
                            content=question_part,
                            position=element.position,
                            page_num=element.page_num,
                            element_index=element.element_index
                        )
                        question_elements.append(question_element)
                    
                    # Answer 부분
                    if answer_part:
                        answer_element = ContentElement(
                            type='text',
                            content=answer_part,
                            position=element.position + answer_match.end(),
                            page_num=element.page_num,
                            element_index=element.element_index + 1
                        )
                        answer_elements.append(answer_element)
                else:
                    # Answer: 마커가 없는 경우 기존 로직대로
                    if question_start <= text_pos < question_end:
                        question_elements.append(element)
                    elif answer_start <= text_pos < answer_end:
                        answer_elements.append(element)
        
        return question_elements, answer_elements
    
    def _extract_raw_text(self, elements: List[ContentElement], is_question: bool = True) -> str:
        """요소들에서 텍스트만 추출"""
        text_parts = []
        for element in elements:
            if element.type == 'text':
                text_parts.append(element.content)
        
        raw_text = "\n".join(text_parts).strip()
        
        # 공통 텍스트 정리
        raw_text = re.sub(r'IT Certification Guaranteed, The Easy Way!\s*\d*', '', raw_text)
        raw_text = re.sub(r'Task Weight:\s*\d+%\s*', '', raw_text)
        raw_text = re.sub(r'Score:\s*\d+%\s*', '', raw_text)
        
        if is_question:
            # Question 영역: QUESTION NO: 제거, Answer: 및 그 이후 내용 제거
            raw_text = re.sub(r'QUESTION NO:\s*\d+\s*', '', raw_text)
            raw_text = re.sub(r'\s*Answer:.*$', '', raw_text, flags=re.DOTALL)
        else:
            # Answer 영역: Answer: 마커와 그 이전 모든 내용 제거
            raw_text = re.sub(r'^.*?Answer:\s*', '', raw_text, flags=re.DOTALL)
        
        raw_text = re.sub(r'\n+', '\n', raw_text)
        cleaned_text = raw_text.strip()
        
        return cleaned_text if cleaned_text else "[내용이 제공되지 않음]"
    
    def convert_to_basic_qa_pairs(self, structured_pairs: List[QuestionAnswerStructured]) -> List[QuestionAnswer]:
        """구조화된 QA를 기본 QuestionAnswer 형태로 변환 (웹앱 호환성)"""
        basic_pairs = []
        
        for structured in structured_pairs:
            # 이미지 데이터 준비 (base64 형태로)
            all_images = []
            
            # Question 이미지들
            for element in structured.question_elements:
                if element.type == 'image':
                    image_info = {
                        'type': 'question',
                        'base64': element.content['base64'],
                        'format': element.content['format'],
                        'width': element.content['width'],
                        'height': element.content['height']
                    }
                    all_images.append(image_info)
            
            # Answer 이미지들  
            for element in structured.answer_elements:
                if element.type == 'image':
                    image_info = {
                        'type': 'answer',
                        'base64': element.content['base64'],
                        'format': element.content['format'],
                        'width': element.content['width'],
                        'height': element.content['height']
                    }
                    all_images.append(image_info)
            
            # QuestionAnswer 객체 생성
            basic_qa = QuestionAnswer(
                question_no=structured.question_no,
                question=structured.raw_question_text,
                answer=structured.raw_answer_text,
                images=all_images,  # base64 데이터로 직접 설정
                has_images=len(all_images) > 0
            )
            
            basic_pairs.append(basic_qa)
        
        return basic_pairs

def extract_cka_data_sequential(pdf_path: str) -> Tuple[List[QuestionAnswer], ExtractionStats]:
    """
    순차적 방식으로 CKA PDF 데이터 추출
    
    Args:
        pdf_path: PDF 파일 경로
    
    Returns:
        (질문답변_리스트, 통계정보)
    """
    start_time = time.time()
    
    try:
        print("[SEQUENTIAL] 순차적 추출 방식: 텍스트와 이미지를 순서대로 처리")
        
        extractor = SequentialExtractor(pdf_path)
        
        # 1단계: 순차적 콘텐츠 추출
        elements = extractor.extract_sequential_content()
        
        # 2단계: Question-Answer 파싱
        structured_pairs = extractor.parse_qa_from_sequential_content(elements)
        
        # 3단계: 기본 형태로 변환
        qa_pairs = extractor.convert_to_basic_qa_pairs(structured_pairs)
        
        # 통계 계산
        stats = ExtractionStats()
        stats.total_questions = len(qa_pairs)
        stats.questions_with_answers = sum(1 for qa in qa_pairs if qa.answer != "[내용이 제공되지 않음]")
        stats.questions_with_images = sum(1 for qa in qa_pairs if qa.has_images)
        stats.total_images = sum(len(qa.images) for qa in qa_pairs)
        stats.processing_time = time.time() - start_time
        
        return qa_pairs, stats
        
    except Exception as e:
        raise PDFExtractionError(f"순차적 CKA 데이터 추출 실패: {e}")
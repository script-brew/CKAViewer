"""
CKA PDF 추출기 - 핵심 추출 기능 (텍스트 순서 기반 이미지 매핑)
"""

import os
import re
import time
from typing import List, Dict, Tuple, Optional
from models import (
    QuestionAnswer, StructuredQuestionAnswer, ImageInfo, TextBlock, 
    ContentElement, ContentType, ExtractionStats,
    PDFExtractionError, ImageExtractionError, TextParsingError
)
from utils import (
    create_output_directory, clean_question_text, clean_answer_text,
    extract_question_numbers_from_text, split_text_by_questions,
    separate_question_and_answer, calculate_statistics
)

# PDF 처리 라이브러리 임포트
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

class PDFExtractor:
    """PDF에서 텍스트와 이미지를 추출하는 클래스"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.image_dir = create_output_directory("extracted_images")
        
    def extract_text_simple(self) -> str:
        """간단한 텍스트 추출 (위치 정보 없음)"""
        if HAS_PDFPLUMBER:
            return self._extract_with_pdfplumber()
        elif HAS_PYMUPDF:
            return self._extract_with_pymupdf()
        elif HAS_PYPDF2:
            return self._extract_with_pypdf2()
        else:
            raise PDFExtractionError("PDF 처리 라이브러리가 설치되지 않았습니다.")
    
    def _extract_with_pdfplumber(self) -> str:
        """pdfplumber를 사용한 텍스트 추출"""
        text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise PDFExtractionError(f"pdfplumber 텍스트 추출 실패: {e}")
        return text
    
    def _extract_with_pymupdf(self) -> str:
        """PyMuPDF를 사용한 텍스트 추출"""
        text = ""
        try:
            doc = fitz.open(self.pdf_path)
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"
            doc.close()
        except Exception as e:
            raise PDFExtractionError(f"PyMuPDF 텍스트 추출 실패: {e}")
        return text
    
    def _extract_with_pypdf2(self) -> str:
        """PyPDF2를 사용한 텍스트 추출"""
        text = ""
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise PDFExtractionError(f"PyPDF2 텍스트 추출 실패: {e}")
        return text

class TextBasedImageMapper:
    """텍스트 순서 기반 이미지 매핑 클래스"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.extractor = PDFExtractor(pdf_path)
        self.image_dir = self.extractor.image_dir
    
    def extract_qa_pairs_with_text_mapping(self) -> List[QuestionAnswer]:
        """텍스트 순서를 기반으로 이미지를 매핑한 질문-답변 쌍 추출"""
        try:
            print("1단계: PDF 텍스트 추출 중...")
            full_text = self.extractor.extract_text_simple()
            
            print("2단계: 텍스트 마커 분석 중...")
            text_markers = self._analyze_text_markers(full_text)
            
            print("3단계: 페이지별 이미지 위치 분석 중...")
            page_images = self._extract_images_with_positions()
            
            print("4단계: 텍스트 순서 기반 이미지 매핑 중...")
            qa_pairs = self._map_images_by_text_order(text_markers, page_images, full_text)
            
            return qa_pairs
            
        except Exception as e:
            raise PDFExtractionError(f"텍스트 기반 이미지 매핑 실패: {e}")
    
    def _analyze_text_markers(self, full_text: str) -> List[Dict[str, any]]:
        """텍스트에서 QUESTION NO:와 Answer: 마커들의 위치 분석"""
        markers = []
        
        # QUESTION NO: 패턴 찾기
        question_pattern = r'QUESTION NO:\s*(\d+)'
        for match in re.finditer(question_pattern, full_text, re.IGNORECASE):
            markers.append({
                'type': 'question',
                'number': int(match.group(1)),
                'position': match.start(),
                'text': match.group(0)
            })
        
        # Answer: 패턴 찾기
        answer_pattern = r'Answer:\s*'
        for match in re.finditer(answer_pattern, full_text, re.IGNORECASE):
            markers.append({
                'type': 'answer',
                'number': None,  # 나중에 연결
                'position': match.start(),
                'text': match.group(0)
            })
        
        # 위치순으로 정렬
        markers.sort(key=lambda x: x['position'])
        
        # Answer를 해당 Question에 연결
        current_question = None
        for marker in markers:
            if marker['type'] == 'question':
                current_question = marker['number']
            elif marker['type'] == 'answer' and current_question:
                marker['number'] = current_question
        
        return markers
    
    def _extract_images_with_positions(self) -> Dict[int, List[Dict[str, any]]]:
        """페이지별로 이미지와 대략적인 텍스트 위치 추출"""
        if not HAS_PYMUPDF:
            raise PDFExtractionError("이미지 위치 분석을 위해서는 PyMuPDF가 필요합니다.")
        
        page_images = {}
        
        try:
            doc = fitz.open(self.pdf_path)
            cumulative_text_length = 0
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                page_start_pos = cumulative_text_length
                page_end_pos = cumulative_text_length + len(page_text)
                
                images = []
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    try:
                        # 이미지 위치 정보 (페이지 내)
                        img_rects = page.get_image_rects(img[0])
                        if img_rects:
                            img_rect = img_rects[0]
                            y_pos_in_page = img_rect[1]  # Y 좌표
                        else:
                            y_pos_in_page = 0
                        
                        # 전체 텍스트에서의 대략적인 위치 추정
                        # 페이지 내 Y 위치 비율을 이용해 텍스트 위치 추정
                        page_height = page.rect.height
                        if page_height > 0:
                            y_ratio = y_pos_in_page / page_height
                            estimated_text_pos = page_start_pos + int(len(page_text) * y_ratio)
                        else:
                            estimated_text_pos = page_start_pos
                        
                        images.append({
                            'img_data': img,
                            'img_index': img_index,
                            'page_num': page_num,
                            'y_pos_in_page': y_pos_in_page,
                            'estimated_text_pos': estimated_text_pos,
                            'page_start_pos': page_start_pos,
                            'page_end_pos': page_end_pos
                        })
                        
                    except Exception as e:
                        print(f"페이지 {page_num+1}, 이미지 {img_index+1} 위치 분석 실패: {e}")
                        continue
                
                page_images[page_num] = images
                cumulative_text_length = page_end_pos + 1  # +1 for page break
            
            doc.close()
            
        except Exception as e:
            raise PDFExtractionError(f"이미지 위치 분석 실패: {e}")
        
        return page_images
    
    def _map_images_by_text_order(self, text_markers: List[Dict[str, any]], 
                                page_images: Dict[int, List[Dict[str, any]]], 
                                full_text: str) -> List[QuestionAnswer]:
        """텍스트 순서를 기반으로 이미지를 Question/Answer에 매핑"""
        
        # 모든 이미지를 하나의 리스트로 합치고 위치순 정렬
        all_images = []
        for page_num, images in page_images.items():
            all_images.extend(images)
        
        all_images.sort(key=lambda x: x['estimated_text_pos'])
        
        # 각 문제별로 Question과 Answer 영역 정의
        question_ranges = self._define_question_ranges(text_markers)
        
        # 각 문제별로 이미지 분류
        question_images = {}  # {question_no: {'question': [images], 'answer': [images]}}
        
        for question_no, ranges in question_ranges.items():
            question_images[question_no] = {'question': [], 'answer': []}
            
            question_start = ranges['question_start']
            question_end = ranges['question_end']
            answer_start = ranges['answer_start']
            answer_end = ranges['answer_end']
            
            # 해당 범위에 있는 이미지들 찾기
            for img_info in all_images:
                img_pos = img_info['estimated_text_pos']
                
                # Question 영역 (QUESTION NO: ~ Answer: 사이)
                if question_start <= img_pos < question_end:
                    question_images[question_no]['question'].append(img_info)
                    
                # Answer 영역 (Answer: ~ 다음 QUESTION NO: 사이)
                elif answer_start <= img_pos < answer_end:
                    question_images[question_no]['answer'].append(img_info)
        
        # 이미지 저장 및 QA 쌍 생성
        qa_pairs = []
        
        # 문제별 텍스트 추출
        question_texts = split_text_by_questions(full_text)
        
        for question_no in sorted(question_ranges.keys()):
            try:
                # 텍스트 내용 가져오기
                content = question_texts.get(question_no, "")
                if content:
                    question_text, answer_text = separate_question_and_answer(content)
                else:
                    question_text = f"문제 {question_no} (텍스트 추출 실패)"
                    answer_text = "[답변이 제공되지 않음]"
                
                # 이미지 저장
                q_images = question_images.get(question_no, {}).get('question', [])
                a_images = question_images.get(question_no, {}).get('answer', [])
                
                question_image_files = self._save_images_with_naming(q_images, question_no, 'question')
                answer_image_files = self._save_images_with_naming(a_images, question_no, 'answer')
                
                # QA 쌍 생성
                all_image_files = question_image_files + answer_image_files
                
                qa_pair = QuestionAnswer(
                    question_no=question_no,
                    question=question_text,
                    answer=answer_text,
                    images=all_image_files
                )
                
                qa_pairs.append(qa_pair)
                
                # 로그 출력
                if question_image_files or answer_image_files:
                    print(f"문제 {question_no}: Question {len(question_image_files)}개, Answer {len(answer_image_files)}개 이미지")
                
            except Exception as e:
                print(f"문제 {question_no} 처리 중 오류: {e}")
                # 오류가 있어도 텍스트만으로라도 QA 생성
                qa_pair = QuestionAnswer(
                    question_no=question_no,
                    question=question_text if 'question_text' in locals() else f"문제 {question_no}",
                    answer="[처리 중 오류 발생]",
                    images=[]
                )
                qa_pairs.append(qa_pair)
                continue
        
        return qa_pairs
    
    def _define_question_ranges(self, text_markers: List[Dict[str, any]]) -> Dict[int, Dict[str, int]]:
        """각 문제의 Question과 Answer 영역 범위 정의"""
        ranges = {}
        
        # 문제 번호별로 마커들 그룹화
        question_markers = [m for m in text_markers if m['type'] == 'question']
        answer_markers = [m for m in text_markers if m['type'] == 'answer']
        
        for i, q_marker in enumerate(question_markers):
            question_no = q_marker['number']
            question_start = q_marker['position']
            
            # 해당 문제의 Answer: 찾기
            answer_marker = None
            for a_marker in answer_markers:
                if a_marker['number'] == question_no and a_marker['position'] > question_start:
                    answer_marker = a_marker
                    break
            
            if answer_marker:
                question_end = answer_marker['position']
                answer_start = answer_marker['position']
                
                # 다음 문제의 시작점 찾기
                if i + 1 < len(question_markers):
                    answer_end = question_markers[i + 1]['position']
                else:
                    answer_end = float('inf')  # 마지막 문제
            else:
                # Answer:가 없는 경우
                if i + 1 < len(question_markers):
                    question_end = question_markers[i + 1]['position']
                else:
                    question_end = float('inf')
                
                answer_start = question_end
                answer_end = question_end
            
            ranges[question_no] = {
                'question_start': question_start,
                'question_end': question_end,
                'answer_start': answer_start,
                'answer_end': answer_end
            }
        
        return ranges
    
    def _save_images_with_naming(self, images: List[Dict[str, any]], 
                               question_no: int, region_type: str) -> List[str]:
        """이미지들을 적절한 이름으로 저장"""
        if not HAS_PYMUPDF or not images:
            return []
        
        saved_files = []
        
        try:
            doc = fitz.open(self.pdf_path)
            
            for img_index, img_info in enumerate(images):
                try:
                    img_data = img_info['img_data']
                    xref = img_data[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    # 파일명 생성: question_5_img_1.png 또는 answer_5_img_1.png
                    filename = f"{region_type}_{question_no}_img_{img_index + 1}.png"
                    filepath = os.path.join(self.image_dir, filename)
                    
                    # CMYK를 RGB로 변환
                    if pix.n - pix.alpha >= 4:
                        pix1 = fitz.Pixmap(fitz.csRGB, pix)
                        pix1.save(filepath)
                        pix1 = None
                    else:
                        pix.save(filepath)
                    
                    pix = None
                    saved_files.append(filename)
                    
                except Exception as e:
                    print(f"이미지 저장 실패 ({region_type}_{question_no}_img_{img_index + 1}): {e}")
                    continue
            
            doc.close()
            
        except Exception as e:
            print(f"이미지 저장 중 오류: {e}")
        
        return saved_files

class SimpleExtractor:
    """간단한 추출 방식 (기존 방식과 호환)"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.extractor = PDFExtractor(pdf_path)
    
    def extract_qa_pairs(self) -> List[QuestionAnswer]:
        """기본 질문-답변 쌍 추출"""
        try:
            # 텍스트 추출
            text = self.extractor.extract_text_simple()
            
            # 문제별 이미지 추출 (기존 방식)
            question_images = self._extract_images_by_question()
            
            # 텍스트 파싱
            qa_pairs = self._parse_text_to_qa_pairs(text, question_images)
            
            return qa_pairs
            
        except Exception as e:
            raise PDFExtractionError(f"간단 추출 실패: {e}")
    
    def _extract_images_by_question(self) -> Dict[str, List[str]]:
        """문제 번호 기준으로 이미지 추출 (기존 방식)"""
        question_images = {}
        
        if not HAS_PYMUPDF:
            return question_images
        
        try:
            doc = fitz.open(self.pdf_path)
            total_images = 0
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                
                # 페이지에서 QUESTION NO: 패턴 찾기
                question_matches = re.findall(r'QUESTION NO:\s*(\d+)', page_text)
                image_list = page.get_images(full=True)
                
                if image_list and question_matches:
                    primary_question = question_matches[0]
                    
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            pix = fitz.Pixmap(doc, xref)
                            
                            image_filename = f"question_{primary_question}_img_{img_index+1}.png"
                            image_path = os.path.join(self.extractor.image_dir, image_filename)
                            
                            if pix.n - pix.alpha < 4:
                                pix.save(image_path)
                            else:
                                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                                pix1.save(image_path)
                                pix1 = None
                            
                            if primary_question not in question_images:
                                question_images[primary_question] = []
                            question_images[primary_question].append(image_filename)
                            total_images += 1
                            pix = None
                            
                        except Exception as e:
                            print(f"이미지 추출 실패: {e}")
                            continue
            
            doc.close()
            print(f"총 {total_images}개의 이미지를 추출했습니다.")
            
        except Exception as e:
            raise ImageExtractionError(f"이미지 추출 실패: {e}")
        
        return question_images
    
    def _parse_text_to_qa_pairs(self, text: str, question_images: Dict[str, List[str]]) -> List[QuestionAnswer]:
        """텍스트를 질문-답변 쌍으로 파싱"""
        qa_pairs = []
        
        # 문제별로 텍스트 분할
        question_texts = split_text_by_questions(text)
        
        for question_no, content in question_texts.items():
            try:
                # 질문과 답변 분리
                question_text, answer_text = separate_question_and_answer(content)
                
                # 해당 문제의 이미지 파일명 가져오기
                images = question_images.get(str(question_no), [])
                
                if question_text:  # 빈 질문은 제외
                    qa = QuestionAnswer(
                        question_no=question_no,
                        question=question_text,
                        answer=answer_text,
                        images=images
                    )
                    qa_pairs.append(qa)
                    
                    if images:
                        print(f"문제 {question_no}에 {len(images)}개 이미지 연결: {', '.join(images)}")
            
            except Exception as e:
                print(f"문제 {question_no} 파싱 실패: {e}")
                continue
        
        return qa_pairs

def extract_cka_data(pdf_path: str, use_enhanced: bool = True) -> Tuple[List[QuestionAnswer], ExtractionStats]:
    """
    CKA PDF에서 데이터 추출
    
    Args:
        pdf_path: PDF 파일 경로
        use_enhanced: 개선된 텍스트 순서 기반 이미지 매핑 사용 여부
    
    Returns:
        (질문답변_리스트, 통계정보)
    """
    start_time = time.time()
    
    try:
        if use_enhanced and HAS_PYMUPDF:
            # 개선된 추출 (텍스트 순서 기반 Question/Answer 이미지 분리)
            print("🔧 개선된 추출 방식: 텍스트 순서 기반 이미지 매핑")
            extractor = TextBasedImageMapper(pdf_path)
            qa_pairs = extractor.extract_qa_pairs_with_text_mapping()
        else:
            # 간단한 추출 (기존 방식)
            print("📝 기본 추출 방식 사용")
            simple_extractor = SimpleExtractor(pdf_path)
            qa_pairs = simple_extractor.extract_qa_pairs()
        
        # 통계 계산
        stats = calculate_statistics(qa_pairs)
        stats.processing_time = time.time() - start_time
        
        return qa_pairs, stats
        
    except Exception as e:
        raise PDFExtractionError(f"CKA 데이터 추출 실패: {e}")
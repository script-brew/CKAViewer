// CKA 학습 웹앱 - JavaScript

// 전역 변수들
let questionsData = [];
let currentMode = 'basic';
let currentIndex = 0;
let shuffledIndices = [];
// Sequential 방식은 이미지가 JSON에 포함되므로 별도 Map 불필요

// DOM 요소들
const fileUpload = document.getElementById('fileUpload');
const modeSelector = document.getElementById('modeSelector');
const stats = document.getElementById('stats');
const quizCard = document.getElementById('quizCard');
const jsonFileInput = document.getElementById('jsonFile');
// Sequential 방식에서는 이미지 폴더 업로드 불필요

// 모드 버튼들
const modeButtons = document.querySelectorAll('.mode-btn');

// 문제 표시 요소들
const questionNumber = document.getElementById('questionNumber');
const progress = document.getElementById('progress');
const questionContent = document.getElementById('questionContent');
const questionImages = document.getElementById('questionImages');
const answerSection = document.getElementById('answerSection');
const answerContent = document.getElementById('answerContent');
const answerImages = document.getElementById('answerImages');

// 이미지 모달 요소들
const imageModal = document.getElementById('imageModal');
const modalImage = document.getElementById('modalImage');
const modalClose = document.getElementById('modalClose');

// 컨트롤 버튼들
const showAnswerBtn = document.getElementById('showAnswerBtn');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const randomBtn = document.getElementById('randomBtn');

// 통계 요소들
const totalCount = document.getElementById('totalCount');
const currentIndexSpan = document.getElementById('currentIndex');
const currentModeSpan = document.getElementById('currentMode');

// 이벤트 리스너들
document.addEventListener('DOMContentLoaded', function() {
    jsonFileInput.addEventListener('change', handleFileUpload);
    // Sequential 방식에서는 이미지 폴더 이벤트 불필요
    
    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => switchMode(btn.dataset.mode));
    });

    showAnswerBtn.addEventListener('click', toggleAnswer);
    prevBtn.addEventListener('click', () => navigateQuestion(-1));
    nextBtn.addEventListener('click', () => navigateQuestion(1));
    randomBtn.addEventListener('click', showRandomQuestion);

    // 이미지 모달 이벤트
    modalClose.addEventListener('click', closeImageModal);
    imageModal.addEventListener('click', function(e) {
        if (e.target === imageModal) {
            closeImageModal();
        }
    });

    // 키보드 단축키
    document.addEventListener('keydown', handleKeyboard);
});

// 파일 업로드 처리
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const uploadStatus = document.getElementById('uploadStatus');

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            questionsData = JSON.parse(e.target.result);
            if (Array.isArray(questionsData) && questionsData.length > 0) {
                console.log('Sequential JSON 파일 로드 완료:', questionsData.length + '개 문제');
                
                // 이미지가 있는 문제 확인
                const imageQuestions = questionsData.filter(q => q.has_images);
                
                if (imageQuestions.length > 0) {
                    uploadStatus.innerHTML = `
                        ✅ Sequential 방식 파일 로드 완료!<br>
                        📦 이미지 ${imageQuestions.length}개 문제, base64 인코딩으로 포함됨
                    `;
                } else {
                    uploadStatus.innerHTML = `
                        ✅ JSON 파일 로드 완료!<br>
                        📄 텍스트 전용 문제 ${questionsData.length}개
                    `;
                }
                
                initializeApp();
            } else {
                alert('올바른 JSON 형식이 아닙니다.');
            }
        } catch (error) {
            alert('JSON 파일을 읽는 중 오류가 발생했습니다: ' + error.message);
        }
    };
    reader.readAsText(file);
}

// Sequential 방식에서는 JSON 파일만으로 모든 데이터가 포함되므로 별도 함수 불필요

// 앱 초기화
function initializeApp() {
    // 문제 번호 순으로 정렬
    questionsData.sort((a, b) => a.question_no - b.question_no);
    
    // 랜덤 인덱스 배열 생성
    shuffledIndices = Array.from({length: questionsData.length}, (_, i) => i);
    shuffleArray(shuffledIndices);

    // UI 표시
    fileUpload.style.display = 'none';
    modeSelector.style.display = 'flex';
    stats.style.display = 'block';
    quizCard.style.display = 'block';

    // 통계 업데이트
    totalCount.textContent = questionsData.length;
    
    // 첫 번째 문제 표시
    currentIndex = 0;
    showCurrentQuestion();
}

// 모드 전환
function switchMode(mode) {
    currentMode = mode;
    currentIndex = 0;

    // 버튼 스타일 업데이트
    modeButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // 랜덤 버튼 표시/숨김
    randomBtn.style.display = mode === 'exam' ? 'inline-flex' : 'none';
    
    // 모드 표시 업데이트
    currentModeSpan.textContent = mode === 'basic' ? '기본' : '시험';

    showCurrentQuestion();
}

// 현재 문제 표시
function showCurrentQuestion() {
    if (questionsData.length === 0) return;

    const questionIndex = currentMode === 'basic' ? currentIndex : shuffledIndices[currentIndex];
    const question = questionsData[questionIndex];

    // 문제 정보 업데이트
    let questionNumberText = `문제 ${question.question_no}`;
    if (question.has_images) {
        questionNumberText += `<span class="image-indicator">🖼️ 이미지 포함</span>`;
    }
    questionNumber.innerHTML = questionNumberText;
    
    progress.textContent = `${currentIndex + 1} / ${questionsData.length}`;

    // Question 텍스트와 이미지 표시
    questionContent.textContent = question.question;
    displayQuestionImages(question);

    // Answer 내용 설정 (표시는 나중에)
    answerContent.textContent = question.answer;

    // 답변 섹션 숨김 및 Answer 이미지 초기화
    answerSection.classList.remove('visible');
    showAnswerBtn.textContent = '💡 답변 보기';
    answerImages.innerHTML = ''; // Answer 이미지 컨테이너 비우기

    // 네비게이션 버튼 상태 업데이트
    prevBtn.disabled = currentIndex === 0;
    nextBtn.disabled = currentIndex === questionsData.length - 1;

    // 통계 업데이트
    currentIndexSpan.textContent = currentIndex + 1;

    // 카드 애니메이션
    quizCard.style.animation = 'none';
    setTimeout(() => {
        quizCard.style.animation = 'fadeIn 0.5s ease';
    }, 10);
}

// Question 이미지만 표시하는 함수
function displayQuestionImages(question) {
    questionImages.innerHTML = ''; // 기존 이미지 제거

    if (!question.has_images || !question.images || question.images.length === 0) {
        return; // 이미지가 없으면 종료
    }

    // Sequential 방식: Question 이미지만 필터링
    const questionImageData = question.images.filter(img => img.type === 'question');
    console.log(`문제 ${question.question_no} - Question 이미지:`, questionImageData.length + '개');

    questionImageData.forEach((imageData, index) => {
        const imageContainer = document.createElement('div');
        imageContainer.className = 'image-container';

        const img = document.createElement('img');
        img.className = 'question-image';
        img.src = `data:image/${imageData.format || 'png'};base64,${imageData.base64}`;
        img.alt = `문제 ${question.question_no} - Question 이미지 ${index + 1}`;
        
        // 이미지 클릭 시 모달로 확대
        img.addEventListener('click', () => openImageModal(img.src, img.alt));

        const caption = document.createElement('div');
        caption.className = 'image-caption';
        caption.textContent = `Question 이미지 ${index + 1}`;

        imageContainer.appendChild(img);
        imageContainer.appendChild(caption);
        questionImages.appendChild(imageContainer);
    });
}

// Answer 이미지만 표시하는 함수
function displayAnswerImages(question) {
    answerImages.innerHTML = ''; // 기존 이미지 제거

    if (!question.has_images || !question.images || question.images.length === 0) {
        return; // 이미지가 없으면 종료
    }

    // Sequential 방식: Answer 이미지만 필터링
    const answerImageData = question.images.filter(img => img.type === 'answer');
    console.log(`문제 ${question.question_no} - Answer 이미지:`, answerImageData.length + '개');

    answerImageData.forEach((imageData, index) => {
        const imageContainer = document.createElement('div');
        imageContainer.className = 'image-container';

        const img = document.createElement('img');
        img.className = 'answer-image';
        img.src = `data:image/${imageData.format || 'png'};base64,${imageData.base64}`;
        img.alt = `문제 ${question.question_no} - Answer 이미지 ${index + 1}`;
        
        // 이미지 클릭 시 모달로 확대
        img.addEventListener('click', () => openImageModal(img.src, img.alt));

        const caption = document.createElement('div');
        caption.className = 'image-caption';
        caption.textContent = `Answer 이미지 ${index + 1}`;

        imageContainer.appendChild(img);
        imageContainer.appendChild(caption);
        answerImages.appendChild(imageContainer);
    });
}

// 이미지 오류 요소 생성
function createImageErrorElement(container, filename) {
    const errorContainer = document.createElement('div');
    errorContainer.className = 'image-container';
    errorContainer.style.border = '2px dashed #ff6b6b';
    errorContainer.style.padding = '1rem';
    errorContainer.style.textAlign = 'center';
    errorContainer.style.color = '#ff6b6b';
    errorContainer.innerHTML = `
        <div>❌ 이미지를 찾을 수 없습니다</div>
        <div style="font-size: 0.8rem; margin-top: 0.5rem;">${filename}</div>
    `;
    container.appendChild(errorContainer);
}

// 답변 토글
function toggleAnswer() {
    const isVisible = answerSection.classList.contains('visible');
    
    if (isVisible) {
        // 답변 숨기기
        answerSection.classList.remove('visible');
        showAnswerBtn.textContent = '💡 답변 보기';
        answerImages.innerHTML = ''; // Answer 이미지 제거
        console.log('답변 숨김 - Answer 이미지 제거됨');
    } else {
        // 답변 보기
        answerSection.classList.add('visible');
        showAnswerBtn.textContent = '🙈 답변 숨기기';
        
        // Answer 이미지 표시
        const questionIndex = currentMode === 'basic' ? currentIndex : shuffledIndices[currentIndex];
        const question = questionsData[questionIndex];
        displayAnswerImages(question);
        console.log('답변 표시 - Answer 이미지 로드됨');
    }
}

// 이미지 모달 열기 (전역 함수로 만들어서 HTML에서 호출 가능)
window.openImageModal = function(imageSrc, imageAlt) {
    modalImage.src = imageSrc;
    modalImage.alt = imageAlt;
    imageModal.classList.add('active');
    document.body.style.overflow = 'hidden'; // 스크롤 방지
}

// 이미지 모달 닫기
function closeImageModal() {
    imageModal.classList.remove('active');
    document.body.style.overflow = 'auto'; // 스크롤 복원
}

// 문제 네비게이션
function navigateQuestion(direction) {
    const newIndex = currentIndex + direction;
    
    if (newIndex >= 0 && newIndex < questionsData.length) {
        currentIndex = newIndex;
        showCurrentQuestion();
    }
}

// 랜덤 문제 표시
function showRandomQuestion() {
    currentIndex = Math.floor(Math.random() * questionsData.length);
    showCurrentQuestion();
}

// 배열 셔플
function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

// 키보드 단축키
function handleKeyboard(event) {
    if (questionsData.length === 0) return;

    switch(event.key) {
        case 'ArrowLeft':
            event.preventDefault();
            if (!prevBtn.disabled) navigateQuestion(-1);
            break;
        case 'ArrowRight':
            event.preventDefault();
            if (!nextBtn.disabled) navigateQuestion(1);
            break;
        case ' ':
            event.preventDefault();
            toggleAnswer();
            break;
        case 'r':
        case 'R':
            if (currentMode === 'exam') {
                event.preventDefault();
                showRandomQuestion();
            }
            break;
        case 'Escape':
            if (imageModal.classList.contains('active')) {
                event.preventDefault();
                closeImageModal();
            }
            break;
    }
}

// 유틸리티 함수들
function debugLog(message, data) {
    console.log(`[CKA Quiz] ${message}`, data || '');
}

// 개발자 도구용 전역 함수들 (디버깅용)
window.CKA_DEBUG = {
    questionsData,
    currentQuestion: () => questionsData[currentMode === 'basic' ? currentIndex : shuffledIndices[currentIndex]],
    showDebugInfo: () => {
        if (questionsData.length > 0) {
            const imageQuestions = questionsData.filter(q => q.has_images);
            debugLog('총 문제 수:', questionsData.length);
            debugLog('이미지 포함 문제:', imageQuestions.length);
            
            if (imageQuestions.length > 0) {
                const firstImageQuestion = imageQuestions[0];
                const questionImages = firstImageQuestion.images.filter(img => img.type === 'question');
                const answerImages = firstImageQuestion.images.filter(img => img.type === 'answer');
                
                debugLog('첫 번째 이미지 문제 (Sequential 방식):', {
                    question_no: firstImageQuestion.question_no,
                    total_images: firstImageQuestion.images.length,
                    question_images: questionImages.length + '개',
                    answer_images: answerImages.length + '개',
                    format: 'base64 embedded'
                });
            }
        }
    },
    testImageMapping: () => {
        const current = window.CKA_DEBUG.currentQuestion();
        if (current && current.has_images) {
            console.log('=== 현재 문제 이미지 분석 ===');
            console.log('문제 번호:', current.question_no);
            console.log('전체 이미지:', current.images);
            console.log('Question 이미지:', current.images.filter(img => img.type === 'question'));
            console.log('Answer 이미지:', current.images.filter(img => img.type === 'answer'));
        } else {
            console.log('현재 문제에는 이미지가 없습니다.');
        }
    },
    forceShowQuestionImages: () => {
        const current = window.CKA_DEBUG.currentQuestion();
        if (current) {
            console.log('Question 이미지 강제 표시 테스트');
            displayQuestionImages(current);
        }
    },
    forceShowAnswerImages: () => {
        const current = window.CKA_DEBUG.currentQuestion();
        if (current) {
            console.log('Answer 이미지 강제 표시 테스트');
            displayAnswerImages(current);
        }
    }
};
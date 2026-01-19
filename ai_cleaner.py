import google.generativeai as genai
import time
import math

# [STEP 2] AI 정제 모듈
# 이 모듈은 Google Gemini API를 사용하여 텍스트의 맥락을 파악하고 정제합니다.
# 주요 역할:
# 1. '속사포 랩' 현상 해결 (문단 분리, 띄어쓰기 복구)
# 2. 페이지 번호 및 헤더를 삭제하지 않고 '태그'로 표시 (<<<DELETE: ...>>>)

def clean_text_with_ai(text, api_key, progress_callback=None):
    """
    Google Gemini API를 사용하여 텍스트를 청크(조각) 단위로 나누어 정제합니다.
    
    Args:
        text (str): 원본 텍스트 내용.
        api_key (str): 사용자의 Gemini API 키.
        progress_callback (func): 진행률을 보고하기 위한 함수 (0.0 ~ 1.0).
        
    Returns:
        str: 정제된 텍스트 전체.
    """
    # [설정] API 키 등록
    genai.configure(api_key=api_key)
    
    # [설정] 생성 모델 파라미터
    # temperature: 0.2로 낮게 설정하여 창의성을 억제하고 원문에 충실하게 만듭니다.
    generation_config = {
        "temperature": 0.2, 
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    
    # [프롬프트] AI에게 내리는 지침
    # 핵심 전략: 무조건 삭제하기보다 '태그'를 달게 하여, 후처리에서 안전하게 삭제하도록 유도합니다.
    system_instruction = """당신은 전문 전자책 편집자입니다. OCR로 스캔된 원고를 EPUB 변환용으로 교정해야 합니다.

[작업 목표]
텍스트의 흐름과 맥락을 완벽하게 파악하여 다음 두 가지 문제를 해결하십시오.

1. **'속사포 랩' 현상 해결 (최우선)**
   - 스캔 과정에서 문단(Paragraph) 구분과 띄어쓰기가 사라진 부분을 복구하십시오.
   - 문맥상 문단이 나뉘어야 할 곳에서 정확히 줄바꿈을 하십시오.
   - 대화문이나 인용구의 줄바꿈과 들여쓰기를 원본 책의 느낌으로 살리십시오.

2. **페이지 번호 및 헤더 '태그' 처리 (삭제 금지)**
   - **중요**: 페이지 번호, 장 제목(Header/Footer) 등 본문이 아닌 요소를 **절대 직접 삭제하지 마십시오**.
   - 대신, 해당 요소를 `<<<DELETE: ... >>>` 태그로 감싸십시오.
   - 예시:
     - 원본: "...집으로 돌아갔다. 15 페이지 제1장 시작 ..."
     - 변경: "...집으로 돌아갔다. <<<DELETE: 15 페이지 제1장 시작>>> ..."
   - 이렇게 해야 본문 내용이 실수로 삭제되는 것을 막을 수 있습니다.

[출력 형식]
- 정제된 텍스트만 출력하십시오.
- 마크다운 코드 블록(```)을 사용하지 마십시오.
"""

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite", 
        generation_config=generation_config,
        system_instruction=system_instruction
    )
    
    try:
        if progress_callback:
            progress_callback(0.1) # [진행상황] 준비 완료
            
        # [STEP 2-1] 청크 분할 (Chunking)
        # 매우 긴 텍스트를 한 번에 보내면 AI의 출력 토큰 제한(약 8192 토큰)에 걸려 뒷부분이 잘립니다.
        # 따라서 안전하게 약 10,000자~15,000자 단위로 잘라서 처리합니다.
        
        chunk_size = 12000 # 한 번에 처리할 글자 수 (토큰 수 고려하여 안전하게 설정)
        input_chunks = []
        
        # 텍스트를 줄 단위로 읽으며 청크를 만듭니다. (문장 중간이 잘리는 것 방지)
        lines = text.splitlines()
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_len = len(line) + 1 # 개행 문자 포함
            if current_length + line_len > chunk_size:
                # 현재 청크가 꽉 찼으면 저장하고 초기화
                input_chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(line)
            current_length += line_len
            
        if current_chunk: # 남은 내용 저장
            input_chunks.append("\n".join(current_chunk))
            
        total_chunks = len(input_chunks)
        cleaned_chunks = []
        
        # [STEP 2-2] 청크별 순차 처리
        for i, chunk in enumerate(input_chunks):
            if not chunk.strip():
                continue
            
            # [API 호출] AI에게 변환 요청
            # 잦은 요청 시 오류가 발생할 수 있으므로 간단한 재시도 로직을 포함하면 좋겠지만, 
            # 여기서는 기본 호출을 수행합니다.
            response = model.generate_content(chunk)
            
            result_text = response.text
            cleaned_chunks.append(result_text)
            
            # [진행상황] 진행률 업데이트
            if progress_callback:
                # AI 처리는 전체 공정의 10% ~ 80%를 차지한다고 가정
                current_progress = 0.1 + (0.7 * (i + 1) / total_chunks)
                progress_callback(current_progress)
                
            # [속도 조절] API 제한 방지 (1초 대기)
            time.sleep(1)

        # [STEP 2-3] 결과 병합
        return "\n\n".join(cleaned_chunks)

    except Exception as e:
        # 에러 발생 시 사용자에게 알리기 위해 상위로 전파
        raise Exception(f"AI 처리 중 오류 발생: {str(e)}")

import re

# [STEP 4] 문단 병합 모듈
# 줄바꿈(Hard Wrap)으로 끊어진 문장을 하나의 문단으로 합칩니다.
# AI 모드 사용 시 이 로직은 보조적으로 사용되거나, AI가 이를 대신 수행할 수 있습니다.

def merge_paragraphs(text):
    """
    불필요하게 끊어진 줄을 병합하되, 빈 줄로 구분된 문단 구조는 보존합니다.
    
    Args:
        text (str): 정제된 텍스트.
        
    Returns:
        str: 문단 단위로 병합된 텍스트.
    """
    lines = text.splitlines()
    paragraphs = []
    current_paragraph_lines = []
    
    # [휴리스틱] 빈 줄이 있는지 확인
    # 만약 원본 파일에 빈 줄이 자주 보인다면, 빈 줄을 문단 구분자로 신뢰할 수 있습니다.
    has_blank_lines = any(not line.strip() for line in lines[:100])
    
    for line in lines:
        unique_line = line.strip()
        
        if not unique_line:
            # 빈 줄을 만남 -> 무조건 문단 끝으로 처리
            if current_paragraph_lines:
                paragraphs.append(" ".join(current_paragraph_lines))
                current_paragraph_lines = []
            continue

        # 현재 모으고 있는 문단 내용이 있다면, 병합할지 끊을지 결정
        if current_paragraph_lines:
            last_line = current_paragraph_lines[-1]
            
            # 문장 종료 부호 확인 (. ! ? " ”)
            terminators = ('.', '!', '?', '"', '”', '’', "'")
            is_terminated = last_line.endswith(terminators)
            
            # [조건 분기]
            if has_blank_lines:
                # 파일이 빈 줄로 문단을 잘 구분하고 있다면, 
                # 인접한 줄은 같은 문단이 잘린 것(Hard Wrap)으로 간주하고 무조건 합칩니다.
                pass
            else:
                # 빈 줄이 거의 없는 빡빡한 텍스트인 경우
                # 앞 문장이 마침표로 끝났다면 새로운 문단으로 간주하고 끊습니다.
                if is_terminated:
                    paragraphs.append(" ".join(current_paragraph_lines))
                    current_paragraph_lines = []
        
        current_paragraph_lines.append(unique_line)
            
    # 마지막 남은 문단 처리
    if current_paragraph_lines:
        paragraphs.append(" ".join(current_paragraph_lines))
        
    # 최종적으로 문단 사이를 두 줄 띄워 반환 (\n\n)
    return "\n\n".join(paragraphs)

import re

# [STEP 3] 텍스트 후처리 모듈
# AI가 처리한 결과물에서 태그된 삭제 대상(`<<<DELETE: ... >>>`)을 제거하고,
# 추가적인 규칙 기반 정제를 수행합니다.

def remove_tagged_content(text):
    """
    AI가 '삭제 대상'으로 태그한 부분을 실제로 제거합니다.
    태그 형식: <<<DELETE: 내용 >>>
    """
    # [정규식 설명]
    # <<<DELETE: : 시작 태그
    # (.*?)       : 삭제할 내용 (최소 매칭)
    # >>>        : 종료 태그
    # re.DOTALL  : 줄바꿈이 포함된 내용도 매칭
    pattern = re.compile(r'<<<DELETE:(.*?)>>>', re.DOTALL)
    
    # 태그된 부분을 빈 문자열로 대체 (삭제)
    cleaned_text = pattern.sub('', text)
    return cleaned_text

def clean_structure(text):
    """
    구조적 정제: 페이지 번호와 반복되는 머리말/꼬리말을 규칙 기반으로 제거합니다.
    (AI 사용 안 함 옵션 선택 시 또는 보조적으로 사용)
    """
    lines = text.splitlines()
    
    # [정규식] 페이지 번호 패턴 (숫자, - 숫자 -, [숫자])
    page_num_pattern = re.compile(r'^[\s\-]*\[?\d+\]?[\s\-]*$')
    
    # 1. 페이지 번호 위치 파악
    page_indices = []
    for i, line in enumerate(lines):
        if page_num_pattern.match(line):
            page_indices.append(i)
            
    # 2. 이웃 라인 분석 (머리말/꼬리말 찾기)
    # 페이지 번호 앞뒤에 반복적으로 나타나는 문구를 찾습니다.
    neighbor_counts = {}
    
    for idx in page_indices:
        # 윗줄 확인
        if idx > 0:
            prev_line = lines[idx-1].strip()
            if prev_line and len(prev_line) < 100: # 너무 긴 줄은 헤더가 아님
                 neighbor_counts[prev_line] = neighbor_counts.get(prev_line, 0) + 1
                 
        # 아랫줄 확인
        if idx < len(lines) - 1:
            next_line = lines[idx+1].strip()
            if next_line and len(next_line) < 100:
                neighbor_counts[next_line] = neighbor_counts.get(next_line, 0) + 1
                
    # [기준] 3회 이상 페이지 번호 근처에서 발견되면 노이즈(헤더/푸터)로 간주
    repeating_headers = {content for content, count in neighbor_counts.items() if count >= 3}
    
    # 3. 필터링 (삭제 수행)
    final_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 페이지 번호 삭제
        if page_num_pattern.match(line):
            continue
            
        # 반복 헤더 삭제
        if stripped in repeating_headers:
            continue
            
        # (옵션) 단순 숫자만 있는 줄 삭제 (안전망)
        if stripped.isdigit():
            continue
            
        final_lines.append(line)
        
    return "\n".join(final_lines)

def sophisticated_clean(text, known_chapter_titles=None):
    """
    [실험적] 챕터 제목 목록을 알고 있을 때, 이를 이용해 헤더를 더 정교하게 제거합니다.
    """
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        
        # 순수 숫자 삭제
        if re.match(r'^[\s\-]*\d+[\s\-]*$', stripped):
            continue
            
        # 알려진 챕터 제목이 포함된 짧은 줄은 헤더일 가능성 높음
        is_header = False
        if known_chapter_titles:
            for title in known_chapter_titles:
                if title in stripped and any(c.isdigit() for c in stripped):
                    if len(stripped) < len(title) + 10:
                        is_header = True
                        break
        
        if not is_header:
            cleaned.append(line)
            
    return "\n".join(cleaned)


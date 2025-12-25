import re

def clean_structure(text):
    """
    Cleans the text by removing page numbers and recurring headers/footers.
    
    Args:
        text (str): Raw text content.
        
    Returns:
        str: Cleaned text.
    """
    lines = text.splitlines()
    
    # regex for page numbers (digits, or "- digits -", or "[digits]")
    page_num_pattern = re.compile(r'^[\s\-]*\[?\d+\]?[\s\-]*$')
    
    # 1. Identify Page Number Indices and Candidate Headers
    page_indices = []
    for i, line in enumerate(lines):
        if page_num_pattern.match(line):
            page_indices.append(i)
            
    # 2. Analyze Neighbors (Predecessors and Successors)
    # We look at lines immediately before and after page numbers.
    # If the same line content appears frequently next to page numbers, it's likely a header/footer.
    
    neighbor_counts = {}
    
    for idx in page_indices:
        # Check line Before
        if idx > 0:
            prev_line = lines[idx-1].strip()
            if prev_line and len(prev_line) < 100: # Headers are usually short
                 neighbor_counts[prev_line] = neighbor_counts.get(prev_line, 0) + 1
                 
        # Check line After
        if idx < len(lines) - 1:
            next_line = lines[idx+1].strip()
            if next_line and len(next_line) < 100:
                neighbor_counts[next_line] = neighbor_counts.get(next_line, 0) + 1
                
    # Threshold for deciding a line is a header.
    # If a line appears more than 3 times next to a page number, we assume it's noise.
    # (Adjustable, but 3 is a safe low number for a book)
    repeating_headers = {content for content, count in neighbor_counts.items() if count >= 3}
    
    # 3. Filtering Pass
    final_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip pure page numbers
        if page_num_pattern.match(line):
            continue
            
        # Skip identified repeating headers
        if stripped in repeating_headers:
            continue
            
        # Optional: Skip pure digits even if logic missed them (safety net)
        if stripped.isdigit():
            continue
            
        final_lines.append(line)
        
    return "\n".join(final_lines)

def sophisticated_clean(text, known_chapter_titles=None):
    """
    Experimental cleaner that uses known chapter titles to remove headers.
    """
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        
        # Pure numbers
        if re.match(r'^[\s\-]*\d+[\s\-]*$', stripped):
            continue
            
        # Check if line contains a known chapter title AND a number, and is short
        is_header = False
        if known_chapter_titles:
            for title in known_chapter_titles:
                if title in stripped and any(c.isdigit() for c in stripped):
                    if len(stripped) < len(title) + 10: # Heuristic: title + page number + minimal extra
                        is_header = True
                        break
        
        if not is_header:
            cleaned.append(line)
            
    return "\n".join(cleaned)

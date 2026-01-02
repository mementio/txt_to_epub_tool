
import re


TERMINATORS = ('.', '!', '?', '"', '”', '’', "'", '。', '！', '？')


def is_short_heading(line, max_length=20):
    clean = line.strip()
    if not clean:
        return False
    if len(clean) > max_length:
        return False
    if clean.endswith(TERMINATORS):
        return False
    return True


def is_heading_candidate(line):
    clean = line.strip()
    if not clean:
        return False
    if len(clean) > 60:
        return False
    if clean.endswith(TERMINATORS):
        return False
    if len(clean.split()) > 12:
        return False
    return True

def merge_paragraphs(text):
    """
    Merges lines that are unnecessarily broken, while preserving actual paragraph structure
    denoted by distinct blank lines.
    
    Args:
        text (str): Pre-cleaned text.
        
    Returns:
        str: Text with paragraphs merged.
    """
    lines = text.splitlines()
    paragraphs = []
    current_paragraph_lines = []
    
    # Heuristic: Check if the file has blank lines.
    # If a file has frequent blank lines, we should respect them as paragraph separators.
    # If not, we rely on punctuation/indentation.
    has_blank_lines = any(not line.strip() for line in lines[:100]) # Check first 100 lines
    
    for line in lines:
        unique_line = line.strip()
        
        if not unique_line:
            # Blank line detected. This is ALWAYS a paragraph break.
            if current_paragraph_lines:
                paragraphs.append(" ".join(current_paragraph_lines))
                current_paragraph_lines = []
            continue
        
        if is_short_heading(unique_line):
            if current_paragraph_lines:
                paragraphs.append(" ".join(current_paragraph_lines))
                current_paragraph_lines = []
            paragraphs.append(unique_line)
            continue

        # If we have current content, decide if we should merge or flush
        if current_paragraph_lines:
            last_line = current_paragraph_lines[-1]
            
            # Decision to flush (start new paragraph):
            # 1. If we are in "no blank lines" mode, we look for punctuation.
            # 2. If the new line starts with an indent (conceptually, though strip() removed it, 
            #    we might need original line context? For now, assume strip() is okay but maybe we check punctuation).
            
            # Simple Punctuation Heuristic:
            # If the PREVIOUS line ended with a sentence terminator (. ! ? " ”), 
            # AND the current line starts with a Capital or Number or Quote,
            # treat it as a new paragraph.
            
            # Common sentence terminators in English and Korean
            terminators = ('.', '!', '?', '"', '”', '’', "'")
            
            is_terminated = last_line.endswith(terminators)
            
            # Special case: If the file DOES contain blank lines, we assume they are the primary separator.
            # In that case, we ONLY merge (because non-blank lines are part of the same block).
            # BUT, the user complained about "joining lines that are not breaks".
            # This implies the user wants to join HARD WRAPS but keep PARAGRAPHS.
            
            if has_blank_lines:
                # If the file uses blank lines for paragraphs, then adjacent lines are part of the same paragraph (hard wrap).
                # So we continue merging.
                pass
            else:
                # File has NO (or few) blank lines. Every line might be a paragraph OR a wrap.
                # Heuristic: Break if valid terminator found.
                if is_terminated:
                    paragraphs.append(" ".join(current_paragraph_lines))
                    current_paragraph_lines = []
        
        current_paragraph_lines.append(unique_line)
            
    # Flush last paragraph
    if current_paragraph_lines:
        paragraphs.append(" ".join(current_paragraph_lines))
        
    # Join paragraphs with double newline to signify standard text format
    return "\n\n".join(paragraphs)

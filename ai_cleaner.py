import google.generativeai as genai
import time

def clean_text_with_ai(text, api_key, progress_callback=None):
    """
    Cleans text using Google Gemini API.
    
    Args:
        text (str): Raw text content.
        api_key (str): User's Gemini API Key.
        progress_callback (func): Optional callback to report progress (0.0 to 1.0).
        
    Returns:
        str: Cleaned and formatted text.
    """
    genai.configure(api_key=api_key)
    
    # Configuration
    generation_config = {
        "temperature": 0.2, # Low temperature for more deterministic/faithful cleanup
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        generation_config=generation_config,
        system_instruction="""You are an expert ebook editor. Your task is to clean raw text extracted from a file (e.g., PDF or OCR scan) for conversion into an EPUB.
        
Instructions:
1. **Remove Noise**: Identify and remove all page numbers, running headers (book titles, chapter titles repeated at top/bottom of pages), and footers.
   - **CRITICAL**: Be extremely careful of headers/footers that appear in the middle of sentences due to page breaks.
   - Example Input: "The quick brown fox jumps over the 10. The Fox and Hound lazy dog."
   - Example Output: "The quick brown fox jumps over the lazy dog."
   - **User Specific Example**: Remove recurring lines like "1장 왜 우리는 수학을 공부하는가" if they interrupt the text flow.
2. **Merge Paragraphs**: Join lines that are hard-wrapped but belong to the same paragraph.
3. **Preserve Structure**: Keep actual paragraph breaks (blank lines).
4. **Format Headers**: If you identify a structural chapter START (not a running header), format it as "## Chapter Name".
5. **Output**: Return ONLY the cleaned text content. No markdown code blocks.
"""
    )
    
    # Basic chunking strategy
    # Gemini 1.5 Flash has a large context window (1M tokens), so we can theoretically pass the whole book.
    # However, for safety and response time, let's chunk if it's massive, or just try sending it all if it's reasonable.
    # For a typical book (100k words), 1.5 Flash can handle it in one go.
    # Let's try a single pass first, but wrap in try/catch.
    
    try:
        if progress_callback:
            progress_callback(0.2)
            
        # If text is extremely huge, we might want to split. 
        # But let's assume < 500,000 characters for now for this tool's scope.
        # If > 500k chars, we might hit output token limits if we ask for full rewrite?
        # Actually output limit is often 8192 tokens per response block in some APIs, 
        # so chunking IS required for outputting a whole book.
        
        # Chunking Strategy:
        # Split by double newlines or roughly every 10,000 characters to be safe for output limits.
        chunk_size = 15000 
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
            
        cleaned_chunks = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            # Overlap context slightly? No, simple chunking for now to avoid duplication issues.
            # Ideally we split on paragraph boundaries.
            
            # Refined split: find last newline
            # (Skipping complex split logic for MVP, assuming simple char chunking is okay-ish 
            # if we warn user, but let's try to be safer: split by \n)
            pass 

        # Better Splitting:
        lines = text.splitlines()
        current_chunk = []
        current_length = 0
        safe_chunks = []
        
        for line in lines:
            if current_length + len(line) > 10000:
                safe_chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(line)
            current_length += len(line) + 1
            
        if current_chunk:
            safe_chunks.append("\n".join(current_chunk))
            
        total_safe_chunks = len(safe_chunks)
        
        for i, chunk_text in enumerate(safe_chunks):
            if not chunk_text.strip():
                continue
                
            response = model.generate_content(chunk_text)
            cleaned_chunks.append(response.text)
            
            if progress_callback:
                # Map progress from 0.2 to 0.9
                prog = 0.2 + (0.7 * (i + 1) / total_safe_chunks)
                progress_callback(prog)
                
            # Rate limit guard
            time.sleep(1) 

        return "\n\n".join(cleaned_chunks)

    except Exception as e:
        raise Exception(f"AI Processing Error: {str(e)}")

"""
Enhanced chunking with better pattern matching and error handling.
"""
import re
from typing import List, Dict

def chunk_pageText(full_text: str) -> List[Dict[str, str]]:
    """
    Enhanced chunking that handles various numbering patterns and document structures.
    """
    if not full_text or not full_text.strip():
        return []
    
    chunks = []
    
    # Multiple patterns for different document types
    patterns = [
        # Standard numbered sections (1., 1.1., 1.1.1.)
        r'(?P<header>\d+(?:\.\d+)*\.)\s+',
        # Letter sections (A., B., etc.)
        r'(?P<header>[A-Z]\.)\s+',
        # Roman numerals (I., II., III.)
        r'(?P<header>[IVX]+\.)\s+',
        # Clause patterns
        r'(?P<header>Clause\s+\d+(?:\.\d+)*[:\.])\s+',
        # Article patterns
        r'(?P<header>Article\s+\d+[:\.])\s+',
    ]
    
    best_matches = []
    best_pattern = None
    
    # Find the pattern that gives the most matches
    for pattern in patterns:
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        if len(matches) > len(best_matches):
            best_matches = matches
            best_pattern = pattern
    
    if not best_matches:
        # If no pattern matches, create chunks by paragraphs
        paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs):
            if len(para) > 50:  # Only include substantial paragraphs
                chunks.append({
                    "section_number": f"para_{i+1}",
                    "text": para
                })
        return chunks
    
    # Process matches
    for i in range(len(best_matches)):
        start = best_matches[i].start()
        end = best_matches[i + 1].start() if i + 1 < len(best_matches) else len(full_text)
        
        section_number = best_matches[i].group("header").strip(".:").strip()
        chunk_text = full_text[start:end].strip()
        
        # Only include chunks with substantial content
        if len(chunk_text) > 30:
            # Clean up the chunk text
            chunk_text = re.sub(r'\n+', '\n', chunk_text)  # Normalize newlines
            chunk_text = re.sub(r'\s+', ' ', chunk_text)   # Normalize spaces
            
            chunks.append({
                "section_number": section_number,
                "text": chunk_text
            })
    
    return chunks
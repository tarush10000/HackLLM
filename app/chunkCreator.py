import re
from typing import List, Dict

def chunk_pageText(full_text: str) -> List[Dict[str, str]]:
    """
    Relaxed chunking: fewer, broader chunks by only using high-level headers and paragraph fallback.
    """
    if not full_text or not full_text.strip():
        return []

    chunks = []

    # Relaxed: only chunk on major headers
    relaxed_patterns = [
        r'(?P<header>\n?\s*\d+\.)\s+',                  # 1., 2.
        r'(?P<header>\n?\s*[A-Z]\.)\s+',                # A., B.
        r'(?P<header>\n?\s*Article\s+\d+[:\.])\s+',     # Article 1:
    ]

    best_matches = []
    best_pattern = None

    for pattern in relaxed_patterns:
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        if len(matches) > len(best_matches):
            best_matches = matches
            best_pattern = pattern

    if not best_matches:
        # Fallback to paragraph-based chunking with larger threshold
        paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
        temp_chunk = ""
        for para in paragraphs:
            if len(temp_chunk) + len(para) < 800:
                temp_chunk += " " + para
            else:
                if temp_chunk.strip():
                    chunks.append({
                        "section_number": f"chunk_{len(chunks)+1}",
                        "text": temp_chunk.strip()
                    })
                temp_chunk = para
        if temp_chunk.strip():
            chunks.append({
                "section_number": f"chunk_{len(chunks)+1}",
                "text": temp_chunk.strip()
            })
        return chunks

    # Process using matched headers
    for i in range(len(best_matches)):
        start = best_matches[i].start()
        end = best_matches[i + 1].start() if i + 1 < len(best_matches) else len(full_text)

        section_number = best_matches[i].group("header").strip(".:").strip()
        chunk_text = full_text[start:end].strip()

        if len(chunk_text) > 100:  # Increased content threshold
            chunk_text = re.sub(r'\n+', '\n', chunk_text)
            chunk_text = re.sub(r'\s+', ' ', chunk_text)

            chunks.append({
                "section_number": section_number,
                "text": chunk_text
            })

    return chunks


import re
import csv

def chunk_pageText(full_text):
    pattern = re.compile(r'(?P<header>\d+(\.\d+)*\.)\s+')
    matches = list(pattern.finditer(full_text))
    chunks = []

    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        section_number = matches[i].group("header").strip(".")
        chunk_text = full_text[start:end].strip()
        if len(chunk_text) > 30:
            chunks.append({
                "section_number": section_number,
                "text": chunk_text
            })

    return chunks

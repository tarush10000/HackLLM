"""
Complete utility functions for hashing, chunking, and text cleaning.
"""
import hashlib
import re
from typing import List

def hash_pdf_metadata(file_name: str, file_size: int, first_words: str) -> str:
    """Create a unique hash for document deduplication"""
    combined = f"{file_name}_{file_size}_{first_words}"
    return hashlib.md5(combined.encode()).hexdigest()

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep important punctuation
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', ' ', text)
    
    # Fix common OCR issues
    text = text.replace('|', 'l')  # Common OCR error
    text = text.replace('0', 'O')  # In specific contexts
    
    return text.strip()

def chunk_text(text: str, strategy="paragraph", chunk_size=500, overlap=50) -> List[str]:
    """Advanced text chunking with multiple strategies"""
    if not text:
        return []
    
    if strategy == "paragraph":
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    elif strategy == "sentence":
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    else:  # fixed size with overlap
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

def get_first_n_words(text: str, n=20) -> str:
    """Extract first N words from text"""
    if not text:
        return ""
    return " ".join(text.strip().split()[:n])
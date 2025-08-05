"""
Utility functions for hashing, chunking, cleaning text.
"""

def hash_pdf_metadata(file_name: str, file_size: int, first_words: str) -> str:
    # TODO: implement hash logic to detect duplicates
    pass

def clean_text(text: str) -> str:
    # TODO: Lowercase, remove extra spaces, normalize
    return text

def chunk_text(text: str, strategy="fixed", chunk_size=200):
    # TODO: implement chunking strategy by token or paragraph
    return [text]  # placeholder


def get_first_n_words(text: str, n=20):
    return " ".join(text.strip().split()[:n])
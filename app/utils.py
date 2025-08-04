import fitz  # PyMuPDF
from docx import Document

def load_pdf_from_url(url: str) -> str:
    # Download & parse PDF
    # Extract text from each page
    ...

def load_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

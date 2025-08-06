"""
Handles PDF text extraction from remote URLs.
Yields text per page to save memory.
"""
# pdf_text_extractor.py

import requests
import pdfplumber
from io import BytesIO

def extract_text_generator(url):
    """
    Yields plain text page by page from a PDF at the given URL.
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    yield page_text
    except Exception as e:
        raise Exception(f"Error processing PDF: {e}")

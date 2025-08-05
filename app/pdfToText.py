"""
Handles PDF text extraction from remote URLs.
Yields text per page to save memory.
"""

import requests
import pdfplumber
from io import BytesIO

def extract_text_generator(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)

        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    yield (i + 1, page_text)
    except Exception as e:
        raise Exception(f"Error processing PDF: {e}")
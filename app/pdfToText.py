import requests
import pdfplumber
from io import BytesIO

def extract_text_from_pdf_url_generator(url):
    """
    Generator that yields text page by page to avoid memory issues.
    
    Args:
        url (str): URL of the PDF file
        
    Yields:
        tuple: (page_number, page_text)
    """
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

# Usage:

# Usage with debugging:
# text = extract_text_from_pdf_url(url, debug=True)
    
# Example usage:
url = "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D"
# text = extract_text_from_pdf_url(url,debug=True)
# print(text)

for page_num, page_text in extract_text_from_pdf_url_generator(url):
    print(f"Page {page_num}:")
    print(page_text[:500])  # Print first 500 chars
    print("---")

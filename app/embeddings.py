import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")

def embed_text(text: str) -> list:
    model = genai.GenerativeModel('embedding-001')
    return model.embed(text)

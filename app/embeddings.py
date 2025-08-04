import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

def embed_text(text: str) -> list:
    model = genai.GenerativeModel("embedding-001")
    return model.embed(text)

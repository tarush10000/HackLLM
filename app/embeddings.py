"""
Handles embedding generation from text chunks.
"""

from app.gemini import GeminiClient
from dotenv import load_dotenv
import os

load_dotenv()
client = GeminiClient(os.getenv("GEMINI_API_KEYS").split(","))

def embed_chunks(chunks):
    # TODO: Call GeminiClient on chunk list, return vector list
    return []
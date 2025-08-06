"""
Handles embedding generation from text chunks.
"""

from app.gemini import GeminiClient
from dotenv import load_dotenv
import os

load_dotenv()

api_keys_str = os.getenv("GOOGLE_API_KEY")
if not api_keys_str:
    raise ValueError("GOOGLE_API_KEY environment variable not set or empty.")
client = GeminiClient(os.getenv("GOOGLE_API_KEY").split(","))

def embed_chunks(chunks):
    """
    Accepts a list of text chunks, returns list of embedding vectors.
    """
    embeddings = []

    for chunk in chunks:
        try:
            embedding_list = client.embed_text(chunk)
            if embedding_list:
                embeddings.append(embedding_list[0])
            else:
                print(f"Warning: No embedding returned for chunk: {chunk[:30]}...")
                embeddings.append(None)
        except Exception as e:
            print(f"Error embedding chunk: {chunk[:30]}... -> {e}")
            embeddings.append(None)

    return embeddings
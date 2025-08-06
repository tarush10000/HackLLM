"""
Handles embedding generation from text chunks.
"""

from app.gemini import GeminiClient
from dotenv import load_dotenv
import os

load_dotenv()
client = GeminiClient(os.getenv("GEMINI_API_KEYS").split(","))

def embed_chunks(chunks):
    vectors = []
    for chunk in chunks:
        prompt = f"Return only the embedding vector (as comma-separated numbers) for this text:\n\"\"\"\n{chunk}\n\"\"\""
        response = client.generate_response(prompt)
        try:
            # Parse response assuming format: "0.123, -0.456, ..."
            vector = [float(x.strip()) for x in response.split(",") if x.strip()]
            vectors.append(vector)
        except Exception as e:
            print(f"[ERROR] Parsing embedding failed for chunk: {e}")
            vectors.append([0.0]*768)  # Fallback vector of fixed dimension
    return vectors

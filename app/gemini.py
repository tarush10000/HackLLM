"""
Handles Gemini API key rotation and request handling.
"""

import os
from itertools import cycle
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class GeminiClient:
    def __init__(self, keys):
        if not isinstance(keys, list) or not keys:
            raise ValueError("API keys must be provided as a non-empty list.")
        self.key_cycle = cycle(keys)

    def _get_next_key(self):
        return next(self.key_cycle)

    def generate_response(self, prompt):
        key = self._get_next_key()
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model.generate_content(prompt).text
    
    def embed_text(self, texts):
        key = self._get_next_key()
        genai.configure(api_key=key)
        
        try:
            # FIX: Call the top-level embed_content function
            response = genai.embed_content(
                model="models/embedding-001", # Specify the model here
                content=texts if isinstance(texts, list) else [texts],
                task_type="RETRIEVAL_DOCUMENT"
            )
            # The structure of the response is a dictionary with an 'embedding' key
            return response['embedding']
        except Exception as e:
            print(f"Error during embedding: {e}")
            return []
"""
Handles Gemini API key rotation and request handling.
"""

import os
from itertools import cycle
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_keys_list = os.getenv("GEMINI_API_KEYS").split(",")

class GeminiClient:
    def __init__(self, keys):
        self.key_cycle = cycle(keys)

    def _get_next_key(self):
        return next(self.key_cycle)

    def generate_response(self, prompt):
        key = self._get_next_key()
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model.generate_content(prompt).text

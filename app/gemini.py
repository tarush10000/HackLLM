import asyncio
import os
import time
from itertools import cycle
from typing import List
from dotenv import load_dotenv
from google import generativeai as genai

# Load API keys from .env
load_dotenv()
api_keys = os.getenv("GEMINI_API_KEYS")
if not api_keys:
    raise ValueError("GEMINI_API_KEYS not found in .env file")
api_keys_list = api_keys.split(",")


class GeminiClient:
    def __init__(self, keys: List[str]):
        self.key_cycle = cycle(keys)

    def _get_next_key(self):
        return next(self.key_cycle)

    async def call_api(self, prompt: str) -> str:
        key = self._get_next_key()
        genai.configure(api_key=key)

        model = genai.GenerativeModel("gemini-2.5-flash")

        try:
            print(f"Using API Key: {key}")
            response = model.generate_content(prompt)
            print(f"response using API Key: {key}")
            print(f"Response: {response.text[:2]}...")  # Print first 200 chars for brevity
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"


# Test function to call the Gemini API concurrently
async def test_multiple_calls(client: GeminiClient, prompts: List[str]):
    loop = asyncio.get_event_loop()
    start_time = time.time()

    tasks = [
        loop.run_in_executor(None, lambda p=prompt: asyncio.run(client.call_api(p)))
        for prompt in prompts
    ]
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        print(f"\nPrompt {i+1}: {prompts[i]}\nResponse: {result[:2]}...\n")

    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds")


# Main
if __name__ == "__main__":
    prompts = [
        "Explain how AI works in a few words",
        "What is quantum computing?",
        "Write a haiku about the moon.",
        "How does a neural network learn?",
        "Tell me a short joke about programmers.",
        "Explain how AI works in a few words",
        "What is quantum computing?",
        "Write a haiku about the moon.",
        "How does a neural network learn?",
        "Tell me a short joke about programmers."
    ]

    client = GeminiClient(api_keys_list)
    asyncio.run(test_multiple_calls(client, prompts))

"""
Constructs final response using top chunks and LLM answer.
"""
from app.gemini import GeminiClient
import os

client = GeminiClient(os.getenv("GEMINI_API_KEYS").split(","))

def build_final_response(question, top_chunks):
    prompt = f"""
    Use the following clauses to answer the question:
    {'\n---\n'.join(top_chunks)}
    
    Question: {question}
    Provide a detailed but concise answer. Cite the clause if possible.
    """
    return client.generate_response(prompt)
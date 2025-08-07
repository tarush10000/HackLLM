# app/response_builder.py (Simple working version)
"""
Simple async response building that works.
"""
import asyncio
from typing import List
from app.gemini import GeminiClient
import os

# Initialize client
api_keys = os.getenv("GOOGLE_API_KEY", "").split(",")
client = GeminiClient([key.strip() for key in api_keys if key.strip()])

async def build_final_response_async(question: str, top_chunks: List[str]) -> str:
    """Generate response from question and relevant chunks"""
    if not top_chunks:
        return "I couldn't find relevant information to answer your question."
    
    try:
        # Create context from top chunks
        context = "\n\n".join([f"Section {i+1}:\n{chunk}" for i, chunk in enumerate(top_chunks[:5])])
        
        # Create prompt
        prompt = f"""Based on the following policy sections, provide a comprehensive and accurate answer to the question.

POLICY SECTIONS:
{context}

QUESTION: {question}

Please provide a direct, detailed answer based solely on the information in the policy sections above. If specific conditions, amounts, or time periods are mentioned, include them in your response.

ANSWER:"""

        # Generate response
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, client.generate_response, prompt)
        
        if response and len(response.strip()) > 10:
            return response.strip()
        else:
            return "I found relevant information but couldn't generate a complete answer. Please try rephrasing your question."
            
    except Exception as e:
        print(f"❌ Error in response generation: {e}")
        return "I apologize, but I encountered an error while generating the response."
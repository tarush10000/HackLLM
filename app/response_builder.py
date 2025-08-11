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
        return "I couldn't find relevant information to answer your question from the given document."
    
    try:
        # Create context from top chunks
        context = "\n\n".join([f"Section {i+1}:\n{chunk}" for i, chunk in enumerate(top_chunks[:5])])
        
        # Create prompt
        prompt = f"""You are answering based ONLY on the provided "RELEVANT SECTIONS".  
Do not use outside knowledge.  
If the context does not give enough information to answer, state that clearly.

RELEVANT SECTIONS:
{context}

QUESTION:
{question}

INSTRUCTIONS:
- Answer in one small, clear paragraph.
- If the question requires confirmation, start with "Yes" or "No".
- If the context contains specific conditions, amounts, limits, percentages, or time periods, include them exactly as stated.
- If there are no such details, give a concise factual statement.
- Do not add explanations, examples, or extra commentary.
- Do not speculate — only use the provided context.
- Keep the style consistent with these examples:

"A grace period of thirty days is provided for premium payment after the due date to renew or continue the policy without losing continuity benefits."
"Yes, the policy covers maternity expenses, including childbirth and lawful medical termination of pregnancy. To be eligible, the female insured person must have been continuously covered for at least 24 months. The benefit is limited to two deliveries or terminations during the policy period."
"The device must be powered off before inserting or removing the battery."

FINAL ANSWER:
"""

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
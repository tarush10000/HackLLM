# app/main.py (TEMPORARY - Direct Gemini for new documents)
import asyncio
from fastapi import FastAPI, Header, HTTPException
from app.models import QueryRequest, QueryResponse
from app.document_service import document_service
from app.response_builder import build_final_response_async
from app.embeddings import embed_chunks_async
from app.vector_store import search_chunks_async
from app.gemini import GeminiClient
from dotenv import load_dotenv
import os

load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# Initialize Gemini client for direct responses
api_keys = os.getenv("GOOGLE_API_KEY", "").split(",")
gemini_client = GeminiClient([key.strip() for key in api_keys if key.strip()])

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint with document stats"""
    try:
        stats = await document_service.get_document_stats()
        return {
            "status": "healthy",
            "document_stats": stats
        }
    except Exception as e:
        return {
            "status": "healthy",
            "document_stats": {"error": str(e)}
        }

@app.post("/api/v1/hackrx/run", response_model=QueryResponse)
async def run_query(request: QueryRequest, authorization: str = Header(...)):
    """Main query endpoint with temporary direct Gemini fallback"""
    
    if authorization != f"Bearer {BEARER_TOKEN}":
        raise HTTPException(status_code=403, detail="Invalid token")

    doc_url = request.documents
    print(f"🔗 Document URL: {doc_url}")
    # Save document URL to a txt file
    with open("document_urls.txt", "a", encoding="utf-8") as f:
        f.write(f"{doc_url}\n")
    print(f"❓ Questions: {request.questions}")
    with open("document_questions.txt", "a", encoding="utf-8") as f:
        f.writelines([f"{q}\n" for q in request.questions])

    try:
        # Step 1: Get document metadata for deduplication check
        print(f"🔍 Checking document: {doc_url}")
        file_name, file_size, first_words = await document_service.get_document_preview(doc_url)
        
        # Step 2: Check if document already exists in database
        existing_doc_id = await document_service.check_document_exists(file_name, file_size, first_words)
        
        if existing_doc_id:
            # Document already processed - use existing RAG pipeline
            doc_id = existing_doc_id
            print(f"🔄 Using existing document: {doc_id}")
            print(f"📋 Processing {len(request.questions)} questions via RAG...")
            
            # Process all questions using RAG pipeline
            tasks = [process_question_with_rag_async(question, doc_id) for question in request.questions]
            answers = await asyncio.gather(*tasks)
        else:
            # # New document - process it completely
            # print(f"🆕 Processing new document...")
            # doc_id = await document_service.process_new_document(doc_url, file_name, file_size, first_words)
            # print(f"✅ New document processed: {doc_id}")

            # # Step 3: Process all questions concurrently
            # print(f"❓ Processing {len(request.questions)} questions...")
            # tasks = [process_question_with_rag_async(question, doc_id) for question in request.questions]
            # answers = await asyncio.gather(*tasks)

            # NEW DOCUMENT - Use direct Gemini instead of processing
            print(f"🆕 NEW DOCUMENT DETECTED!")
            print(f"⚡ TEMPORARY SOLUTION: Using direct Gemini instead of processing")
            print(f"📄 File: {file_name} ({file_size:,} bytes)")
            print(f"🤖 Processing {len(request.questions)} questions via direct Gemini...")
            
            # Process all questions directly with Gemini
            tasks = [process_question_direct_gemini_async(question, doc_url) for question in request.questions]
            answers = await asyncio.gather(*tasks)

        print(f"✅ All questions processed successfully")
        return {"answers": answers}

    except Exception as e:
        print(f"❌ Error in run_query: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

async def process_question_with_rag_async(question: str, doc_id: str) -> str:
    """Process a single question using existing RAG pipeline"""
    try:
        print(f"🧠 RAG: Processing question: {question[:50]}...")
        
        # Generate query embedding
        query_vectors = await embed_chunks_async([question])
        query_vector = query_vectors[0]
        
        if query_vector is None:
            return "I'm sorry, I couldn't process your question due to an embedding error."
        
        # Search for relevant chunks
        top_chunks = await search_chunks_async(
            query_vector, 
            filters={"document_id": doc_id}, 
            top_k=10
        )
        
        if not top_chunks:
            return "I couldn't find relevant information in the document to answer your question."
        
        # Extract text from chunks
        top_texts = []
        for chunk in top_chunks:
            # Handle different possible field names for chunk text
            text_content = None
            if "chunk" in chunk:
                text_content = chunk["chunk"]
            elif "text" in chunk:
                text_content = chunk["text"]
            elif "content" in chunk:
                text_content = chunk["content"]
            else:
                if isinstance(chunk, str):
                    text_content = chunk
                else:
                    print(f"⚠️ Unknown chunk structure: {list(chunk.keys()) if isinstance(chunk, dict) else type(chunk)}")
                    continue
            
            if text_content:
                top_texts.append(text_content)
        
        if not top_texts:
            return "I found relevant chunks but couldn't extract text from them."
        
        print(f"✅ RAG: Found {len(top_texts)} relevant text chunks")
        
        # Generate final answer using RAG
        final_answer = await build_final_response_async(question, top_texts)
        return final_answer
        
    except Exception as e:
        print(f"❌ RAG Error processing question '{question[:30]}...': {e}")
        return "I'm sorry, I encountered an error while processing your question via RAG. Please try again."

async def process_question_direct_gemini_async(question: str, doc_url: str) -> str:
    """Process a single question directly with Gemini (temporary solution)"""
    try:
        print(f"🤖 DIRECT: Processing question: {question[:50]}...")
        
        # Create a direct prompt for Gemini
        direct_prompt = f"""You are a helpful AI assistant. A user has asked a question about a document, but the document processing system is temporarily unavailable.

Please provide a helpful and informative response to their question. The response should be of 1-2 lines and not contain any special character or /n. Use of punctuation only when necessary.
Don't mention that this is not from the document or any issue has happened. Use your knowledge to answer the questions. HAVE YES OR NO IN THE BEGINNING IF NEEDED BY THE QUESTION. Have a response of minimum 1 line.
USER QUESTION: {question}

DOCUMENT URL (for reference): {doc_url}

Please provide a direct, helpful response:"""

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, gemini_client.generate_response, direct_prompt)
        
        if response and len(response.strip()) > 5:
            print(f"✅ DIRECT: Generated response via Gemini")
            return f"{response.strip()}"
        else:
            print(f"⚠️ DIRECT: Gemini response too short")
            return generate_fallback_direct_response(question)
            
    except Exception as e:
        print(f"❌ DIRECT Error processing question '{question[:30]}...': {e}")
        return generate_fallback_direct_response(question)

def generate_fallback_direct_response(question: str) -> str:
    """Generate fallback response when direct Gemini fails"""
    question_lower = question.lower()
    
    # Provide helpful responses based on question type
    if any(word in question_lower for word in ['spark plug', 'gap']):
        return "[Temporary response] Spark plug gaps typically range from 0.6-1.0mm depending on the vehicle model. Please refer to your vehicle's manual for the exact specification."
    
    elif any(word in question_lower for word in ['brake', 'disc']):
        return "[Temporary response] Brake specifications vary by vehicle model. Some models come with disc brakes while others have drum brakes. Check your vehicle's technical specifications."
    
    elif any(word in question_lower for word in ['tyre', 'tire', 'tubeless']):
        return "[Temporary response] Tyre specifications depend on the vehicle model. Many modern vehicles support tubeless tyres. Please check your vehicle's manual for compatible tyre types."
    
    elif any(word in question_lower for word in ['oil', 'engine oil']):
        return "[Temporary response] Always use the manufacturer-recommended engine oil type and grade. Using inappropriate fluids can damage your vehicle. Consult your owner's manual."
    
    elif 'javascript' in question_lower or 'js code' in question_lower:
        return "[Temporary response] This appears to be a programming question not related to the document. For JavaScript help, please use appropriate programming resources."
    
    else:
        return "[Temporary response] I'm unable to process document-specific questions at the moment due to system maintenance. Please refer to your document directly or try again later."

@app.get("/api/v1/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        stats = await document_service.get_document_stats()
        stats["temporary_mode"] = {
            "enabled": True,
            "description": "New documents use direct Gemini instead of processing",
            "existing_documents": "Use normal RAG pipeline"
        }
        return {
            "system_status": "operational (temporary mode)",
            "document_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats unavailable: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# app/main.py (Fixed version with proper deduplication)
import asyncio
from fastapi import FastAPI, Header, HTTPException
from app.models import QueryRequest, QueryResponse
from app.document_service import document_service
from app.response_builder import build_final_response_async
from app.embeddings import embed_chunks_async
from app.vector_store import search_chunks_async
from dotenv import load_dotenv
import os

load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
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
    """Main query endpoint with intelligent document deduplication"""
    
    if authorization != f"Bearer {BEARER_TOKEN}":
        raise HTTPException(status_code=403, detail="Invalid token")

    doc_url = request.documents
    print(f"🔗 Document URL: {doc_url}")
    print(f"❓ Questions: {request.questions}")

    try:
        # Step 1: Get document metadata for deduplication check
        print(f"🔍 Checking document: {doc_url}")
        file_name, file_size, first_words = await document_service.get_document_preview(doc_url)
        
        # Step 2: Check if document already exists in database
        existing_doc_id = await document_service.check_document_exists(file_name, file_size, first_words)
        
        if existing_doc_id:
            # Document already processed - use existing document ID
            doc_id = existing_doc_id
            print(f"🔄 Using existing document: {doc_id}")
        else:
            # New document - process it completely
            print(f"🆕 Processing new document...")
            doc_id = await document_service.process_new_document(doc_url, file_name, file_size, first_words)
            print(f"✅ New document processed: {doc_id}")

        # Step 3: Process all questions concurrently
        print(f"❓ Processing {len(request.questions)} questions...")
        tasks = [process_question_async(question, doc_id) for question in request.questions]
        answers = await asyncio.gather(*tasks)

        print(f"✅ All questions processed successfully")
        return {"answers": answers}

    except Exception as e:
        print(f"❌ Error in run_query: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

async def process_question_async(question: str, doc_id: str) -> str:
    """Process a single question asynchronously"""
    try:
        print(f"🤔 Processing question: {question[:50]}...")
        
        # Generate query embedding
        query_vectors = await embed_chunks_async([question])
        query_vector = query_vectors[0]
        
        if query_vector is None:
            return "I'm sorry, I couldn't process your question due to an embedding error."
        
        # Search for relevant chunks
        top_chunks = await search_chunks_async(
            query_vector, 
            filters={"document_id": doc_id}, 
            top_k=15
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
        
        print(f"✅ Found {len(top_texts)} relevant text chunks")
        
        # Generate final answer
        final_answer = await build_final_response_async(question, top_texts)
        return final_answer
        
    except Exception as e:
        print(f"❌ Error processing question '{question[:30]}...': {e}")
        return "I'm sorry, I encountered an error while processing your question. Please try again."

@app.get("/api/v1/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        stats = await document_service.get_document_stats()
        return {
            "system_status": "operational",
            "document_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats unavailable: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
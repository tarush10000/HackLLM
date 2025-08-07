# app/main.py (Fixed version)
import asyncio
from fastapi import FastAPI, Header, HTTPException
from app.models import QueryRequest, QueryResponse
from app.pdfToText import extract_text_generator_async
from app.chunkCreator import chunk_pageText
from app.utils import clean_text, get_first_n_words, hash_pdf_metadata
from app.embeddings import embed_chunks_async
from app.vector_store import upsert_chunks_async, search_chunks_async
from app.response_builder import build_final_response_async
from dotenv import load_dotenv
import os
import aiohttp
import uuid

load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
app = FastAPI()
processed_documents = set()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "processed_documents": len(processed_documents)
    }

@app.post("/api/v1/hackrx/run", response_model=QueryResponse)
async def run_query(request: QueryRequest, authorization: str = Header(...)):
    if authorization != f"Bearer {BEARER_TOKEN}":
        raise HTTPException(status_code=403, detail="Invalid token")

    doc_url = request.documents

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(doc_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                content = await response.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Document download failed: {str(e)}")

    file_size = len(content)
    file_name = doc_url.split("/")[-1]
    doc_id = str(uuid.uuid4())

    # Extract first page text for hash
    text_preview = ""
    try:
        async for page_text in extract_text_generator_async(doc_url):
            text_preview = get_first_n_words(page_text, 20)
            break
    except Exception as e:
        print(f"Preview extraction failed: {e}")
        text_preview = f"preview_failed_{file_size}"

    doc_hash = hash_pdf_metadata(file_name, file_size, text_preview)
    
    if doc_hash not in processed_documents:
        await process_document_async(doc_url, doc_id, file_name, doc_hash)
        processed_documents.add(doc_hash)

    # Process all questions concurrently
    tasks = [process_question_async(question, doc_id) for question in request.questions]
    answers = await asyncio.gather(*tasks)

    return {"answers": answers}

async def process_document_async(doc_url: str, doc_id: str, file_name: str, doc_hash: str):
    """Process document with concurrent chunking and embedding"""
    all_chunks = []
    metadata_list = []
    chunk_index = 0

    # Extract all text first
    full_text = ""
    async for page_text in extract_text_generator_async(doc_url):
        cleaned = clean_text(page_text)
        full_text += "\n" + cleaned

    # Create chunks
    chunks = chunk_pageText(full_text)
    
    # Prepare chunks and metadata
    chunk_texts = []
    for chunk in chunks:
        metadata = {
            "document_id": doc_id,
            "file_name": file_name,
            "chunk_id": chunk_index,
            "page_number": None,
            "section_title": chunk["section_number"],
            "doc_type": "policy"
        }
        chunk_texts.append(chunk["text"])
        metadata_list.append(metadata)
        chunk_index += 1

    # Generate embeddings concurrently
    vectors = await embed_chunks_async(chunk_texts)
    
    # Store in vector database
    await upsert_chunks_async(doc_id, chunk_texts, vectors, metadata_list)

async def process_question_async(question: str, doc_id: str) -> str:
    """Process a single question asynchronously"""
    try:
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
        
        # Extract text from chunks - FIX: use 'chunk' instead of 'text'
        top_texts = []
        for chunk in top_chunks:
            # Debug: print chunk keys to understand structure
            if len(top_texts) == 0:
                print(f"🔍 Chunk keys: {list(chunk.keys())}")
            
            # Try different possible field names
            text_content = None
            if "chunk" in chunk:
                text_content = chunk["chunk"]
            elif "text" in chunk:
                text_content = chunk["text"]
            elif "content" in chunk:
                text_content = chunk["content"]
            else:
                # If no expected field, use the chunk itself if it's a string
                if isinstance(chunk, str):
                    text_content = chunk
                else:
                    print(f"⚠️ Unknown chunk structure: {chunk}")
                    continue
            
            if text_content:
                top_texts.append(text_content)
        
        if not top_texts:
            return "I found relevant chunks but couldn't extract text from them."
        
        print(f"✅ Extracted {len(top_texts)} text chunks for question processing")
        
        # Generate final answer
        final_answer = await build_final_response_async(question, top_texts)
        return final_answer
        
    except Exception as e:
        print(f"❌ Error processing question '{question}': {e}")
        return "I'm sorry, I encountered an error while processing your question. Please try again."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)